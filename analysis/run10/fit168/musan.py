# Music-pair analysis: unit (run 10b filelo) vs a plug-in render. Splits each output into the part that is the dry input
# (least-squares, both input channels, short FIR around zero lag) and the rest (wet); compares per 1/3-octave band:
# total, dry and wet level, wet side/mid, wet L/R coherence, and the decay of the wet part after the music stops.
import numpy as np, soundfile as sf, sys, os
from scipy import signal
fs = 48000
U = '/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/run10b/'
LAT, G = 1133, np.array([10 ** (0.4 / 20), 10 ** (-0.1 / 20)])
x, _ = sf.read(U + 'stim-filelo.wav', always_2d=True); N = len(x)
cent = 1000 * 2 ** (np.arange(-15, 13) / 3)
def hwcap(n):
    raw, _ = sf.read(U + 'r4B-%03d-filelo.wav' % n, always_2d=True)
    y = np.zeros((N, 2)); s = raw[LAT:LAT + N] / G; y[:len(s)] = s; return y
def split(y, taps=48, pre=8):
    # dry part: y_c ~ sum_k a_k xL[t-k] + b_k xR[t-k], k = -pre..taps-pre
    out = np.zeros_like(y)
    X = []
    for ch in (0, 1):
        for k in range(-pre, taps - pre):
            X.append(np.roll(x[:, ch], k))
    X = np.array(X).T
    sl = slice(fs, N - fs)
    for c in (0, 1):
        w, *_ = np.linalg.lstsq(X[sl][::3], y[sl, c][::3], rcond=None)
        out[:, c] = X @ w
    return out, y - out
def bandlev(z):
    f, P = signal.welch(z, fs, nperseg=8192, axis=0)
    return np.array([10 * np.log10(P[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-30) for c in cent])
def bandsm(w):
    f, Pll = signal.welch(w[:, 0], fs, nperseg=8192); _, Prr = signal.welch(w[:, 1], fs, nperseg=8192)
    _, Plr = signal.csd(w[:, 0], w[:, 1], fs, nperseg=8192)
    m = (w[:, 0] + w[:, 1]) / 2; s = (w[:, 0] - w[:, 1]) / 2
    _, Pm = signal.welch(m, fs, nperseg=8192); _, Ps = signal.welch(s, fs, nperseg=8192)
    sm, coh = [], []
    for c in cent:
        k = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        sm.append(10 * np.log10(Ps[k].sum() / Pm[k].sum())); coh.append(np.abs(Plr[k].sum()) / np.sqrt(Pll[k].sum() * Prr[k].sum()))
    return np.array(sm), np.array(coh)
def analyse(y):
    d, w = split(y)
    tot = bandlev(y.sum(1) / 2); dr = bandlev(d.sum(1) / 2); we = bandlev(w.sum(1) / 2)
    sm, coh = bandsm(w)
    return dict(tot=tot, dry=dr, wet=we, sm=sm, coh=coh, w=w)
def lufsish(y): return 10 * np.log10(np.mean(y ** 2))
if __name__ == '__main__':
    n = int(sys.argv[1]); pl = np.fromfile(sys.argv[2], '<f4').reshape(-1, 2)[:N].astype(float)
    h = analyse(hwcap(n)); p = analyse(pl)
    off = np.median(h['tot'][8:22] - p['tot'][8:22])   # match the mid bands
    sel = list(range(0, len(cent), 2))
    print('band       ' + ' '.join('%6.0f' % cent[i] for i in sel))
    for k, nm in (('tot', 'total'), ('dry', 'dry'), ('wet', 'wet')):
        print('%-10s ' % (nm + ' U-P') + ' '.join('%+6.1f' % (h[k][i] - p[k][i] - off) for i in sel))
    print('wet-dry U  ' + ' '.join('%+6.1f' % (h['wet'][i] - h['dry'][i]) for i in sel))
    print('wet-dry P  ' + ' '.join('%+6.1f' % (p['wet'][i] - p['dry'][i]) for i in sel))
    print('S/M U      ' + ' '.join('%+6.1f' % h['sm'][i] for i in sel))
    print('S/M P      ' + ' '.join('%+6.1f' % p['sm'][i] for i in sel))
    print('coh U      ' + ' '.join('%6.2f' % h['coh'][i] for i in sel))
    print('coh P      ' + ' '.join('%6.2f' % p['coh'][i] for i in sel))
