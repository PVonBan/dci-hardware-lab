#include "Reverb.h"
#include <cstdio>
#include <cmath>
#include <vector>
using namespace ssp;
int main()
{
    const ReverbVoicing* V[] = { &voicings::hall1, &voicings::hall2, &voicings::hall3, &voicings::room1, &voicings::room2, &voicings::plate1, &voicings::plate2, &voicings::dense };
    const char* nm[] = { "hall1", "hall2", "hall3", "room1", "room2", "plate1", "plate2", "dense" };
    for (int v = 0; v < 8; ++v)
    {
        FdnReverb r; r.prepare (48000, *V[v]); r.set (2.0f, 0.0f, 1.0f, 0.0f, 1.0f, 1.0f, 20.0f, 20000.0f);
        const int N = 48000; std::vector<float> in (N, 0.0f), ol (N), orr (N); in[0] = 1.0f;
        for (int p = 0; p < N; p += 256) r.process (&in[p], &in[p], &ol[p], &orr[p], std::min (256, N - p));
        std::vector<double> e (N); double mx = 0;
        for (int i = 0; i < N; ++i) { double a = 0; for (int k = std::max (0, i - 48); k <= std::min (N - 1, i + 48); ++k) a += (std::fabs (ol[k]) + std::fabs (orr[k])) * (std::fabs (ol[k]) + std::fabs (orr[k])); e[i] = a; mx = std::max (mx, a); }
        int on = -1;
        for (int i = 0; i < N - 960 && on < 0; ++i)
        {
            if (10 * std::log10 (e[i] / mx + 1e-30) <= -30) continue;
            std::vector<double> w (e.begin() + i, e.begin() + i + 960); std::nth_element (w.begin(), w.begin() + 480, w.end());
            if (10 * std::log10 (w[480] / mx + 1e-30) > -35) on = i;
        }
        std::printf ("%s %.1f\n", nm[v], on / 48.0);
    }
}
