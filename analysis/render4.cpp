// render4 <bank.syx> <stim.f32 (interleaved stereo)> <outdir> [program]
// Render the SSP-550 engine on programs from an RSP-550 .syx (by memory address) with the capture stimulus.
// Chain as in the plug-in at 48 kHz with 16-bit converters: quantise in -> effect -> quantise out -> x total level.
#include "Programs.h"
#include "Dsp.h"
#include "Converter.h"
#include <cstdio>
#include <vector>
#include <fstream>
#include <map>
#include <cstdlib>
#include <xmmintrin.h>
using namespace ssp;
int main (int argc, char** argv)
{
    _mm_setcsr (_mm_getcsr() | 0x8040);
    std::ifstream sf (argv[1], std::ios::binary); std::vector<unsigned char> d ((std::istreambuf_iterator<char> (sf)), {});
    std::map<int, std::array<unsigned char, 96>> progs;
    for (size_t i = 0; i + 106 <= d.size(); )
        if (d[i] == 0xF0 && d[i + 1] == 0x41 && d[i + 3] == 0x38 && d[i + 4] == 0x12 && d[i + 105] == 0xF7 && (d[i + 5] == 3 || d[i + 5] == 4))
        { const int n = d[i + 5] == 3 ? d[i + 6] + 1 : d[i + 6] + 129; std::copy_n (&d[i + 8], 96, progs[n].begin()); i += 106; }
        else ++i;
    std::ifstream st (argv[2], std::ios::binary); std::vector<float> stim ((std::istreambuf_iterator<char> (st)), {});
    // read as floats
    std::ifstream st2 (argv[2], std::ios::binary | std::ios::ate); const size_t bytes = (size_t) st2.tellg(); st2.seekg (0);
    std::vector<float> s (bytes / 4); st2.read ((char*) s.data(), (std::streamsize) bytes);
    const int N = (int) s.size() / 2;
    std::vector<float> inL (N), inR (N);
    for (int i = 0; i < N; ++i) { inL[i] = s[2 * i]; inR[i] = s[2 * i + 1]; }
    const std::string outDir = argv[3];
    const float sr = 48000; const int B = 256; const float q = 32768.0f;
    NoteState ns; Context ctx; ctx.sr = sr; ctx.bpm = 120; ctx.midi = &ns;
    for (auto& [n, pl] : progs)
    {
        if (n > 160) continue;
        if (argc > 4 && n != std::atoi (argv[4])) continue;
        const int alg = pl[0x11];
        if (alg < 1 || alg > kNumAlgorithms) continue;
        std::string nm (pl.begin(), pl.begin() + 16);
        const Program prog = makeProgram (nm, alg, pl.data());   // as the plug-in's SysEx import: adds its own extras (0x60+)
        auto fx = makeEffect (alg); fx->prepare (sr, B);
        Params P { prog.payload.data(), &algo (alg) };
        const float tg = (float) pl[kTotalLevelOffset] * 0.01f;
        const float m = programMix (alg, prog.payload) * 0.01f, dg = mixDryGain (m), wg = mixWetGain (m);   // as the plug-in's Mix stage
        std::vector<float> qL (N), qR (N), oL (N), oR (N);
        for (int i = 0; i < N; ++i) { qL[i] = quantiseTo (inL[i], q); qR[i] = quantiseTo (inR[i], q); }
        for (int p = 0; p < N; p += B) { const int m = std::min (B, N - p); fx->process (&qL[p], &qR[p], &oL[p], &oR[p], m, P, ctx); }
        std::vector<float> o (2 * (size_t) N);
        for (int i = 0; i < N; ++i) { o[2 * i] = (inL[i] * dg + quantiseTo (oL[i], q) * wg) * tg; o[2 * i + 1] = (inR[i] * dg + quantiseTo (oR[i], q) * wg) * tg; }
        char fn[64]; std::snprintf (fn, sizeof fn, "/%03d.f32", n);
        std::ofstream of (outDir + fn, std::ios::binary); of.write ((char*) o.data(), (std::streamsize) o.size() * 4);
        std::printf ("%d alg %d total %.2f mix %.0f%%\n", n, alg, tg, m * 100);
    }
}
