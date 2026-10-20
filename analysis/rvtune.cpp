// rvtune <voicing 0..7> <rt60> <size> <dampHz> <ratio> <cubic 0/1> -> prints band T30s (125 250 500 1k 2k 4k 8k)
#include "Reverb.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <vector>
#include <complex>
using namespace ssp;
static double t30 (const std::vector<double>& h)
{
    std::vector<double> e (h.size()); double acc = 0;
    for (size_t i = h.size(); i-- > 0;) { acc += h[i] * h[i]; e[i] = acc; }
    size_t i5 = 0, i25 = 0;
    for (size_t i = 0; i < e.size(); ++i) { double d = 10 * std::log10 (e[i] / e[0] + 1e-30); if (! i5 && d < -5) i5 = i; if (d < -25) { i25 = i; break; } }
    return i25 > i5 ? 3.0 * (double) (i25 - i5) / 48000.0 : -1;
}
int main (int argc, char** argv)
{
    const ReverbVoicing* V[] = { &voicings::hall1, &voicings::hall2, &voicings::hall3, &voicings::room1, &voicings::room2, &voicings::plate1, &voicings::plate2, &voicings::dense };
    const int vi = atoi (argv[1]); const float rt = atof (argv[2]), size = atof (argv[3]), dhz = atof (argv[4]), ratio = atof (argv[5]);
    FdnReverb r; r.prepare (48000, *V[vi]);
    r.setDamping (dhz, ratio); if (argc > 7) r.setBaseDamping (atof (argv[6]), atof (argv[7])); r.set (rt, 1.0f, size, 0.0f, 1.0f, 1.0f, 20.0f, 20000.0f);
    const int N = 48000 * 12; std::vector<float> in (N, 0.0f), ol (N), orr (N); in[100] = 1.0f;
    for (int p = 0; p < N; p += 256) r.process (&in[p], &in[p], &ol[p], &orr[p], std::min (256, N - p));
    // band-pass via FFT-free method: 4th-order Butterworth bandpass (two biquads) per octave, forward only
    const double cs[] = { 125, 250, 500, 1000, 2000, 4000, 8000 };
    for (double c : cs)
    {
        std::vector<double> x (N); for (int i = 0; i < N; ++i) x[i] = ol[i] + orr[i];
        for (int pass = 0; pass < 2; ++pass)
        {
            const double f0 = c, Q = 1.414, w = 2 * M_PI * f0 / 48000, al = std::sin (w) / (2 * Q);
            double b0 = al, b1 = 0, b2 = -al, a0 = 1 + al, a1 = -2 * std::cos (w), a2 = 1 - al;
            double x1 = 0, x2 = 0, y1 = 0, y2 = 0;
            for (int i = 0; i < N; ++i) { double y = (b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0; x2 = x1; x1 = x[i]; y2 = y1; y1 = y; x[i] = y; }
        }
        std::printf ("%.3f ", t30 (x));
    }
    std::printf ("\n");
}
