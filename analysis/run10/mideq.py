# Run 10b round 2: program EQ on the Stereo Delay effect path, unit vs ours. Returns 7/8 calibration.
import numpy as np, soundfile as sf, subprocess, os, sys
fs = 48000; SW0, SWN = 396002, 120000; SEG = SWN + 144000; NF = 1 << 19
U = '/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/run10b/'
LAT = 1133; G = np.array([10 ** (0.4 / 20), 10 ** (-0.1 / 20)])
x, _ = sf.read(U + 'stim-std.wav'); xs = x[SW0:SW0 + SEG, 0]
X = np.fft.rfft(xs, NF); f = np.fft.rfftfreq(NF, 1 / fs); Xi = np.where((f > 20) & (f < 20000), 1 / np.where(np.abs(X) > 1e-9, X, 1), 0)
cent = 1000 * 2 ** (np.arange(-14, 13) / 3)
def bands(y):
    m = np.abs(np.fft.rfft(y, NF) * Xi) ** 2
    return np.array([10 * np.log10(m[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].mean() + 1e-30) for c in cent])
REND = sys.argv[1] if len(sys.argv) > 1 else 'v167/render4_l0'
OUT = 'run10r1/r2render_' + os.path.basename(REND); os.makedirs(OUT, exist_ok=True)
x.astype('<f4').tofile('run10r1/std.f32')
def resp(n, plug):
    if plug:
        p = '%s/%03d.f32' % (OUT, n)
        if not os.path.exists(p): subprocess.run([REND, 'run10r1/round2-tests.syx', 'run10r1/std.f32', OUT, str(n)], check=True, capture_output=True)
        y = np.fromfile(p, '<f4').reshape(-1, 2).astype(float)
    else:
        y = sf.read(U + ('r4C-%03d-std-rep2.wav' if n == 120 else 'r4C-%03d-std.wav') % n)[0][LAT:] / G
    return np.array([bands(y[SW0:SW0 + SEG, c]) for c in (0, 1)])
REF = {500: 101, 1000: 102, 2000: 103, 4000: 104}
tests = [(105, 2000, -12), (106, 2000, -6), (107, 2000, -3), (108, 2000, 3), (109, 2000, 6), (110, 2000, 12),
         (111, 500, -12), (112, 500, 12), (113, 1000, -12), (114, 1000, 12), (115, 4000, -12), (116, 4000, 12)]
sel = list(range(0, len(cent), 2))
if __name__ == '__main__':
    print('band        ' + ' '.join('%6.0f' % cent[i] for i in sel))
    hr = {k: resp(v, False) for k, v in REF.items()}; pr = {k: resp(v, True) for k, v in REF.items()}
    print('flat refs differ by Mid Frq (unit, mean over bands):', {k: round(float(np.mean(hr[k] - hr[500])), 2) for k in REF})
    res = {}
    for n, fc, g in tests:
        h = (resp(n, False) - hr[fc]).mean(0); p = (resp(n, True) - pr[fc]).mean(0); res[(fc, g)] = h
        print('%-11s' % ('%+d@%d U' % (g, fc)) + ' '.join('%+6.1f' % h[i] for i in sel))
        print('%-11s' % '   ours' + ' '.join('%+6.1f' % p[i] for i in sel))
    for n, nm in ((117, 'Hi-6'), (118, 'Hi+6'), (119, 'Lo-6'), (120, 'Lo+6')):
        h = (resp(n, False) - hr[2000]).mean(0); p = (resp(n, True) - pr[2000]).mean(0)
        print('%-11s' % (nm + ' U') + ' '.join('%+6.1f' % h[i] for i in sel)); print('%-11s' % '   ours' + ' '.join('%+6.1f' % p[i] for i in sel))
    np.save('run10r1/mid_unit.npy', {'%d,%d' % k: v for k, v in res.items()}, allow_pickle=True)
