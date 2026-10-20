// rsplab run4 <labdir> <backup.syx> <plan.txt> <restore.syx> <testsA.syx> <testsB.syx> <testsC.syx> o1 o2 i1 i2 [capture-subfolder]
//   (an empty tests file skips that batch; later runs reuse this mode with their own plan and sub-folder)
//
// The full measurement battery. Each batch writes up to 28 test programs to the "*" copy slots 101-128 (Bulk Load,
// the user presses the buttons), records every line of plan.txt for that batch with the stimulus its kind asks for,
// and moves on. After the last batch the original 101-128 are written back from restore.syx and verified.
//
// Batch Z (run 9) plays programs by program change after C: repeat references at the end of the session, so drift
// can be measured. A capture that clips is recorded again at once with the stimulus 10 dB lower ("-m10"); a second
// recording of the same program and kind never overwrites the first ("-rep2").
// Run 10: kind "wav:<name>" plays <plan dir>/stim/<name>.wav (the reference-lab battery, made by make_run10.py) at
// that file's own sample rate; the interface is switched to that rate for the capture (and back to 48 kHz after).
// A rate the interface refuses is logged and the line skipped. Markers come from <name>.txt next to the WAV.
// plan.txt: batch <tab> program <tab> kind <tab> description. Kinds:
//   filelo / file2lo / file3lo  listening material 10 dB below "file": ab-source.wav / ab-source2.wav /
//           ab-source3.wav from the lab folder (or a synthetic phrase)
//   std     impulses + ESS + 1 kHz steps (the run 1-3 stimulus, -10 dB)
//   conv    converter battery (noise floor, low-level tones, THD grid, IMD, sweep to 23.9 kHz, foldback tones,
//           one-sided tones for crosstalk, independent noise for decorrelation). Actual levels, not -10 dB.
//   tone    500 Hz, -12 dBFS, 10 s: instantaneous delay / AM / FM tracking (chorus, flanger, delay mod, rotary)
//   tone440 440 Hz 4 s, click train, 100 Hz-4 kHz chirp: pitch-shifter splice and crossfade
//   rotsw   1 kHz 16 s; CC1 0 -> 127 at 4 s -> 0 at 10 s: rotary speed change and rise/fall
//   fb      50 ms 1 kHz burst then 12 s: feedback decay / limiting
//   gate    3 x 400 ms bursts, 2 x 20 ms bursts: gate attack/hold/release
//   gsweep  1 kHz bursts -60..-10 dBFS: gate threshold
//   cc      noise bursts; CC1 stepped (aftertouch 127), then aftertouch stepped (CC1 127)
//   pb      noise bursts; pitch bend stepped
//   vel     noise bursts; each one preceded by a note-on with stepped velocity
//   enh     multitone at four levels, 1 kHz at three levels, white noise: enhancer level dependence
//   note    std stimulus with MIDI note 48 held (vocoder)
//   pcgap   1 kHz 8 s; program change to 4 at 2 s and back to 1 at 5 s: switching gap / crossfade
// Every stimulus is saved once as run4/stim-<kind>.wav with stim-<kind>.txt markers; MIDI events actually sent
// (sample position of the audio callback at send time) go to <name>-events.txt.
#pragma once
#include <set>
#include <functional>

struct Event { int at; MidiMessage msg; String label; };
struct Stim4 { std::vector<float> L, R; StringArray markers; std::vector<Event> events; };

static Stim4 makeStim4 (const String& kind, double fs, int ch)
{
    Stim4 s; auto& L = s.L; auto& R = s.R;
    const double twoPi = 2 * MathConstants<double>::pi;
    auto at = [&] () { return (int) L.size(); };
    auto pad = [&] (double sec) { L.resize (L.size() + (size_t) (sec * fs), 0.0f); R.resize (L.size(), 0.0f); };
    auto tone = [&] (double f, double db, double sec, bool left = true, bool right = true, double ramp = 0.005)
    {
        const int n = (int) (sec * fs); const double a = std::pow (10.0, db / 20);
        for (int i = 0; i < n; ++i)
        {
            const double fade = std::min ({ 1.0, i / (ramp * fs), (n - 1 - i) / (ramp * fs) });
            const float v = (float) (a * fade * std::sin (twoPi * f * i / fs));
            L.push_back (left ? v : 0.0f); R.push_back (right ? v : 0.0f);
        }
    };
    auto mark = [&] (const String& what, double sec) { s.markers.add (what + " " + String (at()) + " " + String ((int) (sec * fs))); };
    Random rng (1234);
    auto noise = [&] (double db, double sec, bool independent)
    {
        const int n = (int) (sec * fs); const double a = std::pow (10.0, db / 20) * std::sqrt (3.0);   // uniform: rms = a/sqrt3
        for (int i = 0; i < n; ++i)
        {
            const double fade = std::min ({ 1.0, i / (0.005 * fs), (n - 1 - i) / (0.005 * fs) });
            const float l = (float) (a * fade * (2 * rng.nextDouble() - 1));
            const float r = independent ? (float) (a * fade * (2 * rng.nextDouble() - 1)) : l;
            L.push_back (l); R.push_back (r);
        }
    };
    auto ev = [&] (int sample, MidiMessage m, const String& label) { s.events.push_back ({ sample, m, label }); };

    if (kind == "conv")
    {
        pad (0.25);
        mark ("silence", 3.0); pad (3.0);
        for (double db : { -100.0, -90.0, -80.0, -70.0, -60.0, -50.0, -40.0 }) { mark ("low1k " + String (db, 0), 1.0); tone (1000, db, 1.0); pad (0.2); }
        for (double f : { 50.0, 100.0, 1000.0, 5000.0, 10000.0 })
            for (double db : { -40.0, -20.0, -10.0, -6.0, -3.0 }) { mark ("thd " + String (f, 0) + " " + String (db, 0), 0.6); tone (f, db, 0.6); pad (0.1); }
        {   // CCIF 19k + 20k, 1:1, each -12 dBFS
            const int n = (int) (2 * fs); const double a = std::pow (10.0, -12 / 20.0);
            mark ("ccif 19000 20000 -12", 2.0);
            for (int i = 0; i < n; ++i) { const double fade = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.01 * fs) }); const float v = (float) (a * fade * (std::sin (twoPi * 19000 * i / fs) + std::sin (twoPi * 20000 * i / fs))); L.push_back (v); R.push_back (v); }
            pad (0.3);
        }
        {   // SMPTE 60 Hz + 7 kHz, 4:1, peak -6 dBFS
            const int n = (int) (2 * fs); const double a = std::pow (10.0, -6 / 20.0);
            mark ("smpte 60 7000 4:1 -6peak", 2.0);
            for (int i = 0; i < n; ++i) { const double fade = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.01 * fs) }); const float v = (float) (a * fade * (0.8 * std::sin (twoPi * 60 * i / fs) + 0.2 * std::sin (twoPi * 7000 * i / fs))); L.push_back (v); R.push_back (v); }
            pad (0.3);
        }
        {   // exponential sweep 20 Hz - 23.9 kHz, 5 s, -12 dBFS
            const double T = 5.0, f1 = 20, f2 = 23900, k = std::log (f2 / f1); const int n = (int) (T * fs);
            mark ("sweep 20 23900 -12", T);
            for (int i = 0; i < n; ++i) { const double t = i / fs; const double fade = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.002 * fs) }); const float v = (float) (0.25 * fade * std::sin (twoPi * f1 * T / k * (std::exp (t / T * k) - 1))); L.push_back (v); R.push_back (v); }
            pad (2.0);
        }
        for (double f : { 18000.0, 20000.0, 21000.0, 22000.0, 23000.0, 23500.0 }) { mark ("hf " + String (f, 0) + " -12", 0.5); tone (f, -12, 0.5); pad (0.1); }
        for (double f : { 1000.0, 10000.0 })
        {
            mark ("xtalkL " + String (f, 0) + " -6", 1.0); tone (f, -6, 1.0, true, false); pad (0.2);
            mark ("xtalkR " + String (f, 0) + " -6", 1.0); tone (f, -6, 1.0, false, true); pad (0.2);
        }
        mark ("noiseIndep -20rms", 3.0); noise (-20, 3.0, true); pad (0.3);
        mark ("noiseMono -20rms", 3.0); noise (-20, 3.0, false); pad (1.0);
    }
    else if (kind == "tone2k")  { pad (0.5); mark ("tone 2000 -12", 12.0); tone (2000, -12, 12.0, true, true, 0.02); pad (1.5); }
    else if (kind == "tsteps")
    {
        // steady sines in 1/12-octave steps, 100 Hz - 8 kHz: the reverb's steady-state response (ringing modes)
        pad (0.3);
        for (int k = 0; k <= 76; ++k)
        {
            const double f = 100.0 * std::pow (2.0, k / 12.0);
            mark ("step " + String (f, 1) + " -20", 0.4); tone (f, -20, 0.4, true, true, 0.01);
        }
        pad (1.5);
    }
    else if (kind == "stereo" || kind == "stereonote" || kind == "stereolo" || kind == "stereohi")
    {
        // one side at a time, then both: the routing matrix (direct and effect, left and right).
        // stereolo / stereohi: the same at -30 / -15 dB rms, for level-dependent effects (run 7)
        const double nd = kind == "stereolo" ? -30.0 : (kind == "stereohi" ? -15.0 : -20.0);
        const String nl = String ((int) nd) + "rms";
        if (kind == "stereonote") ev (0, MidiMessage::noteOn (ch, 48, (uint8) 100), "note on 48");
        pad (0.3);
        mark ("noiseL " + nl, 2.0); { const int a0 = at(); noise (nd, 2.0, false); for (int i = a0; i < at(); ++i) R[(size_t) i] = 0.0f; } pad (1.5);
        mark ("noiseR " + nl, 2.0); { const int a0 = at(); noise (nd, 2.0, false); for (int i = a0; i < at(); ++i) L[(size_t) i] = 0.0f; } pad (1.5);
        mark ("noiseBoth " + nl, 2.0); noise (nd, 2.0, true); pad (1.5);
        mark ("clickL", 0.001); L.push_back (0.5f); R.push_back (0.0f); pad (1.0);
        mark ("clickR", 0.001); L.push_back (0.0f); R.push_back (0.5f); pad (1.5);
        if (kind == "stereonote") ev (at() - 1, MidiMessage::noteOff (ch, 48), "note off 48");
    }
    else if (kind == "file" || kind == "filelo" || kind == "file2lo" || kind == "file3lo")
    {
        // listening material: ab-source.wav from the lab folder if present (first 15 s, 48 kHz), otherwise a
        // synthetic phrase (drum-like hits and a plucked chord). Run 9: "...lo" plays it 10 dB lower (the run-6
        // file captures clipped the interface on two programs); file2lo / file3lo use ab-source2.wav / ab-source3.wav
        // (other material: drums, vocal, guitar), or the synthetic phrase with another seed.
        pad (0.3);
        bool loaded = false;
        const bool lo = kind.endsWith ("lo");
        const int clip = kind.startsWith ("file2") ? 2 : (kind.startsWith ("file3") ? 3 : 1);
        const float fileGain = lo ? 0.158f : 0.5f;
        const String srcName = clip == 1 ? String ("ab-source.wav") : "ab-source" + String (clip) + ".wav";
        const File f = File::getSpecialLocation (File::userHomeDirectory).getChildFile ("Downloads/RSP-550/lab/" + srcName);
        if (f.existsAsFile())
        {
            AudioFormatManager fm; fm.registerBasicFormats();
            if (std::unique_ptr<AudioFormatReader> r { fm.createReaderFor (f) })
            {
                const int len = (int) std::min<int64> (r->lengthInSamples, (int64) (15 * fs));
                AudioBuffer<float> b (2, len); r->read (&b, 0, len, 0, true, true);
                mark ("file " + srcName + (lo ? " -10dB" : ""), len / fs);
                for (int i = 0; i < len; ++i) { L.push_back (fileGain * b.getSample (0, i)); R.push_back (fileGain * b.getSample (r->numChannels > 1 ? 1 : 0, i)); }
                loaded = true;
            }
        }
        if (! loaded)
        {
            const int len = (int) (10 * fs); const int a0 = at(); L.resize ((size_t) (a0 + len), 0.0f); R.resize (L.size(), 0.0f);
            mark ("file synthetic " + String (clip) + (lo ? " -10dB" : ""), 10.0);
            Random rr (98 + clip);
            for (int beat = 0; beat < (clip == 3 ? 0 : 20); ++beat)   // clip 3: chords only
            {
                const int t0 = a0 + (int) (beat * 0.5 * fs);
                for (int i = 0; i < (int) (0.3 * fs) && t0 + i < a0 + len; ++i)   // kick or snare
                {
                    const double t = i / fs;
                    const float v = (beat % 2 == 0) ? (float) (0.5 * std::exp (-t * 18) * std::sin (twoPi * (50 + 90 * std::exp (-t * 30)) * t))
                                                    : (float) (0.25 * std::exp (-t * 25) * (2 * rr.nextDouble() - 1));
                    L[(size_t) (t0 + i)] += v; R[(size_t) (t0 + i)] += v;
                }
                for (int i = 0; i < (int) (0.05 * fs) && t0 + (int) (0.25 * fs) + i < a0 + len; ++i)   // hat
                {
                    const float v = (float) (0.08 * std::exp (-i / fs * 120) * (2 * rr.nextDouble() - 1));
                    L[(size_t) (t0 + (int) (0.25 * fs) + i)] += v; R[(size_t) (t0 + (int) (0.25 * fs) + i)] += 0.8f * v;
                }
            }
            for (double f0 : { 196.0, 246.9, 293.7, 392.0 })   // plucked G chord every 2 s (Karplus-Strong)
                for (int bar = 0; bar < (clip == 2 ? 0 : 5); ++bar)   // clip 2: drums only
                {
                    const int t0 = a0 + (int) (bar * 2.0 * fs + 0.02 * fs * (f0 / 196.0)); const int P = (int) (fs / f0);
                    std::vector<float> d ((size_t) P); for (auto& x : d) x = (float) (2 * rr.nextDouble() - 1) * 0.12f;
                    for (int i = 0; i < (int) (1.8 * fs) && t0 + i < a0 + len; ++i)
                    {
                        const int k = i % P, k1 = (i + 1) % P; const float y = d[(size_t) k];
                        d[(size_t) k] = 0.996f * 0.5f * (d[(size_t) k] + d[(size_t) k1]);
                        L[(size_t) (t0 + i)] += 0.8f * y; R[(size_t) (t0 + i)] += y;
                    }
                }
            if (lo) for (int i = a0; i < a0 + len; ++i) { L[(size_t) i] *= 0.316f; R[(size_t) i] *= 0.316f; }
        }
        pad (3.0);
    }
    else if (kind == "tone")    { pad (0.5); mark ("tone 500 -12", 10.0); tone (500, -12, 10.0, true, true, 0.02); pad (1.5); }
    else if (kind == "clicktrain")
    {
        // run 7: a click every 40 ms for 12 s on both inputs; each click's response shows the delay at that moment,
        // so slow modulation (flanger LFO shape, rate, left/right phase) can be followed where tone tracking fails
        pad (0.5); mark ("clicks 40ms x300", 12.0);
        for (int c = 0; c < 300; ++c) { L.push_back (0.5f); R.push_back (0.5f); pad (0.04 - 1.0 / fs); }
        pad (1.5);
    }
    else if (kind == "tone440" || kind == "note440")
    {
        // note440 (run 7): the same with MIDI note 48 held throughout, for note-driven pitch shifters and the vocoder
        if (kind == "note440") ev (0, MidiMessage::noteOn (ch, 48, (uint8) 100), "note on 48");
        pad (0.5); mark ("tone 440 -12", 4.0); tone (440, -12, 4.0, true, true, 0.02); pad (0.5);
        mark ("clicks 250ms x8", 2.0);
        for (int c = 0; c < 8; ++c) { L.push_back (0.5f); R.push_back (0.5f); pad (0.25 - 1.0 / fs); }
        pad (0.5);
        {
            const double T = 2.0, f1 = 100, f2 = 4000, k = std::log (f2 / f1); const int n = (int) (T * fs);
            mark ("chirp 100 4000 -12", T);
            for (int i = 0; i < n; ++i) { const double t = i / fs; const double fade = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.01 * fs) }); const float v = (float) (0.25 * fade * std::sin (twoPi * f1 * T / k * (std::exp (t / T * k) - 1))); L.push_back (v); R.push_back (v); }
        }
        pad (1.5);
        if (kind == "note440") ev (at() - 1, MidiMessage::noteOff (ch, 48), "note off 48");
    }
    else if (kind == "rotsw")
    {
        ev (0, MidiMessage::controllerEvent (ch, 1, 0), "CC1 0");
        pad (0.5); const int t0 = at(); mark ("tone 1000 -12", 16.0); tone (1000, -12, 16.0, true, true, 0.02);
        ev (t0 + (int) (4 * fs), MidiMessage::controllerEvent (ch, 1, 127), "CC1 127");
        ev (t0 + (int) (10 * fs), MidiMessage::controllerEvent (ch, 1, 0), "CC1 0");
        pad (1.0);
    }
    else if (kind == "fb")     { pad (0.25); mark ("burst 1000 -20", 0.05); tone (1000, -20, 0.05, true, true, 0.002); pad (12.0); }
    else if (kind == "gate")
    {
        pad (0.5);
        for (int k = 0; k < 3; ++k) { mark ("burst 1000 -20", 0.4); tone (1000, -20, 0.4, true, true, 0.001); pad (1.6); }
        for (int k = 0; k < 2; ++k) { mark ("short 1000 -20", 0.02); tone (1000, -20, 0.02, true, true, 0.001); pad (1.5); }
    }
    else if (kind == "gsweep")
    {
        for (double db = -60; db <= -9.99; db += 2) { mark ("burst 1000 " + String (db, 0), 0.4); tone (1000, db, 0.4, true, true, 0.003); pad (1.2); }
    }
    else if (kind == "cc" || kind == "pb" || kind == "vel")
    {
        pad (0.3);
        auto burst = [&] (const String& label) { mark ("noise -20 " + label, 0.5); noise (-20, 0.5, false); pad (0.9); };
        const int steps[] = { 0, 16, 32, 48, 64, 80, 96, 112, 127 };
        if (kind == "cc")
        {
            ev (0, MidiMessage::channelPressureChange (ch, 127), "AT 127");
            for (int v : steps) { ev (at() - (int) (0.1 * fs), MidiMessage::controllerEvent (ch, 1, v), "CC1 " + String (v)); burst ("CC1=" + String (v)); }
            ev (at() - (int) (0.1 * fs), MidiMessage::controllerEvent (ch, 1, 127), "CC1 127");
            for (int v : steps) { ev (at() - (int) (0.1 * fs), MidiMessage::channelPressureChange (ch, v), "AT " + String (v)); burst ("AT=" + String (v)); }
        }
        else if (kind == "pb")
        {
            for (int v : steps) { const int pb = std::min (16383, v * 129); ev (at() - (int) (0.1 * fs), MidiMessage::pitchWheel (ch, pb), "PB " + String (pb)); burst ("PB=" + String (pb)); }
            ev (at(), MidiMessage::pitchWheel (ch, 8192), "PB centre");
        }
        else
        {
            for (int v : steps)
            {
                const int vel = std::max (1, v);
                ev (at() - (int) (0.1 * fs), MidiMessage::noteOn (ch, 60, (uint8) vel), "note on vel " + String (vel));
                burst ("VEL=" + String (vel));
                ev (at() - (int) (0.2 * fs), MidiMessage::noteOff (ch, 60), "note off");
            }
        }
        pad (1.5);
    }
    else if (kind == "enh")
    {
        pad (0.25);
        const double fr[] = { 97, 203, 511, 1013, 2027, 4001, 7919 };
        for (double db : { -40.0, -30.0, -20.0, -10.0 })
        {
            const int n = (int) (1.5 * fs); const double a = std::pow (10.0, db / 20) / 7.0;   // db = peak of the sum
            mark ("multitone " + String (db, 0), 1.5);
            for (int i = 0; i < n; ++i)
            {
                double v = 0; for (int k = 0; k < 7; ++k) v += std::sin (twoPi * fr[k] * i / fs + k * 1.3);
                const double fade = std::min ({ 1.0, i / (0.01 * fs), (n - 1 - i) / (0.01 * fs) });
                L.push_back ((float) (a * fade * v)); R.push_back ((float) (a * fade * v));
            }
            pad (0.3);
        }
        for (double db : { -40.0, -20.0, -6.0 }) { mark ("tone 1000 " + String (db, 0), 1.0); tone (1000, db, 1.0); pad (0.2); }
        mark ("noiseMono -20rms", 3.0); noise (-20, 3.0, false); pad (1.0);
    }
    else if (kind == "pcgap")
    {
        pad (0.5); const int t0 = at(); mark ("tone 1000 -12", 8.0); tone (1000, -12, 8.0, true, true, 0.02);
        ev (t0 + (int) (2 * fs), MidiMessage::programChange (ch, 3), "PC 4");
        ev (t0 + (int) (5 * fs), MidiMessage::programChange (ch, 0), "PC 1");
        pad (1.5);
    }
    else   // std and note
    {
        auto st = makeStimulus (fs); s.L = st.L; s.R = st.R; s.markers = st.markers;
        if (kind == "note") { s.events.push_back ({ 0, MidiMessage::noteOn (ch, 48, (uint8) 100), "note on 48" }); s.events.push_back ({ (int) s.L.size() - 1, MidiMessage::noteOff (ch, 48), "note off 48" }); }
    }
    return s;
}

static bool loadWavStim (const File& f, Stim4& s, double& rate)
{
    AudioFormatManager fm; fm.registerBasicFormats();
    std::unique_ptr<AudioFormatReader> r (fm.createReaderFor (f));
    if (r == nullptr || r->lengthInSamples <= 0) return false;
    rate = r->sampleRate; const int n = (int) r->lengthInSamples;
    AudioBuffer<float> b ((int) jmax (2u, r->numChannels), n);
    r->read (&b, 0, n, 0, true, true);
    s.L.assign (b.getReadPointer (0), b.getReadPointer (0) + n);
    const int rc = r->numChannels > 1 ? 1 : 0;
    s.R.assign (b.getReadPointer (rc), b.getReadPointer (rc) + n);
    const File m = f.withFileExtension ("txt");
    if (m.existsAsFile()) { s.markers.addLines (m.loadFileAsString()); s.markers.removeEmptyStrings(); }
    return true;
}

static int runRun4 (int argc, char** argv)
{
    if (argc < 13) { out ("usage: rsplab run4 <labdir> <backup.syx> <plan.txt> <restore.syx> <testsA.syx> <testsB.syx> <testsC.syx> o1 o2 i1 i2"); return 1; }
    const File lab { String (CharPointer_UTF8 (argv[2])) };
    auto bank = loadBank (File { String (CharPointer_UTF8 (argv[3])) });
    StringArray plan; plan.addLines (File { String (CharPointer_UTF8 (argv[4])) }.loadFileAsString()); plan.removeEmptyStrings();
    auto restore = loadBank (File { String (CharPointer_UTF8 (argv[5])) });
    std::map<String, std::vector<BankProgram>> tests { { "A", loadBank (File { String (CharPointer_UTF8 (argv[6])) }) },
                                                      { "B", loadBank (File { String (CharPointer_UTF8 (argv[7])) }) },
                                                      { "C", loadBank (File { String (CharPointer_UTF8 (argv[8])) }) } };
    const std::vector<int> sends { atoi (argv[9]) - 1, atoi (argv[10]) - 1 }, rets { atoi (argv[11]) - 1, atoi (argv[12]) - 1 };
    const String runName = argc > 13 ? String (CharPointer_UTF8 (argv[13])) : String ("run4");   // capture sub-folder
    const File capDir = lab.getChildFile ("capture").getChildFile (runName); capDir.createDirectory();
    const double fs = 48000.0;
    const File planDir = File { String (CharPointer_UTF8 (argv[4])) }.getParentDirectory();
    auto waitReturn = [] (const String& what) { out (">>> " + what + " Then press Return here."); std::string s; std::getline (std::cin, s); };
    out ("RSP-550 lab " + runName + ", " + Time::getCurrentTime().toString (true, true) + ": " + String (plan.size()) + " recordings (batches A, B, C, Z)");

    // safety: only the copy slots, and the restore file must cover every slot a batch writes
    std::set<int> restorable; for (auto& r : restore) restorable.insert (r.number);
    for (auto& [b, progs] : tests)
        for (auto& t : progs)
            if (t.number < 101 || t.number > 128 || ! restorable.count (t.number)) { out ("refusing: batch " + b + " writes slot " + String (t.number) + ", outside 101-128 or not in the restore file"); return 1; }

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
    auto matches = [&] (int n, const std::array<uint8, 96>& p) { auto cur = slotData (n); return cur.size() == 96 && std::equal (cur.begin(), cur.end(), p.begin()); };

    for (auto& r : restore) if (! matches (r.number, r.payload)) { out ("slot " + String (r.number) + " doesn't match the backup - stopping before writing anything"); return 3; }
    out ("slots 101-128 match the backup; they are written back at the end");
    const auto original = readArea (2, 0, 0, 0x60);

    AudioDeviceManager adm; String devName; AudioIODeviceType* devType = nullptr;
    for (auto* t : adm.getAvailableDeviceTypes())
    { t->scanForDevices(); for (auto& n : t->getDeviceNames (false)) if (n.containsIgnoreCase ("MHLink") && t->getDeviceNames (true).contains (n)) { devName = n; devType = t; } }
    if (devName.isEmpty()) { out ("audio: MHLink not found - nothing written"); return 3; }
    adm.setCurrentAudioDeviceType (devType->getTypeName(), true);
    AudioDeviceManager::AudioDeviceSetup setup;
    setup.outputDeviceName = setup.inputDeviceName = devName; setup.sampleRate = fs; setup.bufferSize = 512;
    setup.useDefaultInputChannels = setup.useDefaultOutputChannels = false;
    setup.inputChannels.setRange (0, 32, true); setup.outputChannels.setRange (0, 32, true);
    if (adm.setAudioDeviceSetup (setup, true).isNotEmpty() || adm.getCurrentAudioDevice() == nullptr) { out ("audio: could not open " + devName + " - nothing written"); return 3; }
    PlayRec pr; adm.addAudioCallback (&pr); Thread::sleep (500);
    out ("audio: " + devName + ", sends " + String (sends[0] + 1) + "/" + String (sends[1] + 1) + ", returns " + String (rets[0] + 1) + "/" + String (rets[1] + 1));

    auto selectPC = [&] (int number)
    {
        mo->sendMessageNow (MidiMessage::programChange (dev + 1, number % 128)); Thread::sleep (500);
        mo->sendMessageNow (MidiMessage::programChange (dev + 1, number - 1)); Thread::sleep (800);
    };
    auto resetControllers = [&]
    {
        mo->sendMessageNow (MidiMessage::controllerEvent (dev + 1, 1, 0));
        mo->sendMessageNow (MidiMessage::channelPressureChange (dev + 1, 0));
        mo->sendMessageNow (MidiMessage::pitchWheel (dev + 1, 8192));
        mo->sendMessageNow (MidiMessage::allNotesOff (dev + 1));
    };
    double curRate = fs;
    auto setRate = [&] (double want) -> bool
    {
        if (std::abs (curRate - want) < 1.0) return true;
        auto s = adm.getAudioDeviceSetup(); s.sampleRate = want;
        const auto err = adm.setAudioDeviceSetup (s, true);
        auto* d = adm.getCurrentAudioDevice();
        if (err.isNotEmpty() || d == nullptr || std::abs (d->getCurrentSampleRate() - want) > 1.0)
        {
            s.sampleRate = fs; adm.setAudioDeviceSetup (s, true); curRate = fs; Thread::sleep (1500);
            return std::abs (want - fs) < 1.0;
        }
        out ("  interface now at " + String (want, 0) + " Hz");
        curRate = want; Thread::sleep (1500);   // let the converters settle
        return true;
    };
    std::set<String> stimSaved;
    FileOutputStream index (capDir.getChildFile ("run4-index.tsv")); index.setPosition (0); index.truncate();
    index << "file\tbatch\tprogram\tkind\tdescription\tstored-name\n";

    std::function<bool (const String&, int, const String&, const String&, float)> record;
    record = [&] (const String& batch, int number, const String& kind, const String& desc, float stimDb) -> bool
    {
        const bool isWav = kind.startsWith ("wav:");
        const String kname = isWav ? kind.fromFirstOccurrenceOf ("wav:", false, false) : kind;   // used in file names
        Stim4 st; double rate = fs;
        if (isWav)
        {
            const File wf = planDir.getChildFile ("stim").getChildFile (kname + ".wav");
            if (! loadWavStim (wf, st, rate)) { out ("  stimulus " + wf.getFullPathName() + " missing or unreadable - line skipped"); return false; }
        }
        else st = makeStim4 (kind, fs, dev + 1);
        if (! setRate (rate)) { out ("  the interface would not run at " + String (rate, 0) + " Hz - " + kname + " on " + String (number) + " skipped"); return false; }
        if (stimDb != 0.0f) { const float g = Decibels::decibelsToGain (stimDb); for (auto& v : st.L) v *= g; for (auto& v : st.R) v *= g; }
        if (! stimSaved.count (kname))
        {
            writeWav (capDir.getChildFile ("stim-" + kname + ".wav"), { st.L, st.R }, rate);
            capDir.getChildFile ("stim-" + kname + ".txt").replaceWithText (st.markers.joinIntoString ("\n") + "\n");
            stimSaved.insert (kname);
        }
        resetControllers();
        selectPC (number);
        const auto buf = readArea (2, 0, 0, 0x60);
        for (auto& [bb, progs] : tests)
            if (bb == batch)
                for (auto& t : progs)
                    if (t.number == number && buf.size() == 96)
                    {
                        String diff;
                        for (int k = 0; k < 96; ++k) if (buf[(size_t) k] != t.payload[(size_t) k]) diff << String::toHexString (k) << ":" << (int) t.payload[(size_t) k] << "->" << (int) buf[(size_t) k] << " ";
                        if (diff.isNotEmpty()) out ("  note: the unit changed bytes of " + String (number) + " on load: " + diff);
                    }
        String name = "r4" + batch + "-" + String (number).paddedLeft ('0', 3) + "-" + kname + (stimDb != 0.0f ? "-m" + String ((int) -stimDb) : String());
        for (int k = 2; capDir.getChildFile (name + ".wav").existsAsFile(); ++k)   // repeats never overwrite (run 9)
            name = name.upToLastOccurrenceOf ("-rep", false, false) + "-rep" + String (k);
        pr.setup ((int) st.L.size(), sends, rets); pr.play[0] = st.L; pr.play[1] = st.R;
        StringArray sent;
        size_t next = 0;
        auto events = st.events; std::stable_sort (events.begin(), events.end(), [] (auto& a, auto& b) { return a.at < b.at; });
        while (next < events.size() && events[next].at <= 0) { mo->sendMessageNow (events[next].msg); sent.add (String (events[next].at) + "\t0\t" + events[next].label); ++next; }
        pr.pos.store (0);
        const double t0 = Time::getMillisecondCounterHiRes(); bool ok = true;
        while (pr.pos.load() < pr.len)
        {
            const int p = pr.pos.load();
            while (next < events.size() && p >= events[next].at) { mo->sendMessageNow (events[next].msg); sent.add (String (events[next].at) + "\t" + String (p) + "\t" + events[next].label); ++next; }
            Thread::sleep (1);
            if (Time::getMillisecondCounterHiRes() - t0 > (pr.len / rate + 5.0) * 1000.0) { ok = false; break; }
        }
        pr.pos.store (-1);
        while (next < events.size()) { mo->sendMessageNow (events[next].msg); sent.add (String (events[next].at) + "\tend\t" + events[next].label); ++next; }
        resetControllers();
        if (! ok) { out ("  audio stalled on " + name); return false; }
        writeWav (capDir.getChildFile (name + ".wav"), pr.rec, rate);
        if (! sent.isEmpty()) capDir.getChildFile (name + "-events.txt").replaceWithText ("intended\tactual\tevent\n" + sent.joinIntoString ("\n") + "\n");
        MemoryOutputStream m; for (auto b : buf) m.writeByte ((char) b);
        capDir.getChildFile (name + "-editbuffer.bin").replaceWithData (m.getData(), m.getDataSize());
        const String stored = buf.size() >= 16 ? asciiName (buf.data(), 16).trim() : String ("?");
        index << name << ".wav\t" << batch << "\t" << number << "\t" << kind << "\t" << desc << "\t" << stored << "\n"; index.flush();
        float peak = 0; for (auto& c : pr.rec) for (float v : c) peak = std::max (peak, std::abs (v));
        out ("  " + name + "  \"" + stored + "\"  " + desc + ", peak " + String (20 * std::log10 (peak + 1e-9), 1) + " dBFS" + (peak > 0.99f ? "  CLIPPED" : ""));
        // run 9: a clipped capture is useless for level and tone; take it again right away with the stimulus 10 dB
        // lower (saved as ...-m10; the index notes the stimulus level). One retake only.
        if (peak > 0.99f && stimDb == 0.0f)
        {
            out ("  clipped at the interface: recording it again with the stimulus 10 dB lower");
            return record (batch, number, kind, desc + " (stimulus -10 dB)", -10.0f);
        }
        return true;
    };

    auto bulkWrite = [&] (const std::vector<BankProgram>& progs) { for (auto& p : progs) { mo->sendMessageNow (dt1 (dev, 3, p.number - 1, 0, p.payload.data(), 96)); Thread::sleep (200); } };
    const double t0 = Time::getMillisecondCounterHiRes();
    for (const String batch : { "A", "B", "C", "Z" })   // Z (run 9): program changes only, last - repeat references
    {
        const auto& progs = tests[batch];
        out ("== batch " + batch + ": " + String ((int) progs.size()) + " test programs");
        if (! progs.empty())
        {
            waitReturn ("Batch " + batch + ": on the RSP-550, start Bulk Load so it shows 'Waiting'.");
            bulkWrite (progs);
            waitReturn ("Leave Bulk Load on the RSP-550 (back to the normal play screen).");
            int ok = 0; for (auto& t : progs) { if (matches (t.number, t.payload)) ++ok; else out ("  slot " + String (t.number) + " did not take its test program"); }
            out ("  stored " + String (ok) + " of " + String ((int) progs.size()));
            // run 4: after leaving Bulk Load the unit kept playing its previous sound for ~11 s although the edit
            // buffer already showed the new program, which spoiled the first recording of each batch
            out ("  letting the unit settle (15 s)"); selectPC (1); Thread::sleep (15000);
        }
        for (auto& line : plan)
        {
            StringArray f; f.addTokens (line, "\t", ""); if (f.size() < 4 || f[0] != batch) continue;
            record (batch, f[1].getIntValue(), f[2], f[3], 0.0f);
        }
        out ("  elapsed " + String ((Time::getMillisecondCounterHiRes() - t0) / 60000.0, 1) + " min");
    }
    // Follow-up rounds (run 7 on): while the runner waits, Claude analyses the recordings so far and may place
    // round<N>-plan.txt (lines "R<N> <program> <kind> <description>") and, for new test programs, round<N>-tests.syx
    // next to the plan. Same safety as the batches: slots 101-128 only, every slot covered by the restore file.
    for (int round = 1; round <= 12; )
    {
        out (">>> Follow-up round " + String (round) + ": wait until Claude says it is ready, then press Return here."
             " If Claude says the run is finished, type done and press Return.");
        std::string line; std::getline (std::cin, line);
        if (String (line).trim().equalsIgnoreCase ("done")) break;
        const String tag = "R" + String (round);
        const File pf = planDir.getChildFile ("round" + String (round) + "-plan.txt"), tf = planDir.getChildFile ("round" + String (round) + "-tests.syx");
        if (! pf.existsAsFile()) { out ("  " + pf.getFileName() + " is not there yet - waiting again"); continue; }
        auto progs = tf.existsAsFile() ? loadBank (tf) : std::vector<BankProgram> {};
        bool safe = true;
        for (auto& t : progs) if (t.number < 101 || t.number > 128 || ! restorable.count (t.number)) { out ("refusing round " + String (round) + ": it writes slot " + String (t.number)); safe = false; }
        if (! safe) { ++round; continue; }
        tests[tag] = progs;
        if (! progs.empty())
        {
            waitReturn ("Round " + String (round) + ": on the RSP-550, start Bulk Load so it shows 'Waiting'.");
            bulkWrite (progs);
            waitReturn ("Leave Bulk Load on the RSP-550 (back to the normal play screen).");
            int ok = 0; for (auto& t : progs) { if (matches (t.number, t.payload)) ++ok; else out ("  slot " + String (t.number) + " did not take its test program"); }
            out ("  stored " + String (ok) + " of " + String ((int) progs.size()));
            out ("  letting the unit settle (15 s)"); selectPC (1); Thread::sleep (15000);
        }
        StringArray pl; pl.addLines (pf.loadFileAsString()); pl.removeEmptyStrings();
        int n = 0;
        for (auto& l : pl) { StringArray f; f.addTokens (l, "\t", ""); if (f.size() >= 4 && f[0] == tag) { record (tag, f[1].getIntValue(), f[2], f[3], 0.0f); ++n; } }
        out ("  round " + String (round) + ": " + String (n) + " recordings, elapsed " + String ((Time::getMillisecondCounterHiRes() - t0) / 60000.0, 1) + " min");
        ++round;
    }
    setRate (fs);
    adm.removeAudioCallback (&pr);

    waitReturn ("Restoring slots 101-128: on the RSP-550, start Bulk Load again so it shows 'Waiting'.");
    bulkWrite (restore);
    waitReturn ("Leave Bulk Load on the RSP-550 (back to the normal play screen).");
    int good = 0;
    for (auto& r : restore) { if (matches (r.number, r.payload)) ++good; else out ("  slot " + String (r.number) + " NOT restored - run this again or use RSP-550-restore-101-128.command"); }
    out ("restored: " + String (good) + " of " + String ((int) restore.size()) + (good == (int) restore.size() ? " - slots 101-128 match the backup again" : ""));
    for (auto& p : bank) if (original.size() == 96 && p.number <= 128 && std::equal (p.payload.begin(), p.payload.end(), original.data())) { selectPC (p.number); out ("unit set back to program " + String (p.number) + " " + p.name); break; }
    out ("== DONE in " + String ((Time::getMillisecondCounterHiRes() - t0) / 60000.0, 1) + " min");
    return 0;
}

// rsplab restore <restore.syx>: writes the slots in restore.syx back (Bulk Load) and verifies them. For use after an
// interrupted run.
static int runRestore (int argc, char** argv)
{
    if (argc < 3) { out ("usage: rsplab restore <restore.syx>"); return 1; }
    auto restore = loadBank (File { String (CharPointer_UTF8 (argv[2])) });
    if (restore.empty()) { out ("no programs in the restore file"); return 1; }
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
        if (dev >= 0) mo = std::move (m);
    }
    if (dev < 0) { out ("MIDI: no answer from the RSP-550 (it must be on the normal play screen)"); return 2; }
    out (">>> On the RSP-550, start Bulk Load so it shows 'Waiting'. Then press Return here."); { std::string s; std::getline (std::cin, s); }
    for (auto& p : restore) { mo->sendMessageNow (dt1 (dev, p.number <= 128 ? 3 : 4, p.number <= 128 ? p.number - 1 : p.number - 129, 0, p.payload.data(), 96)); Thread::sleep (200); }
    out (">>> Leave Bulk Load on the RSP-550 (back to the normal play screen). Then press Return here."); { std::string s; std::getline (std::cin, s); }
    int good = 0;
    for (auto& p : restore)
    {
        const size_t before = col.count(); mo->sendMessageNow (rq1 (dev, p.number <= 128 ? 3 : 4, p.number <= 128 ? p.number - 1 : p.number - 129, 0, 0x60));
        std::vector<uint8> data; const double t0 = Time::getMillisecondCounterHiRes();
        while (Time::getMillisecondCounterHiRes() - t0 < 1500 && data.size() < 96)
        {
            Thread::sleep (5); data.clear();
            for (auto& r : col.since (before)) if (isDT1 (r.bytes) && checksumOk (r.bytes) && r.bytes[5] == (p.number <= 128 ? 3 : 4) && r.bytes[6] == (p.number <= 128 ? p.number - 1 : p.number - 129)) data.insert (data.end(), r.bytes.begin() + 8, r.bytes.end() - 2);
        }
        if (data.size() >= 96 && std::equal (p.payload.begin(), p.payload.end(), data.begin())) ++good; else out ("  slot " + String (p.number) + " does not match");
    }
    out ("restored " + String (good) + " of " + String ((int) restore.size()));
    return good == (int) restore.size() ? 0 : 4;
}

// rsplab stims <dir>: writes every run-4 stimulus with its markers and events (for analysis and plug-in renders)
static int runStims (int argc, char** argv)
{
    if (argc < 3) { out ("usage: rsplab stims <dir>"); return 1; }
    const File dir { String (CharPointer_UTF8 (argv[2])) }; dir.createDirectory();
    for (auto kind : { "std", "conv", "tone", "tone440", "rotsw", "fb", "gate", "gsweep", "cc", "pb", "vel", "enh", "note", "pcgap", "tone2k", "tsteps", "stereo", "stereonote", "file", "stereolo", "stereohi", "clicktrain", "note440", "filelo", "file2lo", "file3lo" })
    {
        const auto st = makeStim4 (kind, 48000.0, 1);
        writeWav (dir.getChildFile (String ("stim-") + kind + ".wav"), { st.L, st.R }, 48000.0);
        StringArray ev; for (auto& e : st.events) ev.add (String (e.at) + "\t" + e.label);
        dir.getChildFile (String ("stim-") + kind + ".txt").replaceWithText (st.markers.joinIntoString ("\n") + "\n");
        if (! ev.isEmpty()) dir.getChildFile (String ("stim-") + kind + "-events.txt").replaceWithText (ev.joinIntoString ("\n") + "\n");
        out (String (kind) + ": " + String (st.L.size() / 48000.0, 1) + " s, " + String ((int) st.events.size()) + " events");
    }
    return 0;
}
