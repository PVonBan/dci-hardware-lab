# Rotary: unit vs ours on the music clips. Per 1/3-octave band: average power gain (out/in, mono sum, re 1 kHz), L/R
# coherence, side/mid, and the band level's fluctuation (std of 50 ms out/in level, dB).
import numpy as np, soundfile as sf, subprocess, os, sys
from scipy import signal
fs = 48000; C = '/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/'
CLIPS = [('run10b', 'filelo', 1133), ('run9', 'file2lo', 1179), ('run9', 'file3lo', 1179)]
cent = 1000 * 2 ** (np.arange(-12, 13, 2) / 3)
def bp(c): return signal.butter(3, [c / 2 ** (1 / 3), min(c * 2 ** (1 / 3), 23000)], 'band', fs=fs, output='sos')
def feats(x, y):
    xm = x.mean(1); ym = y.mean(1); g, coh, sm, fl = [], [], [], []
    m = (y[:, 0] + y[:, 1]) / 2; s = (y[:, 0] - y[:, 1]) / 2
    for c in cent:
        so = bp(c); a = signal.sosfilt(so, xm); b = signal.sosfilt(so, ym)
        g.append(10 * np.log10(np.mean(b ** 2) / np.mean(a ** 2)))
        l = signal.sosfilt(so, y[:, 0]); r = signal.sosfilt(so, y[:, 1])
        coh.append(np.mean(l * r) / np.sqrt(np.mean(l ** 2) * np.mean(r ** 2)))
        sm.append(10 * np.log10(np.mean(signal.sosfilt(so, s) ** 2) / np.mean(signal.sosfilt(so, m) ** 2)))
        w = int(0.05 * fs); ea = np.add.reduceat(a ** 2, np.arange(0, len(a), w)); eb = np.add.reduceat(b ** 2, np.arange(0, len(b), w))
        k = ea > ea.max() * 1e-3; fl.append(np.std(10 * np.log10(eb[k] / ea[k])))
    g = np.array(g); return g - g[6], np.array(coh), np.array(sm), np.array(fl)
def load(run, clip, lat, binp=None, prog=87, env=None):
    x, _ = sf.read(C + run + '/stim-%s.wav' % clip, always_2d=True); N = len(x)
    if binp is None:
        raw, _ = sf.read(C + run + '/r4B-%03d-%s.wav' % (prog, clip), always_2d=True); y = raw[lat:lat + N]
    else:
        f32 = 'rot_%s.f32' % clip
        if not os.path.exists(f32): x.astype('<f4').tofile(f32)
        subprocess.run([binp, '--render', 'rotr', f32, 'bankA.syx', str(prog)], check=True, stdout=subprocess.DEVNULL, env=dict(os.environ, **(env or {})))
        y = np.fromfile('rotr/%03d.f32' % prog, '<f4').reshape(-1, 2).astype(float)[:N]
    n = min(len(x), len(y)); return x[:n], y[:n]
if __name__ == '__main__':
    binp = sys.argv[1]; env = dict(a.split('=') for a in sys.argv[2:])
    acc = {'u': [], 'o': []}
    for run, clip, lat in CLIPS:
        acc['u'].append(feats(*load(run, clip, lat))); acc['o'].append(feats(*load(run, clip, lat, binp, env=env)))
    U = [np.mean([a[i] for a in acc['u']], 0) for i in range(4)]; O = [np.mean([a[i] for a in acc['o']], 0) for i in range(4)]
    print('band      ' + ' '.join('%6.0f' % c for c in cent))
    for i, nm in enumerate(('gain', 'coh', 'S/M', 'fluct')):
        print('%-5s U   ' % nm + ' '.join('%6.2f' % v for v in U[i])); print('%-5s O   ' % nm + ' '.join('%6.2f' % v for v in O[i]))
    err = np.mean(np.abs(U[0] - O[0])[1:]) + 2 * np.mean(np.abs(U[1] - O[1])) + 0.5 * np.mean(np.abs(U[3] - O[3]))
    print('COST %.3f  (gain %.2f dB, coh %.2f, fluct %.2f dB)' % (err, np.mean(np.abs(U[0] - O[0])[1:]), np.mean(np.abs(U[1] - O[1])), np.mean(np.abs(U[3] - O[3]))))
