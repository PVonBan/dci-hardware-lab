// RSP-550 lab tool (DCI). Talks to a Roland RSP-550 over MIDI and audio.
//
//   rsplab probe <outdir> [reference.syx]
//       Read-only. Lists audio devices and MIDI ports, finds the MIDI port and device ID the RSP-550 answers
//       on (RQ1 requests for a program name), then backs up the system area, the temporary (edit) area and
//       all 160 internal programs to <outdir>/RSP550-backup-<date>.syx and compares them with reference.syx.
//       Nothing is written to the unit.
#include <juce_audio_devices/juce_audio_devices.h>
#include <juce_audio_formats/juce_audio_formats.h>
#include <cstdio>
#include <iostream>
#include <mutex>
#include <thread>
#include <map>

using namespace juce;

static void out (const String& s) { std::printf ("%s\n", s.toRawUTF8()); std::fflush (stdout); }

//==============================================================================
struct Collector : public MidiInputCallback
{
    struct Msg { int port; std::vector<uint8> bytes; double t; };
    std::mutex m;
    std::vector<Msg> sysex;
    std::map<int, int> otherCount;   // non-sysex messages per input port (clock, active sensing, ...)
    std::map<MidiInput*, int> portOf;

    void handleIncomingMidiMessage (MidiInput* src, const MidiMessage& msg) override
    {
        std::lock_guard<std::mutex> l (m);
        const int port = portOf.count (src) ? portOf[src] : -1;
        if (msg.isSysEx())
        {
            const auto* d = msg.getRawData();
            sysex.push_back ({ port, std::vector<uint8> (d, d + msg.getRawDataSize()), Time::getMillisecondCounterHiRes() });
        }
        else ++otherCount[port];
    }
    size_t count() { std::lock_guard<std::mutex> l (m); return sysex.size(); }
    std::vector<Msg> since (size_t from) { std::lock_guard<std::mutex> l (m); return { sysex.begin() + (long) std::min (from, sysex.size()), sysex.end() }; }
};

static uint8 rolandSum (const std::vector<uint8>& b) { int s = 0; for (auto v : b) s += v; return (uint8) ((128 - (s % 128)) % 128); }

// F0 41 dev 38 11 a a a s s s sum F7
static MidiMessage rq1 (int dev, int a0, int a1, int a2, int size)
{
    std::vector<uint8> body { (uint8) a0, (uint8) a1, (uint8) a2, (uint8) ((size >> 14) & 0x7F), (uint8) ((size >> 7) & 0x7F), (uint8) (size & 0x7F) };
    std::vector<uint8> m { 0x41, (uint8) dev, 0x38, 0x11 };
    m.insert (m.end(), body.begin(), body.end());
    m.push_back (rolandSum (body));
    return MidiMessage::createSysExMessage (m.data(), (int) m.size());
}

static bool isDT1 (const std::vector<uint8>& b) { return b.size() >= 10 && b[0] == 0xF0 && b[1] == 0x41 && b[3] == 0x38 && b[4] == 0x12; }
static bool checksumOk (const std::vector<uint8>& b)
{
    if (b.size() < 10) return false;
    std::vector<uint8> body (b.begin() + 5, b.end() - 2);
    return rolandSum (body) == b[b.size() - 2];
}
static String hex (const std::vector<uint8>& b, size_t maxBytes = 24)
{
    String s; for (size_t i = 0; i < b.size() && i < maxBytes; ++i) s << String::toHexString ((int) b[i]).paddedLeft ('0', 2) << " ";
    if (b.size() > maxBytes) s << "... (" << (int) b.size() << " bytes)";
    return s.trim();
}
static String asciiName (const uint8* p, int n)
{
    String s; for (int i = 0; i < n; ++i) s << ((p[i] >= 32 && p[i] < 127) ? (char) p[i] : ' ');
    return s.trimEnd();
}

//==============================================================================
static void listAudio()
{
    out ("== Audio devices");
    AudioDeviceManager adm;
    for (auto* type : adm.getAvailableDeviceTypes())
    {
        type->scanForDevices();
        out ("type: " + type->getTypeName());
        auto outs = type->getDeviceNames (false), ins = type->getDeviceNames (true);
        StringArray all = outs; all.addArray (ins); all.removeDuplicates (false);
        for (auto& name : all)
        {
            std::unique_ptr<AudioIODevice> dev (type->createDevice (outs.contains (name) ? name : String(), ins.contains (name) ? name : String()));
            if (dev == nullptr) { out ("  " + name + " (could not open)"); continue; }
            String rates; for (auto r : dev->getAvailableSampleRates()) rates << (int) r << " ";
            out ("  device: " + name);
            out ("    outputs (" + String (dev->getOutputChannelNames().size()) + "): " + dev->getOutputChannelNames().joinIntoString (" | "));
            out ("    inputs  (" + String (dev->getInputChannelNames().size()) + "): " + dev->getInputChannelNames().joinIntoString (" | "));
            out ("    rates: " + rates);
        }
    }
}

struct Ports
{
    Array<MidiDeviceInfo> inInfo, outInfo;
    std::vector<std::unique_ptr<MidiInput>> ins;
    std::vector<std::unique_ptr<MidiOutput>> outs;
};

static int runProbe (int argc, char** argv)
{
    if (argc < 3) { out ("usage: rsplab probe <outdir> [reference.syx]"); return 1; }
    const File outDir { String (CharPointer_UTF8 (argv[2])) };
    outDir.createDirectory();
    const File ref = argc > 3 ? File (String (CharPointer_UTF8 (argv[3]))) : File();

    out ("RSP-550 lab probe, " + Time::getCurrentTime().toString (true, true) + " (read-only: nothing is written to the unit)");
    listAudio();

    out ("== MIDI ports");
    Collector col;
    Ports P;
    P.inInfo = MidiInput::getAvailableDevices();
    P.outInfo = MidiOutput::getAvailableDevices();
    for (int i = 0; i < P.inInfo.size(); ++i)
    {
        out ("  in  " + String (i) + ": " + P.inInfo[i].name);
        auto mi = MidiInput::openDevice (P.inInfo[i].identifier, &col);
        if (mi) { col.portOf[mi.get()] = i; mi->start(); }
        P.ins.push_back (std::move (mi));
    }
    for (int i = 0; i < P.outInfo.size(); ++i) out ("  out " + String (i) + ": " + P.outInfo[i].name);
    Thread::sleep (1500);
    for (auto& [p, n] : col.otherCount) out ("  input " + String (p) + " is sending " + String (n) + " non-SysEx messages (clock / active sensing / notes)");

    // Find the unit: ask every output, every device ID, for program 1's name
    out ("== Looking for the RSP-550 (RQ1, program 1 name, every port and device ID)");
    int foundOut = -1, foundIn = -1, foundDev = -1;
    for (int o = 0; o < P.outInfo.size() && foundOut < 0; ++o)
    {
        auto mo = MidiOutput::openDevice (P.outInfo[o].identifier);
        if (! mo) { out ("  out " + String (o) + ": could not open"); continue; }
        for (int dev = 0; dev < 16 && foundOut < 0; ++dev)
        {
            const size_t before = col.count();
            mo->sendMessageNow (rq1 (dev, 0x03, 0x00, 0x00, 16));
            for (int w = 0; w < 30 && col.count() == before; ++w) Thread::sleep (10);
            Thread::sleep (60);
            for (auto& m : col.since (before))
                if (isDT1 (m.bytes))
                {
                    foundOut = o; foundIn = m.port; foundDev = m.bytes[2];
                    out ("  ANSWER on in " + String (m.port) + " to out " + String (o) + " dev " + String (dev) + " (MIDI channel " + String (dev + 1) + "): "
                         + hex (m.bytes) + "  name \"" + (m.bytes.size() > 10 ? asciiName (m.bytes.data() + 8, (int) m.bytes.size() - 10) : String()) + "\""
                         + (checksumOk (m.bytes) ? "" : "  BAD CHECKSUM"));
                }
                else out ("  other SysEx on in " + String (m.port) + ": " + hex (m.bytes));
        }
        P.outs.push_back (std::move (mo));
    }
    if (foundOut < 0)
    {
        out ("RESULT: no answer from the RSP-550 on any port or device ID.");
        out ("Check: MIDI OUT of the computer -> MIDI IN of the RSP-550, and RSP-550 MIDI OUT -> computer MIDI IN; the unit powered on.");
        return 2;
    }
    out ("RESULT: RSP-550 found. Send on '" + P.outInfo[foundOut].name + "', receive on '" + P.inInfo[foundIn].name + "', device ID "
         + String (foundDev) + " (MIDI channel " + String (foundDev + 1) + ")");

    // Backup
    out ("== Backup (read-only)");
    auto mo = MidiOutput::openDevice (P.outInfo[foundOut].identifier);
    std::vector<std::vector<uint8>> all;
    auto request = [&] (int a0, int a1, int a2, int size, const String& what) -> std::vector<std::vector<uint8>>
    {
        for (int attempt = 0; attempt < 3; ++attempt)
        {
            const size_t before = col.count();
            mo->sendMessageNow (rq1 (foundDev, a0, a1, a2, size));
            const double t0 = Time::getMillisecondCounterHiRes();
            int got = 0; double last = t0;
            std::vector<std::vector<uint8>> r;
            while (Time::getMillisecondCounterHiRes() - last < 250 && Time::getMillisecondCounterHiRes() - t0 < 3000)
            {
                Thread::sleep (5);
                auto s = col.since (before);
                if ((int) s.size() > got) { got = (int) s.size(); last = Time::getMillisecondCounterHiRes(); }
            }
            for (auto& m : col.since (before)) if (isDT1 (m.bytes) && m.bytes[5] == a0 && (a0 == 0x00 || m.bytes[6] == a1)) r.push_back (m.bytes);   // ignore late replies to earlier requests
            int data = 0; bool ok = true;
            for (auto& b : r) { data += (int) b.size() - 10; ok = ok && checksumOk (b); }
            if (data >= size && ok) return r;
            out ("  " + what + ": got " + String (data) + " of " + String (size) + " bytes" + (ok ? "" : " (checksum error)") + ", retrying");
        }
        return {};
    };

    auto sys1 = request (0x00, 0x00, 0x00, 5, "system flags");
    auto sys2 = request (0x00, 0x01, 0x00, 256, "MIDI mapping");
    auto tmp  = request (0x02, 0x00, 0x00, 0x61, "temporary area");
    for (auto* v : { &sys1, &sys2, &tmp }) for (auto& b : *v) all.push_back (b);
    if (! tmp.empty() && tmp[0].size() > 30)
        out ("  temporary (current) program: \"" + asciiName (tmp[0].data() + 8, 16) + "\", algorithm " + String ((int) tmp[0][8 + 0x11]));
    if (! sys1.empty()) out ("  system flags: " + hex (sys1[0], 16));

    std::vector<std::array<uint8, 96>> progs;
    int missing = 0;
    for (int n = 1; n <= 160; ++n)
    {
        const int a0 = n <= 128 ? 0x03 : 0x04, a1 = n <= 128 ? n - 1 : n - 129;
        auto r = request (a0, a1, 0x00, 0x60, "program " + String (n));
        std::array<uint8, 96> pl {};
        if (r.empty()) { ++missing; out ("  program " + String (n) + ": NO DATA"); progs.push_back (pl); continue; }
        std::vector<uint8> data; for (auto& b : r) data.insert (data.end(), b.begin() + 8, b.end() - 2);
        std::copy_n (data.begin(), 96, pl.begin());
        progs.push_back (pl);
        for (auto& b : r) all.push_back (b);
        if (n % 20 == 0 || n == 1) out ("  program " + String (n).paddedLeft (' ', 3) + ": \"" + asciiName (pl.data(), 16) + "\" algorithm " + String ((int) pl[0x11]));
    }

    const File syx = outDir.getChildFile ("RSP550-backup-" + Time::getCurrentTime().formatted ("%Y%m%d-%H%M%S") + ".syx");
    { FileOutputStream os (syx); os.setPosition (0); os.truncate(); for (auto& b : all) os.write (b.data(), b.size()); }
    out ("  saved " + String ((int) all.size()) + " messages to " + syx.getFullPathName() + (missing ? ", " + String (missing) + " programs missing" : String()));

    // Compare with the reference dump
    if (ref.existsAsFile())
    {
        MemoryBlock mb; ref.loadFileAsData (mb);
        const auto* d = (const uint8*) mb.getData();
        std::map<int, std::array<uint8, 96>> refProg;
        for (size_t i = 0; i + 106 <= mb.getSize(); )
        {
            if (d[i] == 0xF0 && d[i + 1] == 0x41 && d[i + 3] == 0x38 && d[i + 4] == 0x12 && d[i + 105] == 0xF7)
            {
                const int n = d[i + 5] == 0x03 ? d[i + 6] + 1 : d[i + 5] == 0x04 ? d[i + 6] + 129 : -1;
                if (n > 0) std::copy_n (d + i + 8, 96, refProg[n].begin());
                i += 106;
            }
            else ++i;
        }
        int same = 0, diff = 0;
        for (int n = 1; n <= 160; ++n)
        {
            if (! refProg.count (n)) continue;
            const auto& a = progs[(size_t) n - 1]; const auto& b = refProg[n];
            int nd = 0; String where;
            for (int k = 0; k < 96; ++k) if (a[(size_t) k] != b[(size_t) k]) { ++nd; if (nd <= 6) where << String::toHexString (k) << ":" << (int) b[(size_t) k] << "->" << (int) a[(size_t) k] << " "; }
            if (nd == 0) ++same;
            else { ++diff; out ("  differs from reference: program " + String (n) + " \"" + asciiName (a.data(), 16) + "\" " + String (nd) + " bytes: " + where); }
        }
        out ("  reference " + ref.getFileName() + ": " + String (same) + " programs identical, " + String (diff) + " different");
    }
    out ("== DONE");
    return 0;
}

#include "Capture.h"
#include "Run4.h"

int main (int argc, char** argv)
{
    ScopedJuceInitialiser_GUI init;
    const String mode = argc > 1 ? String (argv[1]) : String();
    if (mode == "probe") return runProbe (argc, argv);
    if (mode == "capture" || mode == "capturepc") return runCapture (argc, argv);
    if (mode == "tone") return runTone (argc, argv);
    if (mode == "loadtest") return runLoadTest (argc, argv);
    if (mode == "blindwrite") return runBlindWrite (argc, argv);
    if (mode == "run2") return runRun2 (argc, argv);
    if (mode == "run3") return runRun3 (argc, argv);
    if (mode == "run4") return runRun4 (argc, argv);
    if (mode == "restore") return runRestore (argc, argv);
    if (mode == "stims") return runStims (argc, argv);
    out ("usage: rsplab probe <outdir> [reference.syx] | rsplab capture <labdir> <bank.syx> [first last]");
    return 1;
}
