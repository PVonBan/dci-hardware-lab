// rsplab capture <labdir> <bank.syx> [first last]
//
// 1. Finds the RSP-550 on MIDI and opens the multichannel interface (name containing "MHLink", or the
//    first device with 4+ inputs and outputs) at 48 kHz.
// 2. Finds the audio routing: a quiet (-30 dBFS) 250 ms 1 kHz burst on each output in turn while every input
//    records. The RSP-550's sends are the outputs whose return carries a reverb tail (the current edit-buffer
//    program is a hall); a direct loopback has no tail.
// 3. For each program of bank.syx: writes its 96 bytes to the TEMPORARY area (02 00 00) and sends the sound
//    change request (02 00 60), reads the name back to confirm, then plays the stimulus and records the
//    returns to <labdir>/capture/NNN.wav (24-bit, 48 kHz, stereo).
// 4. Restores the edit buffer it found. Stored programs (03/04 xx xx) are never written.
#pragma once

struct PlayRec : public AudioIODeviceCallback
{
    std::vector<std::vector<float>> play; std::vector<int> playCh;
    std::vector<std::vector<float>> rec;  std::vector<int> recCh;
    std::atomic<int> pos { -1 };
    int len = 0;
    std::atomic<int> callbacks { 0 };

    void audioDeviceIOCallbackWithContext (const float* const* in, int numIn, float* const* outp, int numOut, int n,
                                           const AudioIODeviceCallbackContext&) override
    {
        ++callbacks;
        for (int c = 0; c < numOut; ++c) if (outp[c] != nullptr) std::fill (outp[c], outp[c] + n, 0.0f);
        const int p = pos.load();
        if (p < 0 || p >= len) return;
        const int m = std::min (n, len - p);
        for (size_t r = 0; r < playCh.size(); ++r)
            if (playCh[r] < numOut && outp[playCh[r]] != nullptr) std::copy_n (play[r].data() + p, m, outp[playCh[r]]);
        for (size_t r = 0; r < recCh.size(); ++r)
            if (recCh[r] < numIn && in[recCh[r]] != nullptr) std::copy_n (in[recCh[r]], m, rec[r].data() + p);
        pos.store (p + m);
    }
    void audioDeviceAboutToStart (AudioIODevice*) override {}
    void audioDeviceStopped() override {}

    void setup (int length, std::vector<int> outs, std::vector<int> ins)
    {
        len = length; playCh = std::move (outs); recCh = std::move (ins);
        play.assign (playCh.size(), std::vector<float> ((size_t) len, 0.0f));
        rec.assign (recCh.size(), std::vector<float> ((size_t) len, 0.0f));
    }
    bool runBlocking (double fs)
    {
        pos.store (0);
        const double t0 = Time::getMillisecondCounterHiRes();
        while (pos.load() < len)
        {
            Thread::sleep (10);
            if (Time::getMillisecondCounterHiRes() - t0 > (len / fs + 5.0) * 1000.0) { pos.store (-1); return false; }
        }
        pos.store (-1);
        return true;
    }
};

// energy of a tone at f over [a, b) samples (single-bin DFT), dBFS-ish
static double toneDb (const std::vector<float>& x, double fs, double f, int a, int b)
{
    a = std::max (0, a); b = std::min ((int) x.size(), b);
    if (b <= a) return -200;
    double re = 0, im = 0;
    for (int i = a; i < b; ++i) { const double ph = 2 * MathConstants<double>::pi * f * i / fs; re += x[(size_t) i] * std::cos (ph); im += x[(size_t) i] * std::sin (ph); }
    const double amp = 2 * std::sqrt (re * re + im * im) / (b - a);
    return 20 * std::log10 (amp + 1e-12);
}
static double rmsDb (const std::vector<float>& x, int a, int b)
{
    a = std::max (0, a); b = std::min ((int) x.size(), b);
    double s = 0; for (int i = a; i < b; ++i) s += (double) x[(size_t) i] * x[(size_t) i];
    return 10 * std::log10 (s / std::max (1, b - a) + 1e-24);
}

static MidiMessage dt1 (int dev, int a0, int a1, int a2, const uint8* data, int n)
{
    std::vector<uint8> body { (uint8) a0, (uint8) a1, (uint8) a2 };
    body.insert (body.end(), data, data + n);
    std::vector<uint8> m { 0x41, (uint8) dev, 0x38, 0x12 };
    m.insert (m.end(), body.begin(), body.end());
    m.push_back (rolandSum (body));
    return MidiMessage::createSysExMessage (m.data(), (int) m.size());
}

struct BankProgram { int number; String name; std::array<uint8, 96> payload; };

static std::vector<BankProgram> loadBank (const File& f)
{
    std::vector<BankProgram> v;
    MemoryBlock mb; if (! f.loadFileAsData (mb)) return v;
    const auto* d = (const uint8*) mb.getData();
    for (size_t i = 0; i + 106 <= mb.getSize(); )
    {
        if (d[i] == 0xF0 && d[i + 1] == 0x41 && d[i + 3] == 0x38 && d[i + 4] == 0x12 && d[i + 105] == 0xF7 && (d[i + 5] == 0x03 || d[i + 5] == 0x04))
        {
            BankProgram p; p.number = d[i + 5] == 0x03 ? d[i + 6] + 1 : d[i + 6] + 129;
            std::copy_n (d + i + 8, 96, p.payload.begin());
            p.name = asciiName (p.payload.data(), 16).trim();
            v.push_back (p);
            i += 106;
        }
        else ++i;
    }
    std::sort (v.begin(), v.end(), [] (auto& a, auto& b) { return a.number < b.number; });
    return v;
}

// Stimulus (48 kHz): 0.25 s silence | impulse L + 4 s | impulse R + 4 s | exp. sweep 20 Hz-20 kHz 2.5 s at -12 dBFS
// + 3 s | 1 kHz steps -36/-24/-12/-6/-3 dBFS (0.3 s on, 0.1 s off) + 1 s. Markers written to stimulus.txt.
struct Stimulus { std::vector<float> L, R; StringArray markers; };
static Stimulus makeStimulus (double fs)
{
    Stimulus s; auto& L = s.L; auto& R = s.R;
    auto at = [&] () { return (int) L.size(); };
    auto pad = [&] (double sec) { L.resize (L.size() + (size_t) (sec * fs), 0.0f); R.resize (L.size(), 0.0f); };
    pad (0.25);
    s.markers.add ("impulseL " + String (at())); L.push_back (0.5f); R.push_back (0.0f); pad (4.0);
    s.markers.add ("impulseR " + String (at())); L.push_back (0.0f); R.push_back (0.5f); pad (4.0);
    {
        const double T = 2.5, f1 = 20, f2 = 20000, k = std::log (f2 / f1);
        const int n = (int) (T * fs);
        s.markers.add ("sweep " + String (at()) + " " + String (n) + " 20 20000 -12dBFS");
        for (int i = 0; i < n; ++i)
        {
            const double t = i / fs;
            double v = 0.25 * std::sin (2 * MathConstants<double>::pi * f1 * T / k * (std::exp (t / T * k) - 1));
            const double fade = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.002 * fs) });
            v *= fade;
            L.push_back ((float) v); R.push_back ((float) v);
        }
        pad (3.0);
    }
    for (double db : { -36.0, -24.0, -12.0, -6.0, -3.0 })
    {
        const int n = (int) (0.3 * fs);
        s.markers.add ("tone1k " + String (at()) + " " + String (n) + " " + String (db, 0) + "dBFS");
        const double a = std::pow (10.0, db / 20);
        for (int i = 0; i < n; ++i)
        {
            const double fade = std::min ({ 1.0, i / (0.005 * fs), (n - 1 - i) / (0.005 * fs) });
            const float v = (float) (a * fade * std::sin (2 * MathConstants<double>::pi * 1000.0 * i / fs));
            L.push_back (v); R.push_back (v);
        }
        pad (0.1);
    }
    pad (1.0);
    // 10 dB lower than first designed: through the RSP-550 some programs add up to +4 dB, and the MHLink
    // inputs clipped on the loud steps. Markers keep the nominal levels; the true send level is nominal - 10 dB.
    for (auto* ch : { &L, &R }) for (auto& v : *ch) v *= 0.31622777f;
    s.markers.add ("gain -10dB (all levels above are nominal; actual = nominal - 10 dB)");
    return s;
}

static bool writeWav (const File& f, const std::vector<std::vector<float>>& ch, double fs)
{
    f.deleteFile();
    WavAudioFormat wav;
    std::unique_ptr<OutputStream> os (f.createOutputStream().release());
    if (! os) return false;
    std::unique_ptr<AudioFormatWriter> w (wav.createWriterFor (os.get(), fs, (unsigned) ch.size(), 24, {}, 0));
    if (! w) return false;
    os.release();
    AudioBuffer<float> b ((int) ch.size(), (int) ch[0].size());
    for (size_t c = 0; c < ch.size(); ++c) b.copyFrom ((int) c, 0, ch[c].data(), (int) ch[c].size());
    return w->writeFromAudioSampleBuffer (b, 0, b.getNumSamples());
}

static int runCapture (int argc, char** argv)
{
    if (argc < 4) { out ("usage: rsplab capture <labdir> <bank.syx> [first last]"); return 1; }
    const File lab { String (CharPointer_UTF8 (argv[2])) };
    const File bankFile { String (CharPointer_UTF8 (argv[3])) };
    const int first = argc > 5 ? atoi (argv[4]) : 1, last = argc > 5 ? atoi (argv[5]) : 160;
    const File capDir = lab.getChildFile ("capture");
    capDir.createDirectory();
    const double fs = 48000.0;

    out ("RSP-550 lab capture, " + Time::getCurrentTime().toString (true, true));
    auto bank = loadBank (bankFile);
    out ("bank " + bankFile.getFileName() + ": " + String ((int) bank.size()) + " programs");
    if (bank.empty()) return 1;

    // ---- MIDI
    Collector col;
    auto inInfo = MidiInput::getAvailableDevices(); auto outInfo = MidiOutput::getAvailableDevices();
    std::vector<std::unique_ptr<MidiInput>> ins;
    for (int i = 0; i < inInfo.size(); ++i)
    {
        auto mi = MidiInput::openDevice (inInfo[i].identifier, &col);
        if (mi) { col.portOf[mi.get()] = i; mi->start(); }
        ins.push_back (std::move (mi));
    }
    std::unique_ptr<MidiOutput> mo; int dev = -1;
    for (int o = 0; o < outInfo.size() && dev < 0; ++o)
    {
        auto m = MidiOutput::openDevice (outInfo[o].identifier);
        if (! m) continue;
        for (int d = 0; d < 16 && dev < 0; ++d)
        {
            const size_t before = col.count();
            m->sendMessageNow (rq1 (d, 0x03, 0x00, 0x00, 16));
            for (int w = 0; w < 30 && col.count() == before; ++w) Thread::sleep (10);
            Thread::sleep (60);
            for (auto& r : col.since (before)) if (isDT1 (r.bytes)) { dev = r.bytes[2]; out ("MIDI: RSP-550 on '" + outInfo[o].name + "' device ID " + String (dev)); }
        }
        if (dev >= 0) mo = std::move (m);
    }
    if (dev < 0) { out ("MIDI: no answer from the RSP-550"); return 2; }

    auto readArea = [&] (int a0, int a1, int a2, int size) -> std::vector<uint8>
    {
        for (int attempt = 0; attempt < 3; ++attempt)
        {
            const size_t before = col.count();
            mo->sendMessageNow (rq1 (dev, a0, a1, a2, size));
            const double t0 = Time::getMillisecondCounterHiRes();
            std::vector<uint8> data;
            while (Time::getMillisecondCounterHiRes() - t0 < 1500 && (int) data.size() < size)
            {
                Thread::sleep (5);
                data.clear();
                for (auto& r : col.since (before))
                    if (isDT1 (r.bytes) && checksumOk (r.bytes) && r.bytes[5] == a0 && r.bytes[6] == a1)
                        data.insert (data.end(), r.bytes.begin() + 8, r.bytes.end() - 2);
            }
            if ((int) data.size() >= size) { data.resize ((size_t) size); return data; }
        }
        return {};
    };
    auto loadTemp = [&] (const uint8* payload96) -> bool
    {
        mo->sendMessageNow (dt1 (dev, 0x02, 0x00, 0x00, payload96, 96));
        Thread::sleep (80);
        const uint8 zero = 0;
        mo->sendMessageNow (dt1 (dev, 0x02, 0x00, 0x60, &zero, 1));   // sound change request
        Thread::sleep (400);
        auto back = readArea (0x02, 0x00, 0x00, 0x60);
        return back.size() == 96 && std::equal (back.begin(), back.end(), payload96);
    };

    const bool usePC = String (argv[1]) == "capturepc";
    auto selectPC = [&] (const BankProgram& p) -> bool
    {
        if (p.number > 128) return false;
        for (int attempt = 0; attempt < 2; ++attempt)
        {
            if (attempt == 1)   // the unit ignores a program change to the program it is already on: step away first
            {
                mo->sendMessageNow (MidiMessage::programChange (dev + 1, p.number % 128));
                Thread::sleep (500);
            }
            mo->sendMessageNow (MidiMessage::programChange (dev + 1, p.number - 1));
            Thread::sleep (700);
            auto back = readArea (0x02, 0x00, 0x00, 0x60);
            if (back.size() == 96 && std::equal (back.begin(), back.end(), p.payload.data())) return true;
        }
        return false;
    };
    auto original = readArea (0x02, 0x00, 0x00, 0x60);
    if (original.size() != 96) { out ("could not read the edit buffer"); return 2; }
    out ("edit buffer now: \"" + asciiName (original.data(), 16).trim() + "\" (restored at the end)");

    // ---- Audio
    AudioDeviceManager adm;
    String devName; AudioIODeviceType* devType = nullptr;
    for (auto* t : adm.getAvailableDeviceTypes())
    {
        t->scanForDevices();
        for (auto& n : t->getDeviceNames (false)) if (n.containsIgnoreCase ("MHLink") && t->getDeviceNames (true).contains (n)) { devName = n; devType = t; }
    }
    if (devName.isEmpty()) { out ("audio: MHLink not found"); return 3; }
    adm.setCurrentAudioDeviceType (devType->getTypeName(), true);
    AudioDeviceManager::AudioDeviceSetup setup;
    setup.outputDeviceName = setup.inputDeviceName = devName;
    setup.sampleRate = fs; setup.bufferSize = 512;
    setup.useDefaultInputChannels = setup.useDefaultOutputChannels = false;
    setup.inputChannels.setRange (0, 32, true); setup.outputChannels.setRange (0, 32, true);
    const String err = adm.setAudioDeviceSetup (setup, true);
    auto* io = adm.getCurrentAudioDevice();
    if (err.isNotEmpty() || io == nullptr) { out ("audio: could not open " + devName + ": " + err); return 3; }
    const int nIn = io->getActiveInputChannels().countNumberOfSetBits(), nOut = io->getActiveOutputChannels().countNumberOfSetBits();
    out ("audio: " + devName + " at " + String (io->getCurrentSampleRate(), 0) + " Hz, block " + String (io->getCurrentBufferSizeSamples())
         + ", " + String (nIn) + " in / " + String (nOut) + " out, reported latency in " + String (io->getInputLatencyInSamples()) + " out " + String (io->getOutputLatencyInSamples()));
    if (std::abs (io->getCurrentSampleRate() - fs) > 1) { out ("audio: device would not run at 48 kHz"); return 3; }
    PlayRec pr;
    adm.addAudioCallback (&pr);
    Thread::sleep (500);

    std::vector<int> sends, rets;
    if (argc > 9)
    {
        sends = { atoi (argv[6]) - 1, atoi (argv[7]) - 1 }; rets = { atoi (argv[8]) - 1, atoi (argv[9]) - 1 };
        out ("ROUTING (given): RSP-550 fed from outputs " + String (sends[0] + 1) + "/" + String (sends[1] + 1) + ", returns on inputs " + String (rets[0] + 1) + "/" + String (rets[1] + 1));
    }
    else
    {
    // ---- Routing: -30 dBFS 1 kHz burst on each output in turn, every input recording
    out ("== Finding the routing (quiet 1 kHz bursts, one output at a time)");
    const int burstAt = (int) (0.05 * fs), burstLen = (int) (0.25 * fs), segLen = (int) (0.9 * fs);
    struct Hit { int o, i; double burst, tail, noise, floorDb; };
    std::vector<Hit> hits;
    std::vector<int> allIns; for (int i = 0; i < nIn; ++i) allIns.push_back (i);
    std::vector<float> inPeak ((size_t) nIn, 0.0f); std::vector<double> inSq ((size_t) nIn, 0.0); long long inN = 0;
    for (int o = 0; o < nOut; ++o)
    {
        pr.setup (segLen, { o }, allIns);
        for (int i = 0; i < burstLen; ++i)
        {
            const double fade = std::min ({ 1.0, i / (0.005 * fs), (burstLen - 1 - i) / (0.005 * fs) });
            pr.play[0][(size_t) (burstAt + i)] = (float) (0.0316 * fade * std::sin (2 * MathConstants<double>::pi * 1000.0 * i / fs));
        }
        if (! pr.runBlocking (fs)) { out ("audio: playback stalled (callbacks " + String (pr.callbacks.load()) + ")"); return 3; }
        for (int i = 0; i < nIn; ++i)
            for (float v : pr.rec[(size_t) i]) { inPeak[(size_t) i] = std::max (inPeak[(size_t) i], std::abs (v)); inSq[(size_t) i] += (double) v * v; }
        inN += segLen;
        for (int i = 0; i < nIn; ++i)
        {
            const auto& x = pr.rec[(size_t) i];
            const double noise = toneDb (x, fs, 1000, 0, burstAt), burst = toneDb (x, fs, 1000, burstAt + (int) (0.03 * fs), burstAt + burstLen),
                         tail = rmsDb (x, burstAt + burstLen + (int) (0.06 * fs), segLen) + 3.0,
                         floorDb = rmsDb (x, 0, burstAt) + 3.0;
            if (burst > -75 && burst - noise > 20) hits.push_back ({ o, i, burst, tail, noise, floorDb });
        }
    }
    {
        String l1, l2; int silent = 0;
        for (int i = 0; i < nIn; ++i)
        {
            if (inPeak[(size_t) i] == 0.0f) ++silent;
            l1 << "in" << (i + 1) << " " << String (20 * std::log10 (inPeak[(size_t) i] + 1e-12), 0) << "  ";
            l2 << "in" << (i + 1) << " " << String (10 * std::log10 (inSq[(size_t) i] / (double) inN + 1e-24), 0) << "  ";
        }
        out ("  input peaks (dBFS) over the whole test: " + l1);
        out ("  input rms   (dBFS): " + l2);
        out ("  inputs that were exactly silent (all zeros): " + String (silent) + " of " + String (nIn)
             + (silent == nIn ? "  <- no input audio at all: check System Settings > Privacy & Security > Microphone for Terminal" : ""));
        out ("  audio callbacks: " + String (pr.callbacks.load()));
    }
    for (auto& h : hits)
        out ("  out " + String (h.o + 1) + " -> in " + String (h.i + 1) + ": burst " + String (h.burst, 1) + " dBFS, tail " + String (h.tail, 1) + " dBFS, noise " + String (h.noise, 1) + ", floor " + String (h.floorDb, 1));
    // the RSP-550's sends: outputs whose returns carry a tail; returns: the inputs with the most tail energy
    std::map<int, double> sendScore, retScore;
    for (auto& h : hits) if (h.tail > h.burst - 45 && h.tail > h.floorDb + 8) { sendScore[h.o] = std::max (sendScore[h.o], h.tail); retScore[h.i] += std::pow (10.0, h.tail / 10); }
    for (auto& [o, s] : sendScore) sends.push_back (o);
    std::vector<std::pair<double, int>> rs; for (auto& [i, s] : retScore) rs.push_back ({ s, i });
    std::sort (rs.rbegin(), rs.rend());
    for (size_t k = 0; k < rs.size() && k < 2; ++k) rets.push_back (rs[k].second);
    std::sort (rets.begin(), rets.end());
    if (sends.empty() || sends.size() > 2 || rets.empty())
    {
        out ("ROUTING: could not identify the RSP-550 (" + String ((int) sends.size()) + " candidate sends, " + String ((int) rets.size()) + " returns). Stopping.");
        adm.removeAudioCallback (&pr); return 4;
    }
    }
    if (sends.size() == 1) sends.push_back (sends[0]);
    if (rets.size() == 1) rets.push_back (rets[0]);
    out ("ROUTING: RSP-550 fed from outputs " + String (sends[0] + 1) + "/" + String (sends[1] + 1) + ", returns on inputs " + String (rets[0] + 1) + "/" + String (rets[1] + 1));

    // ---- Capture
    const auto stim = makeStimulus (fs);
    {
        std::vector<std::vector<float>> st { stim.L, stim.R };
        writeWav (capDir.getChildFile ("stimulus.wav"), st, fs);
        capDir.getChildFile ("stimulus.txt").replaceWithText (stim.markers.joinIntoString ("\n") + "\nsends " + String (sends[0] + 1) + " " + String (sends[1] + 1)
                                                              + "\nreturns " + String (rets[0] + 1) + " " + String (rets[1] + 1) + "\n");
    }
    out ("== Capturing programs " + String (first) + "-" + String (last) + " (" + String (stim.L.size() / fs, 1) + " s each)");
    String index;
    int done = 0, failed = 0;
    const double tStart = Time::getMillisecondCounterHiRes();
    for (auto& p : bank)
    {
        if (p.number < first || p.number > last) continue;
        if (usePC ? ! selectPC (p) : ! loadTemp (p.payload.data()))
        {
            ++failed; out ("  " + String (p.number).paddedLeft (' ', 3) + " " + p.name + ": " + (usePC ? String ("program change did not select it (edit buffer differs), skipped") : String ("edit buffer did not take the program, skipped")));
            if (done == 0 && failed >= 3) { out ("The unit is not accepting edit-buffer writes. Stopping."); break; }
            continue;
        }
        pr.setup ((int) stim.L.size(), { sends[0], sends[1] }, { rets[0], rets[1] });
        pr.play[0] = stim.L; pr.play[1] = stim.R;
        if (! pr.runBlocking (fs)) { out ("audio stalled"); break; }
        float peak = 0; for (auto& c : pr.rec) for (float v : c) peak = std::max (peak, std::abs (v));
        const File wav = capDir.getChildFile (String (p.number).paddedLeft ('0', 3) + ".wav");
        writeWav (wav, pr.rec, fs);
        ++done;
        index << p.number << "\t" << p.name << "\talg " << (int) p.payload[0x11] << "\tpeak " << String (20 * std::log10 (peak + 1e-9), 1) << " dBFS\n";
        const double el = (Time::getMillisecondCounterHiRes() - tStart) / 1000.0;
        out ("  " + String (p.number).paddedLeft (' ', 3) + " " + p.name.paddedRight (' ', 16) + " alg " + String ((int) p.payload[0x11]).paddedLeft (' ', 2)
             + "  peak " + String (20 * std::log10 (peak + 1e-9), 1) + " dBFS" + (peak > 0.99f ? "  CLIPPED" : "")
             + "   [" + String (done) + " done, ~" + String ((int) (el / done * (std::min (last, 160) - first + 1 - done) / 60.0)) + " min left]");
        capDir.getChildFile ("index.txt").replaceWithText (index);
    }

    adm.removeAudioCallback (&pr);
    bool restored = false;
    if (usePC)
    {
        for (auto& p : bank) if (p.number <= 128 && std::equal (p.payload.begin(), p.payload.end(), original.data())) { restored = selectPC (p); break; }
    }
    else restored = loadTemp (original.data());
    out ("edit buffer restored to \"" + asciiName (original.data(), 16).trim() + "\": " + (restored ? "OK" : "could not confirm"));
    out ("captured " + String (done) + ", skipped " + String (failed));
    out ("== DONE");
    return 0;
}

// rsplab tone <out1> <out2> [hz] [dBFS]: steady sine on two outputs (1-based) until the window is closed,
// printing every input's level once a second, to help with patching.
struct ToneCb : public AudioIODeviceCallback
{
    int o1 = 2, o2 = 3; double ph = 0, inc = 0; float amp = 0.1f;
    std::vector<float> peak; std::mutex m;
    void audioDeviceIOCallbackWithContext (const float* const* in, int numIn, float* const* outp, int numOut, int n,
                                           const AudioIODeviceCallbackContext&) override
    {
        for (int c = 0; c < numOut; ++c) if (outp[c] != nullptr) std::fill (outp[c], outp[c] + n, 0.0f);
        for (int i = 0; i < n; ++i)
        {
            const float v = amp * (float) std::sin (ph); ph += inc; if (ph > 2 * MathConstants<double>::pi) ph -= 2 * MathConstants<double>::pi;
            if (o1 < numOut && outp[o1]) outp[o1][i] = v;
            if (o2 < numOut && outp[o2]) outp[o2][i] = v;
        }
        std::lock_guard<std::mutex> l (m);
        peak.resize ((size_t) numIn, 0.0f);
        for (int c = 0; c < numIn; ++c) if (in[c]) for (int i = 0; i < n; ++i) peak[(size_t) c] = std::max (peak[(size_t) c], std::abs (in[c][i]));
    }
    void audioDeviceAboutToStart (AudioIODevice*) override {}
    void audioDeviceStopped() override {}
};

static int runTone (int argc, char** argv)
{
    ToneCb cb;
    cb.o1 = (argc > 2 ? atoi (argv[2]) : 3) - 1; cb.o2 = (argc > 3 ? atoi (argv[3]) : 4) - 1;
    const double hz = argc > 4 ? atof (argv[4]) : 1000.0, db = argc > 5 ? atof (argv[5]) : -20.0;
    AudioDeviceManager adm;
    String devName; AudioIODeviceType* devType = nullptr;
    for (auto* t : adm.getAvailableDeviceTypes())
    {
        t->scanForDevices();
        for (auto& n : t->getDeviceNames (false)) if (n.containsIgnoreCase ("MHLink") && t->getDeviceNames (true).contains (n)) { devName = n; devType = t; }
    }
    if (devName.isEmpty()) { out ("MHLink not found"); return 3; }
    adm.setCurrentAudioDeviceType (devType->getTypeName(), true);
    AudioDeviceManager::AudioDeviceSetup setup;
    setup.outputDeviceName = setup.inputDeviceName = devName; setup.sampleRate = 48000; setup.bufferSize = 512;
    setup.useDefaultInputChannels = setup.useDefaultOutputChannels = false;
    setup.inputChannels.setRange (0, 32, true); setup.outputChannels.setRange (0, 32, true);
    const String err = adm.setAudioDeviceSetup (setup, true);
    if (err.isNotEmpty() || adm.getCurrentAudioDevice() == nullptr) { out ("could not open " + devName + ": " + err); return 3; }
    cb.inc = 2 * MathConstants<double>::pi * hz / adm.getCurrentAudioDevice()->getCurrentSampleRate();
    cb.amp = (float) std::pow (10.0, db / 20);
    adm.addAudioCallback (&cb);
    out ("Playing " + String (hz, 0) + " Hz at " + String (db, 0) + " dBFS on " + devName + " outputs " + String (cb.o1 + 1) + " & " + String (cb.o2 + 1)
         + ". Close this window (or press Ctrl-C) to stop.");
    out ("Inputs with signal (peak dBFS over the last second, shown when above -70):");
    for (;;)
    {
        Thread::sleep (1000);
        String line; std::vector<float> pk;
        { std::lock_guard<std::mutex> l (cb.m); pk = cb.peak; std::fill (cb.peak.begin(), cb.peak.end(), 0.0f); }
        for (size_t c = 0; c < pk.size(); ++c)
            if (pk[c] > 0.000316f) line << "in" << (int) (c + 1) << " " << String (20 * std::log10 (pk[c]), 1) << "   ";
        out (Time::getCurrentTime().toString (false, true, true, true) + "  " + (line.isEmpty() ? String ("(nothing above -70 dBFS)") : line));
    }
}

// rsplab loadtest <bank.syx>: how does the unit take edit-buffer writes? Reads the temp area, tries several
// writes and reads back after each, then restores. Never touches stored programs.
static int runLoadTest (int argc, char** argv)
{
    auto bank = loadBank (File { String (CharPointer_UTF8 (argv[2])) });
    if (bank.empty()) { out ("no bank"); return 1; }
    Collector col;
    auto inInfo = MidiInput::getAvailableDevices(); auto outInfo = MidiOutput::getAvailableDevices();
    std::vector<std::unique_ptr<MidiInput>> ins;
    for (int i = 0; i < inInfo.size(); ++i) { auto mi = MidiInput::openDevice (inInfo[i].identifier, &col); if (mi) { col.portOf[mi.get()] = i; mi->start(); } ins.push_back (std::move (mi)); }
    std::unique_ptr<MidiOutput> mo; int dev = -1;
    for (int o = 0; o < outInfo.size() && dev < 0; ++o)
    {
        auto m = MidiOutput::openDevice (outInfo[o].identifier); if (! m) continue;
        for (int d = 0; d < 16 && dev < 0; ++d)
        {
            const size_t before = col.count(); m->sendMessageNow (rq1 (d, 0x03, 0x00, 0x00, 16));
            for (int w = 0; w < 30 && col.count() == before; ++w) Thread::sleep (10);
            Thread::sleep (60);
            for (auto& r : col.since (before)) if (isDT1 (r.bytes)) dev = r.bytes[2];
        }
        if (dev >= 0) { mo = std::move (m); out ("unit on '" + outInfo[o].name + "' dev " + String (dev)); }
    }
    if (dev < 0) { out ("no unit"); return 2; }
    auto readTemp = [&] () -> std::vector<uint8>
    {
        const size_t before = col.count(); mo->sendMessageNow (rq1 (dev, 0x02, 0x00, 0x00, 0x61));
        std::vector<uint8> data; const double t0 = Time::getMillisecondCounterHiRes();
        while (Time::getMillisecondCounterHiRes() - t0 < 1500 && data.size() < 0x61)
        {
            Thread::sleep (5); data.clear();
            for (auto& r : col.since (before)) if (isDT1 (r.bytes) && r.bytes[5] == 2 && r.bytes[6] == 0) data.insert (data.end(), r.bytes.begin() + 8, r.bytes.end() - 2);
        }
        return data;
    };
    auto report = [&] (const String& what, const std::vector<uint8>& got, const uint8* want, int n)
    {
        int nd = 0; String s;
        for (int k = 0; k < n && k < (int) got.size(); ++k) if (got[(size_t) k] != want[k]) { ++nd; if (nd <= 10) s << String::toHexString (k) << ":" << (int) want[k] << "->" << (int) got[(size_t) k] << " "; }
        out (what + ": read back " + String ((int) got.size()) + " bytes, name \"" + (got.size() >= 16 ? asciiName (got.data(), 16).trim() : String()) + "\", "
             + String (nd) + " of " + String (n) + " bytes differ from what was sent  " + s);
    };
    // echo: does the unit send anything back after a DT1 (error, ack)?
    auto sendAndWatch = [&] (const MidiMessage& m, const String& what)
    {
        const size_t before = col.count(); mo->sendMessageNow (m); Thread::sleep (300);
        for (auto& r : col.since (before)) out ("  (unit sent after " + what + ": " + hex (r.bytes) + ")");
    };
    const auto orig = readTemp();
    out ("edit buffer: \"" + asciiName (orig.data(), 16).trim() + "\", " + String ((int) orig.size()) + " bytes: " + hex (orig, 0x61));
    const auto& p = bank[0];
    out ("bank program 1: \"" + p.name + "\" " + hex (std::vector<uint8> (p.payload.begin(), p.payload.end()), 96));
    const uint8 zero = 0;

    out ("A. 96 bytes to 02 00 00, then sound change 02 00 60");
    sendAndWatch (dt1 (dev, 2, 0, 0, p.payload.data(), 96), "A data"); sendAndWatch (dt1 (dev, 2, 0, 0x60, &zero, 1), "A sound change");
    Thread::sleep (300); report ("A", readTemp(), p.payload.data(), 96);

    out ("B. 97 bytes to 02 00 00 (data + sound change byte in one message)");
    { std::vector<uint8> d (p.payload.begin(), p.payload.end()); d.push_back (0); sendAndWatch (dt1 (dev, 2, 0, 0, d.data(), 97), "B"); }
    Thread::sleep (300); report ("B", readTemp(), p.payload.data(), 96);

    out ("C. one byte: name character 1 = 'Z' at 02 00 00");
    { const uint8 z = 'Z'; sendAndWatch (dt1 (dev, 2, 0, 0, &z, 1), "C"); }
    Thread::sleep (300); { auto t = readTemp(); out ("C: first name byte now " + (t.empty() ? String ("?") : String ((int) t[0])) + " (90 = Z)"); }

    out ("D. one parameter byte: 02 00 14 (Parameter 1) = its current value + 1, then sound change");
    if (orig.size() > 0x14) { const uint8 v = (uint8) ((orig[0x14] + 1) & 0x7F); sendAndWatch (dt1 (dev, 2, 0, 0x14, &v, 1), "D"); sendAndWatch (dt1 (dev, 2, 0, 0x60, &zero, 1), "D sound change");
        Thread::sleep (300); auto t = readTemp(); out ("D: parameter 1 was " + String ((int) orig[0x14]) + ", now " + (t.size() > 0x14 ? String ((int) t[0x14]) : String ("?"))); }

    out ("E. same as A, but slowly: 96 single-byte messages 20 ms apart");
    for (int k = 0; k < 96; ++k) { mo->sendMessageNow (dt1 (dev, 2, 0, k, p.payload.data() + k, 1)); Thread::sleep (20); }
    mo->sendMessageNow (dt1 (dev, 2, 0, 0x60, &zero, 1)); Thread::sleep (400);
    report ("E", readTemp(), p.payload.data(), 96);

    out ("Restoring the edit buffer");
    mo->sendMessageNow (dt1 (dev, 2, 0, 0, orig.data(), 96)); Thread::sleep (100); mo->sendMessageNow (dt1 (dev, 2, 0, 0x60, &zero, 1)); Thread::sleep (400);
    report ("restore", readTemp(), orig.data(), 96);
    out ("== DONE");
    return 0;
}

// rsplab blindwrite <bank.syx>: for Bulk Load "Waiting" mode, where the unit doesn't answer requests. Sends bank
// program 1 to the TEMPORARY area only (02 00 00 + sound change 02 00 60) on the port named "USB Midi", device 0,
// then tries to read the edit buffer back. Never addresses stored programs.
static int runBlindWrite (int argc, char** argv)
{
    auto bank = loadBank (File { String (CharPointer_UTF8 (argv[2])) });
    if (bank.empty()) { out ("no bank"); return 1; }
    Collector col;
    auto inInfo = MidiInput::getAvailableDevices(); auto outInfo = MidiOutput::getAvailableDevices();
    std::vector<std::unique_ptr<MidiInput>> ins;
    for (int i = 0; i < inInfo.size(); ++i) { auto mi = MidiInput::openDevice (inInfo[i].identifier, &col); if (mi) { col.portOf[mi.get()] = i; mi->start(); } ins.push_back (std::move (mi)); }
    std::unique_ptr<MidiOutput> mo;
    for (auto& o : outInfo) if (o.name.containsIgnoreCase ("USB Midi")) { mo = MidiOutput::openDevice (o.identifier); out ("sending on '" + o.name + "', device 0"); break; }
    if (! mo) { out ("USB Midi port not found"); return 2; }
    const int dev = 0; const uint8 zero = 0;
    const auto& p = bank[0];
    out ("writing \"" + p.name + "\" to the edit buffer (02 00 00) + sound change");
    size_t before = col.count();
    mo->sendMessageNow (dt1 (dev, 2, 0, 0, p.payload.data(), 96)); Thread::sleep (150);
    mo->sendMessageNow (dt1 (dev, 2, 0, 0x60, &zero, 1)); Thread::sleep (800);
    for (auto& r : col.since (before)) out ("  unit sent: " + hex (r.bytes));
    before = col.count();
    mo->sendMessageNow (rq1 (dev, 2, 0, 0, 0x60)); Thread::sleep (800);
    bool any = false;
    for (auto& r : col.since (before)) { any = true; out ("  read-back: " + hex (r.bytes, 24) + (r.bytes.size() > 24 ? "  name \"" + asciiName (r.bytes.data() + 8, 16).trim() + "\"" : String())); }
    if (! any) out ("  no read-back (expected in Bulk Load mode). Now leave Bulk Load and run the loadtest again to see if the edit buffer took it.");
    out ("== DONE");
    return 0;
}

// rsplab run2 <labdir> <backup.syx> <out1> <out2> <in1> <in2>
//   a) programs 56 and 67 by Program Change, recorded even if the edit buffer differs from the backup (it is saved)
//   b) converter reference: 1 kHz steps -40..0 dBFS through program 67 (direct path only) -> where the unit clips
//   c) gate thresholds: 1 kHz bursts -60..-10 dBFS through programs 38, 39, 40 -> where each gate opens
//   d) program 160: waits for you to select it on the front panel (Return), then records it
// Nothing is written to the unit.
static int runRun2 (int argc, char** argv)
{
    if (argc < 8) { out ("usage: rsplab run2 <labdir> <backup.syx> o1 o2 i1 i2"); return 1; }
    const File lab { String (CharPointer_UTF8 (argv[2])) };
    auto bank = loadBank (File { String (CharPointer_UTF8 (argv[3])) });
    const std::vector<int> sends { atoi (argv[4]) - 1, atoi (argv[5]) - 1 }, rets { atoi (argv[6]) - 1, atoi (argv[7]) - 1 };
    const File capDir = lab.getChildFile ("capture"); capDir.createDirectory();
    const double fs = 48000.0;
    out ("RSP-550 lab run 2, " + Time::getCurrentTime().toString (true, true));

    Collector col;
    auto inInfo = MidiInput::getAvailableDevices(); auto outInfo = MidiOutput::getAvailableDevices();
    std::vector<std::unique_ptr<MidiInput>> ins;
    for (int i = 0; i < inInfo.size(); ++i) { auto mi = MidiInput::openDevice (inInfo[i].identifier, &col); if (mi) { col.portOf[mi.get()] = i; mi->start(); } ins.push_back (std::move (mi)); }
    std::unique_ptr<MidiOutput> mo; int dev = -1;
    for (int o = 0; o < outInfo.size() && dev < 0; ++o)
    {
        auto m = MidiOutput::openDevice (outInfo[o].identifier); if (! m) continue;
        for (int d = 0; d < 16 && dev < 0; ++d)
        {
            const size_t before = col.count(); m->sendMessageNow (rq1 (d, 0x03, 0x00, 0x00, 16));
            for (int w = 0; w < 30 && col.count() == before; ++w) Thread::sleep (10);
            Thread::sleep (60);
            for (auto& r : col.since (before)) if (isDT1 (r.bytes)) dev = r.bytes[2];
        }
        if (dev >= 0) { mo = std::move (m); out ("MIDI: RSP-550 on '" + outInfo[o].name + "' device ID " + String (dev)); }
    }
    if (dev < 0) { out ("MIDI: no answer from the RSP-550 (is it on the normal play screen?)"); return 2; }
    auto readTemp = [&] () -> std::vector<uint8>
    {
        const size_t before = col.count(); mo->sendMessageNow (rq1 (dev, 2, 0, 0, 0x60));
        std::vector<uint8> data; const double t0 = Time::getMillisecondCounterHiRes();
        while (Time::getMillisecondCounterHiRes() - t0 < 1500 && data.size() < 96)
        {
            Thread::sleep (5); data.clear();
            for (auto& r : col.since (before)) if (isDT1 (r.bytes) && checksumOk (r.bytes) && r.bytes[5] == 2 && r.bytes[6] == 0) data.insert (data.end(), r.bytes.begin() + 8, r.bytes.end() - 2);
        }
        if (data.size() > 96) data.resize (96);
        return data;
    };
    auto selectPC = [&] (int number)
    {
        mo->sendMessageNow (MidiMessage::programChange (dev + 1, number % 128)); Thread::sleep (500);   // step away first
        mo->sendMessageNow (MidiMessage::programChange (dev + 1, number - 1)); Thread::sleep (800);
    };
    const auto original = readTemp();

    AudioDeviceManager adm; String devName; AudioIODeviceType* devType = nullptr;
    for (auto* t : adm.getAvailableDeviceTypes())
    { t->scanForDevices(); for (auto& n : t->getDeviceNames (false)) if (n.containsIgnoreCase ("MHLink") && t->getDeviceNames (true).contains (n)) { devName = n; devType = t; } }
    if (devName.isEmpty()) { out ("audio: MHLink not found"); return 3; }
    adm.setCurrentAudioDeviceType (devType->getTypeName(), true);
    AudioDeviceManager::AudioDeviceSetup setup;
    setup.outputDeviceName = setup.inputDeviceName = devName; setup.sampleRate = fs; setup.bufferSize = 512;
    setup.useDefaultInputChannels = setup.useDefaultOutputChannels = false;
    setup.inputChannels.setRange (0, 32, true); setup.outputChannels.setRange (0, 32, true);
    if (adm.setAudioDeviceSetup (setup, true).isNotEmpty() || adm.getCurrentAudioDevice() == nullptr) { out ("audio: could not open " + devName); return 3; }
    PlayRec pr; adm.addAudioCallback (&pr); Thread::sleep (500);
    out ("audio: " + devName + ", sends " + String (sends[0] + 1) + "/" + String (sends[1] + 1) + ", returns " + String (rets[0] + 1) + "/" + String (rets[1] + 1));

    const auto stim = makeStimulus (fs);
    auto recordStim = [&] (int number, const std::vector<uint8>& buf)
    {
        pr.setup ((int) stim.L.size(), sends, rets); pr.play[0] = stim.L; pr.play[1] = stim.R;
        if (! pr.runBlocking (fs)) { out ("audio stalled"); return; }
        writeWav (capDir.getChildFile (String (number).paddedLeft ('0', 3) + ".wav"), pr.rec, fs);
        MemoryOutputStream m; for (auto b : buf) m.writeByte ((char) b);
        capDir.getChildFile (String (number).paddedLeft ('0', 3) + "-editbuffer.bin").replaceWithData (m.getData(), m.getDataSize());
        float peak = 0; for (auto& c : pr.rec) for (float v : c) peak = std::max (peak, std::abs (v));
        out ("  recorded " + String (number) + " \"" + (buf.size() >= 16 ? asciiName (buf.data(), 16).trim() : String ("?")) + "\", peak " + String (20 * std::log10 (peak + 1e-9), 1) + " dBFS");
    };

    // a) 56 and 67
    out ("== a) programs 56 and 67");
    for (int number : { 56, 67 })
    {
        selectPC (number);
        const auto buf = readTemp();
        for (auto& p : bank) if (p.number == number)
        {
            int nd = 0; String where;
            for (size_t k = 0; k < 96 && k < buf.size(); ++k) if (buf[k] != p.payload[k]) { ++nd; if (nd <= 8) where << String::toHexString ((int) k) << ":" << (int) p.payload[k] << "->" << (int) buf[k] << " "; }
            out ("  " + String (number) + " " + p.name + ": edit buffer differs from the stored program in " + String (nd) + " bytes " + where);
        }
        recordStim (number, buf);
    }

    // b) converter reference through 67 (direct path only)
    out ("== b) converter reference (program 67, 1 kHz, -40..0 dBFS in 2 dB steps)");
    selectPC (67);
    {
        const int stepN = (int) (0.25 * fs), gapN = (int) (0.05 * fs);
        std::vector<double> levels; for (double db = -40; db <= 0.01; db += 2) levels.push_back (db);
        const int len = (int) levels.size() * (stepN + gapN) + (int) (0.3 * fs);
        pr.setup (len, sends, rets);
        for (size_t k = 0; k < levels.size(); ++k)
        {
            const double a = std::pow (10.0, levels[k] / 20);
            for (int i = 0; i < stepN; ++i)
            {
                const double fade = std::min ({ 1.0, i / (0.005 * fs), (stepN - 1 - i) / (0.005 * fs) });
                const float v = (float) (a * fade * std::sin (2 * MathConstants<double>::pi * 1000.0 * i / fs));
                pr.play[0][(size_t) ((int) k * (stepN + gapN) + i)] = v; pr.play[1][(size_t) ((int) k * (stepN + gapN) + i)] = v;
            }
        }
        if (pr.runBlocking (fs))
        {
            writeWav (capDir.getChildFile ("adc-ramp.wav"), pr.rec, fs);
            for (size_t k = 0; k < levels.size(); ++k)
            {
                const int a = (int) k * (stepN + gapN) + 1200 + 1300, b = a + 8000;   // skip fade + loop latency
                String line = "  out " + String (levels[k], 0).paddedLeft (' ', 3) + " dBFS:";
                for (int c = 0; c < 2; ++c)
                {
                    const auto& x = pr.rec[(size_t) c];
                    const double f1 = toneDb (x, fs, 1000, a, b);
                    double hp = 0; for (int h = 2; h <= 7; ++h) hp += std::pow (10.0, toneDb (x, fs, 1000.0 * h, a, b) / 10);
                    line << "  ch" << (c + 1) << " " << String (f1, 1) << " dBFS THD " << String (10 * std::log10 (hp + 1e-20) - f1, 1) << " dB";
                }
                out (line);
            }
        }
    }

    // c) gate thresholds
    out ("== c) gate thresholds (1 kHz bursts -60..-10 dBFS, 2 dB steps)");
    for (int number : { 38, 39, 40 })
    {
        selectPC (number);
        const int onN = (int) (0.4 * fs), offN = (int) (1.2 * fs);
        std::vector<double> levels; for (double db = -60; db <= -9.99; db += 2) levels.push_back (db);
        const int len = (int) levels.size() * (onN + offN);
        pr.setup (len, sends, rets);
        for (size_t k = 0; k < levels.size(); ++k)
        {
            const double a = std::pow (10.0, levels[k] / 20);
            for (int i = 0; i < onN; ++i)
            {
                const double fade = std::min ({ 1.0, i / (0.003 * fs), (onN - 1 - i) / (0.003 * fs) });
                const float v = (float) (a * fade * std::sin (2 * MathConstants<double>::pi * 1000.0 * i / fs));
                pr.play[0][(size_t) ((int) k * (onN + offN) + i)] = v; pr.play[1][(size_t) ((int) k * (onN + offN) + i)] = v;
            }
        }
        if (! pr.runBlocking (fs)) break;
        writeWav (capDir.getChildFile ("gate-" + String (number).paddedLeft ('0', 3) + ".wav"), pr.rec, fs);
        String line = "  " + String (number) + ": out level vs return-in (dB):";
        for (size_t k = 0; k < levels.size(); ++k)
        {
            const int a = (int) k * (onN + offN) + 2500, b = a + onN - 3000;
            const double g = 0.5 * (toneDb (pr.rec[0], fs, 1000, a, b) + toneDb (pr.rec[1], fs, 1000, a, b)) - levels[k];
            line << " " << String (levels[k], 0) << ":" << String (g, 1);
        }
        out (line);
    }

    // d) program 160
    out ("== d) program 160: select program 160 on the RSP-550 front panel now, then press Return here");
    std::string dummy; std::getline (std::cin, dummy);
    {
        const auto buf = readTemp();
        out ("  edit buffer now: \"" + (buf.size() >= 16 ? asciiName (buf.data(), 16).trim() : String ("?")) + "\"");
        recordStim (160, buf);
    }

    adm.removeAudioCallback (&pr);
    for (auto& p : bank) if (original.size() == 96 && p.number <= 128 && std::equal (p.payload.begin(), p.payload.end(), original.data())) { selectPC (p.number); out ("unit set back to program " + String (p.number) + " " + p.name); break; }
    out ("== DONE");
    return 0;
}

// rsplab run3 <labdir> <backup.syx> <tests.syx> <restore.syx> o1 o2 i1 i2
//   Writes the test programs in tests.syx (slots 121-128, copies of 21-28) while the unit is in Bulk Load,
//   records them, records the Vocoder (100) with a held MIDI note, sweeps the two new gate thresholds,
//   then writes restore.syx back (Bulk Load again) and verifies every slot against the backup.
static int runRun3 (int argc, char** argv)
{
    if (argc < 10) { out ("usage: rsplab run3 <labdir> <backup.syx> <tests.syx> <restore.syx> o1 o2 i1 i2"); return 1; }
    const File lab { String (CharPointer_UTF8 (argv[2])) };
    auto bank = loadBank (File { String (CharPointer_UTF8 (argv[3])) });
    auto tests = loadBank (File { String (CharPointer_UTF8 (argv[4])) });
    auto restore = loadBank (File { String (CharPointer_UTF8 (argv[5])) });
    const std::vector<int> sends { atoi (argv[6]) - 1, atoi (argv[7]) - 1 }, rets { atoi (argv[8]) - 1, atoi (argv[9]) - 1 };
    const File capDir = lab.getChildFile ("capture"); capDir.createDirectory();
    const double fs = 48000.0;
    auto waitReturn = [] (const String& what) { out (">>> " + what + " Then press Return here."); std::string s; std::getline (std::cin, s); };
    out ("RSP-550 lab run 3, " + Time::getCurrentTime().toString (true, true) + ": " + String ((int) tests.size()) + " test programs, " + String ((int) restore.size()) + " to restore");
    if (tests.empty() || restore.size() != tests.size()) { out ("test/restore files don't match"); return 1; }
    for (auto& t : tests) if (t.number < 121 || t.number > 128) { out ("refusing: test program outside slots 121-128"); return 1; }

    Collector col;
    auto inInfo = MidiInput::getAvailableDevices(); auto outInfo = MidiOutput::getAvailableDevices();
    std::vector<std::unique_ptr<MidiInput>> ins;
    for (int i = 0; i < inInfo.size(); ++i) { auto mi = MidiInput::openDevice (inInfo[i].identifier, &col); if (mi) { col.portOf[mi.get()] = i; mi->start(); } ins.push_back (std::move (mi)); }
    std::unique_ptr<MidiOutput> mo; int dev = -1;
    for (int o = 0; o < outInfo.size() && dev < 0; ++o)
    {
        auto m = MidiOutput::openDevice (outInfo[o].identifier); if (! m) continue;
        for (int d = 0; d < 16 && dev < 0; ++d)
        {
            const size_t before = col.count(); m->sendMessageNow (rq1 (d, 0x03, 0x00, 0x00, 16));
            for (int w = 0; w < 30 && col.count() == before; ++w) Thread::sleep (10);
            Thread::sleep (60);
            for (auto& r : col.since (before)) if (isDT1 (r.bytes)) dev = r.bytes[2];
        }
        if (dev >= 0) { mo = std::move (m); out ("MIDI: RSP-550 on '" + outInfo[o].name + "' device ID " + String (dev)); }
    }
    if (dev < 0) { out ("MIDI: no answer from the RSP-550 (it must be on the normal play screen to start)"); return 2; }
    auto readArea = [&] (int a0, int a1, int a2, int size) -> std::vector<uint8>
    {
        for (int attempt = 0; attempt < 3; ++attempt)
        {
            const size_t before = col.count(); mo->sendMessageNow (rq1 (dev, a0, a1, a2, size));
            std::vector<uint8> data; const double t0 = Time::getMillisecondCounterHiRes();
            while (Time::getMillisecondCounterHiRes() - t0 < 1500 && (int) data.size() < size)
            {
                Thread::sleep (5); data.clear();
                for (auto& r : col.since (before)) if (isDT1 (r.bytes) && checksumOk (r.bytes) && r.bytes[5] == a0 && r.bytes[6] == a1) data.insert (data.end(), r.bytes.begin() + 8, r.bytes.end() - 2);
            }
            if ((int) data.size() >= size) { data.resize ((size_t) size); return data; }
        }
        return {};
    };
    auto slotData = [&] (int n) { return readArea (n <= 128 ? 3 : 4, n <= 128 ? n - 1 : n - 129, 0, 0x60); };

    // 0. the slots must still hold what the restore file will put back
    for (auto& r : restore)
    {
        auto cur = slotData (r.number);
        if (cur.size() != 96 || ! std::equal (cur.begin(), cur.end(), r.payload.begin())) { out ("slot " + String (r.number) + " doesn't match the backup - stopping before writing anything"); return 3; }
    }
    out ("slots 121-128 match the backup; it will be written back at the end");
    const auto original = readArea (2, 0, 0, 0x60);

    auto bulkWrite = [&] (const std::vector<BankProgram>& progs)
    {
        for (auto& p : progs) { mo->sendMessageNow (dt1 (dev, 3, p.number - 1, 0, p.payload.data(), 96)); Thread::sleep (200); }
    };
    // 1. write the tests
    waitReturn ("On the RSP-550, start Bulk Load so it shows 'Waiting'.");
    bulkWrite (tests);
    waitReturn ("Leave Bulk Load on the RSP-550 (back to the normal play screen).");
    int ok = 0;
    for (auto& t : tests) { auto cur = slotData (t.number); if (cur.size() == 96 && std::equal (cur.begin(), cur.end(), t.payload.begin())) ++ok; else out ("  slot " + String (t.number) + " did not take the test program"); }
    out ("test programs stored: " + String (ok) + " of " + String ((int) tests.size()));

    // audio
    AudioDeviceManager adm; String devName; AudioIODeviceType* devType = nullptr;
    for (auto* t : adm.getAvailableDeviceTypes())
    { t->scanForDevices(); for (auto& n : t->getDeviceNames (false)) if (n.containsIgnoreCase ("MHLink") && t->getDeviceNames (true).contains (n)) { devName = n; devType = t; } }
    bool audioOk = devName.isNotEmpty();
    PlayRec pr;
    if (audioOk)
    {
        adm.setCurrentAudioDeviceType (devType->getTypeName(), true);
        AudioDeviceManager::AudioDeviceSetup setup;
        setup.outputDeviceName = setup.inputDeviceName = devName; setup.sampleRate = fs; setup.bufferSize = 512;
        setup.useDefaultInputChannels = setup.useDefaultOutputChannels = false;
        setup.inputChannels.setRange (0, 32, true); setup.outputChannels.setRange (0, 32, true);
        audioOk = adm.setAudioDeviceSetup (setup, true).isEmpty() && adm.getCurrentAudioDevice() != nullptr;
        if (audioOk) { adm.addAudioCallback (&pr); Thread::sleep (500); }
    }
    if (! audioOk) out ("audio: could not open MHLink - skipping recordings (the slots are still restored)");
    const auto stim = makeStimulus (fs);
    auto selectPC = [&] (int number)
    {
        mo->sendMessageNow (MidiMessage::programChange (dev + 1, number % 128)); Thread::sleep (500);
        mo->sendMessageNow (MidiMessage::programChange (dev + 1, number - 1)); Thread::sleep (800);
    };
    auto record = [&] (const String& name, bool note)
    {
        pr.setup ((int) stim.L.size(), sends, rets); pr.play[0] = stim.L; pr.play[1] = stim.R;
        if (note) mo->sendMessageNow (MidiMessage::noteOn (dev + 1, 48, (uint8) 100));
        const bool done = pr.runBlocking (fs);
        if (note) mo->sendMessageNow (MidiMessage::noteOff (dev + 1, 48));
        if (! done) { out ("audio stalled"); return; }
        writeWav (capDir.getChildFile (name + ".wav"), pr.rec, fs);
        const auto buf = readArea (2, 0, 0, 0x60);
        MemoryOutputStream m; for (auto b : buf) m.writeByte ((char) b);
        capDir.getChildFile (name + "-editbuffer.bin").replaceWithData (m.getData(), m.getDataSize());
        float peak = 0; for (auto& c : pr.rec) for (float v : c) peak = std::max (peak, std::abs (v));
        out ("  recorded " + name + " \"" + (buf.size() >= 16 ? asciiName (buf.data(), 16).trim() : String ("?")) + "\", peak " + String (20 * std::log10 (peak + 1e-9), 1) + " dBFS");
    };
    if (audioOk)
    {
        out ("== recordings");
        for (auto& t : tests) { selectPC (t.number); record ("test-" + String (t.number), false); }
        selectPC (100); record ("100-note48", true);
        out ("== gate thresholds for 126 (Thr 70) and 127 (Thr 30)");
        for (int number : { 126, 127 })
        {
            selectPC (number);
            const int onN = (int) (0.4 * fs), offN = (int) (1.2 * fs);
            std::vector<double> levels; for (double db = -60; db <= -9.99; db += 2) levels.push_back (db);
            pr.setup ((int) levels.size() * (onN + offN), sends, rets);
            for (size_t k = 0; k < levels.size(); ++k)
            {
                const double a = std::pow (10.0, levels[k] / 20);
                for (int i = 0; i < onN; ++i)
                {
                    const double fade = std::min ({ 1.0, i / (0.003 * fs), (onN - 1 - i) / (0.003 * fs) });
                    const float v = (float) (a * fade * std::sin (2 * MathConstants<double>::pi * 1000.0 * i / fs));
                    pr.play[0][(size_t) ((int) k * (onN + offN) + i)] = v; pr.play[1][(size_t) ((int) k * (onN + offN) + i)] = v;
                }
            }
            if (! pr.runBlocking (fs)) break;
            writeWav (capDir.getChildFile ("gate-" + String (number) + ".wav"), pr.rec, fs);
            String line = "  " + String (number) + " tail after burst (dBFS):";
            for (size_t k = 0; k < levels.size(); ++k)
            {
                const int a = (int) k * (onN + offN) + onN + 1179 + 480, b = a + 14400;
                line << " " << String (levels[k], 0) << ":" << String (rmsDb (pr.rec[0], a, b), 0);
            }
            out (line);
        }
        adm.removeAudioCallback (&pr);
    }

    // 2. restore
    waitReturn ("Restoring slots 121-128: on the RSP-550, start Bulk Load again so it shows 'Waiting'.");
    bulkWrite (restore);
    waitReturn ("Leave Bulk Load on the RSP-550 (back to the normal play screen).");
    int good = 0;
    for (auto& r : restore) { auto cur = slotData (r.number); if (cur.size() == 96 && std::equal (cur.begin(), cur.end(), r.payload.begin())) ++good; else out ("  slot " + String (r.number) + " NOT restored - run this again or reload the backup"); }
    out ("restored: " + String (good) + " of " + String ((int) restore.size()) + (good == (int) restore.size() ? " - the unit matches the 4:18 backup again" : ""));
    for (auto& p : bank) if (original.size() == 96 && p.number <= 128 && std::equal (p.payload.begin(), p.payload.end(), original.data())) { selectPC (p.number); out ("unit set back to program " + String (p.number) + " " + p.name); break; }
    out ("== DONE");
    return 0;
}
