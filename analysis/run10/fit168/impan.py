# Impulse comparison, unit vs ours (run-10 cut renders): energy per octave band in time windows, for L-in and R-in,
# own side and cross side; plus the arrival of the first strong reflections. Energy relative to the dry impulse.
import numpy as np, soundfile as sf, sys
from scipy import signal
fs = 48000
B = [125, 250, 500, 1000, 2000, 4000, 8000]
W = [(0, 2), (2, 20), (20, 50), (50, 100), (100, 200), (200, 400), (400, 800), (800, 1600), (1600, 3200)]
def load(d, tag, k): return sf.read('%s/renders/%s_%s.wav' % (d, tag, k))[0]
def bands(y):
    out = []
    for b in B:
        sos = signal.butter(3, [b / 2 ** 0.5, min(b * 2 ** 0.5, 23000)], 'band', fs=fs, output='sos')
        out.append(signal.sosfiltfilt(sos, y))
    return np.array(out)
def wins(y):
    z = bands(y) ** 2
    return np.array([[10 * np.log10(z[i, int(a * fs / 1000):int(b * fs / 1000)].sum() + 1e-20) for (a, b) in W] for i in range(len(B))])
def table(d, tag):
    L, R = load(d, tag, 'impL'), load(d, tag, 'impR')
    return {'LL': wins(L[:, 0]), 'LR': wins(L[:, 1]), 'RR': wins(R[:, 1]), 'RL': wins(R[:, 0])}
def env_ms(y, ms=1.0):
    w = int(ms * fs / 1000); e = np.sum(y ** 2, 1); return 10 * np.log10(np.convolve(e, np.ones(w), 'valid')[::w] + 1e-20)
if __name__ == '__main__':
    tag = sys.argv[1]; H = table('r10/hw', tag); O = table('r10/o' + sys.argv[2], tag)
    print('windows ms: ' + ' '.join('%d-%d' % w for w in W))
    for p in ('LL', 'LR', 'RR', 'RL'):
        print('-- %s  unit dB | unit-ours' % p)
        for i, b in enumerate(B):
            print('%5d  ' % b + ' '.join('%6.1f' % v for v in H[p][i]) + '  | ' + ' '.join('%+5.1f' % v for v in H[p][i] - O[p][i]))
    for d in ('r10/hw', 'r10/o' + sys.argv[2]):
        e = env_ms(load(d, tag, 'impL'))[:160]
        pk = np.argsort(e[2:])[::-1][:8] + 2
        print(d, 'loudest 1 ms blocks after 2 ms (L in):', sorted(pk.tolist()))
