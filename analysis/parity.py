# Render parity: the analysis renderer must sound like the real plug-in (level and 1/3-octave transfer, per channel).
# usage: parity.py <plugin_dir> <analysis_dir> <stim.f32> [progs...]
import numpy as np, sys, os, glob
PD, AD, ST = sys.argv[1:4]; progs = [int(a) for a in sys.argv[4:]] or sorted(int(os.path.basename(f)[:3]) for f in glob.glob(PD + '/*.f32'))
fs = 48000; SW0, SWN = 396002, 120000; SEG = SWN + 144000; NF = 1 << 19
stim = np.fromfile(ST, '<f4').reshape(-1, 2).astype(float); x = stim[SW0:SW0 + SEG, 0]
X = np.fft.rfft(x, NF); f = np.fft.rfftfreq(NF, 1 / fs); Xi = np.where((f > 20) & (f < 20000), 1 / np.where(np.abs(X) > 1e-9, X, 1), 0)
cent = 1000 * 2 ** (np.arange(-14, 13) / 3); fq = np.fft.rfftfreq(SEG, 1 / fs)
def bands(y):
    h = np.fft.irfft(np.fft.rfft(y, NF) * Xi, NF)[:SEG]; m = np.abs(np.fft.rfft(h)) ** 2
    return np.array([10 * np.log10(m[(fq >= c / 2 ** (1 / 6)) & (fq < c * 2 ** (1 / 6))].mean() + 1e-30) for c in cent])
bad = 0
for n in progs:
    a = np.fromfile('%s/%03d.f32' % (PD, n), '<f4').reshape(-1, 2).astype(float); b = np.fromfile('%s/%03d.f32' % (AD, n), '<f4').reshape(-1, 2).astype(float)
    m = min(len(a), len(b)); a, b = a[:m], b[:m]
    worst = 0; lv = []
    for c in (0, 1):
        ea = (a[SW0:SW0 + SEG, c] ** 2).sum(); eb = (b[SW0:SW0 + SEG, c] ** 2).sum(); lv.append(10 * np.log10(ea / eb))
        d = bands(a[SW0:SW0 + SEG, c]) - bands(b[SW0:SW0 + SEG, c]); worst = max(worst, np.abs(d - np.median(d)).max())
    ok = max(abs(v) for v in lv) < 0.3 and worst < 0.5
    early = 20 * np.log10(np.abs(a[:2 * fs] - b[:2 * fs]).max() / (np.abs(a[:2 * fs]).max() + 1e-12) + 1e-12)
    chaotic = not ok and early < -60   # identical at first, then a high-feedback loop diverges (splice / limiter decisions)
    bad += not ok and not chaotic
    print('%3d level plug-in - analysis %+.2f/%+.2f dB, worst band %.2f dB, first 2 s %.0f dB  %s' % (n, lv[0], lv[1], worst, early,
          'OK' if ok else ('OK (identical at first, diverges later: chaotic feedback)' if chaotic else '<<< MISMATCH')))
print('PARITY OK' if not bad else 'PARITY FAILED on %d programs' % bad)
sys.exit(1 if bad else 0)
