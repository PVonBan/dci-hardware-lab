// rsplab loopcheck <labdir> [o1 o2 i1 i2]: tests the audio loop through the RSP-550 without touching the unit's memory
// (no MIDI, no SysEx). Plays on the interface sends (default 3/4) and records the returns (default 5/6):
//   1. 5 s silence            each return's own floor: the unit's idle hiss is about -88 to -91 dBFS; a dead return or
//                              unplugged cable reads lower (about -110 dBFS)
//   2. 1 kHz -20 dBFS left only, then right only, then both (3 s each): each path carries signal
//   3. 60 s pink-ish noise -20 dBFS on both sends ("wiggle test"): move the cables gently while it plays; any 0.25 s block
//      where one return falls below -97 dBFS while the other carries signal is a dropout
// Writes capture/loopcheck-<time>.wav and prints PASS or FAIL per return. (Added 2026-11-03 after run 9 lost 38
// captures to a left return that cut in and out.)
static int runLoopCheck (int argc, char** argv)
{
    if (argc < 3) { out ("usage: rsplab loopcheck <labdir> [o1 o2 i1 i2]"); return 1; }
    const File lab { String (CharPointer_UTF8 (argv[2])) };
    const std::vector<int> sends { (argc > 6 ? atoi (argv[3]) : 3) - 1, (argc > 6 ? atoi (argv[4]) : 4) - 1 },
                           rets  { (argc > 6 ? atoi (argv[5]) : 5) - 1, (argc > 6 ? atoi (argv[6]) : 6) - 1 };
    const double fs = 48000.0;
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

    // stimulus
    std::vector<float> L, R; Random rng (7);
    auto pad = [&] (double s) { L.resize (L.size() + (size_t) (s * fs), 0.0f); R.resize (L.size(), 0.0f); };
    auto tone = [&] (bool l, bool r, double s)
    {
        const int n = (int) (s * fs); const double a = 0.1;
        for (int i = 0; i < n; ++i)
        {
            const double f = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.01 * fs) });
            const float v = (float) (a * f * std::sin (2 * MathConstants<double>::pi * 1000.0 * i / fs));
            L.push_back (l ? v : 0.0f); R.push_back (r ? v : 0.0f);
        }
    };
    struct Seg { String name; int a, b; };
    std::vector<Seg> seg;
    auto mark = [&] (const String& nm, double s, std::function<void()> fn) { const int a = (int) L.size(); fn(); seg.push_back ({ nm, a, a + (int) (s * fs) }); };
    pad (0.5);
    mark ("silence", 5.0, [&] { pad (5.0); });
    mark ("tone left only", 3.0, [&] { tone (true, false, 3.0); }); pad (0.5);
    mark ("tone right only", 3.0, [&] { tone (false, true, 3.0); }); pad (0.5);
    mark ("tone both", 3.0, [&] { tone (true, true, 3.0); }); pad (0.5);
    mark ("noise (wiggle test)", 60.0, [&] {
        const int n = (int) (60.0 * fs); float bL = 0, bR = 0;
        for (int i = 0; i < n; ++i)
        {
            const double f = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.01 * fs) });
            bL = 0.97f * bL + 0.03f * (2 * rng.nextFloat() - 1); bR = 0.97f * bR + 0.03f * (2 * rng.nextFloat() - 1);
            L.push_back ((float) (f * 0.1 * (0.5 * (2 * rng.nextFloat() - 1) + 4.0 * bL)));
            R.push_back ((float) (f * 0.1 * (0.5 * (2 * rng.nextFloat() - 1) + 4.0 * bR)));
        }
    });
    pad (1.0);

    out (">>> The test takes about 80 s. During the last 60 s (noise), gently move both cables between the RSP-550 outputs");
    out ("    and the interface inputs, at both ends. Keep the monitors low.");
    pr.setup ((int) L.size(), sends, rets); pr.play[0] = L; pr.play[1] = R;
    pr.pos.store (0);
    const double t0 = Time::getMillisecondCounterHiRes();
    while (pr.pos.load() < pr.len) { Thread::sleep (5); if (Time::getMillisecondCounterHiRes() - t0 > (pr.len / fs + 5) * 1000) { out ("audio stalled"); return 4; } }
    pr.pos.store (-1);
    adm.removeAudioCallback (&pr);
    const File cap = lab.getChildFile ("capture").getChildFile ("loopcheck-" + Time::getCurrentTime().formatted ("%Y%m%d-%H%M%S") + ".wav");
    writeWav (cap, pr.rec, fs);

    const int lat = 1179;   // loop latency (run 1)
    auto rmsDb = [&] (int c, int a, int b) { double e = 0; a += lat; b = std::min (b + lat, (int) pr.rec[(size_t) c].size()); for (int i = a; i < b; ++i) e += (double) pr.rec[(size_t) c][(size_t) i] * pr.rec[(size_t) c][(size_t) i]; return 10 * std::log10 (e / std::max (1, b - a) + 1e-30); };
    bool ok[2] = { true, true };
    const char* nm[2] = { "LEFT ", "RIGHT" };
    for (auto& s : seg)
    {
        out ("  " + s.name.paddedRight (' ', 22) + "  left " + String (rmsDb (0, s.a, s.b), 1) + " dBFS   right " + String (rmsDb (1, s.a, s.b), 1) + " dBFS");
    }
    for (int c = 0; c < 2; ++c)
    {
        const double fl = rmsDb (c, seg[0].a + (int) fs, seg[0].b);
        if (fl < -100.0) { out (String ("  ") + nm[c] + " return: floor " + String (fl, 1) + " dBFS is below the unit's own hiss - nothing is connected, or the path is dead"); ok[c] = false; }
        if (rmsDb (c, seg[3].a, seg[3].b) < -40.0) { out (String ("  ") + nm[c] + " return: no tone with both sends playing"); ok[c] = false; }
    }
    // dropouts in the noise part, 0.25 s blocks
    const int blk = (int) (0.25 * fs); int drops[2] = { 0, 0 }; String where[2];
    for (int a = seg[4].a + (int) (0.5 * fs); a + blk <= seg[4].b - (int) (0.5 * fs); a += blk)
    {
        const double e0 = rmsDb (0, a, a + blk), e1 = rmsDb (1, a, a + blk);
        for (int c = 0; c < 2; ++c)
        {
            const double me = c == 0 ? e0 : e1, other = c == 0 ? e1 : e0;
            if (me < other - 20.0)   // the same noise level goes into both sends: a 20 dB gap is a broken path
            { ++drops[c]; if (where[c].length() < 60) where[c] << String ((a - seg[4].a) / fs, 1) << "s "; }
        }
    }
    for (int c = 0; c < 2; ++c)
    {
        if (drops[c] > 0) { out (String ("  ") + nm[c] + " return: " + String (drops[c]) + " dropouts during the wiggle test, at " + where[c]); ok[c] = false; }
        out (String ("  ") + nm[c] + " return: " + (ok[c] ? "PASS" : "FAIL"));
    }
    out ("saved " + cap.getFullPathName());
    out (ok[0] && ok[1] ? "LOOP OK" : "LOOP PROBLEM");
    return ok[0] && ok[1] ? 0 : 5;
}
