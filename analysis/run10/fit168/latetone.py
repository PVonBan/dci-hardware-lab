# Per program: late-field tone (150-600 ms, both inputs, both outputs) unit-ours normalised at 500 Hz-1 kHz; band decay
# slope (dB/s over 200-1000 ms, Schroeder-free: band energy in 50 ms blocks, least squares) unit / ours.
import numpy as np, soundfile as sf, sys
from scipy import signal
fs = 48000; B = [125, 250, 500, 1000, 2000, 4000, 8000]
def ld(d, tag, k): return sf.read('%s/renders/%s_%s.wav' % (d, tag, k))[0]
def feats(d, tag):
    y = np.hstack([ld(d, tag, 'impL'), ld(d, tag, 'impR')])
    tone, slope = [], []
    for b in B:
        sos = signal.butter(3, [b / 2 ** 0.5, min(b * 2 ** 0.5, 23000)], 'band', fs=fs, output='sos')
        z = np.sum(signal.sosfiltfilt(sos, y, axis=0) ** 2, 1)
        tone.append(10 * np.log10(z[int(.15 * fs):int(.6 * fs)].sum()))
        blk = int(0.05 * fs); e = 10 * np.log10(np.add.reduceat(z, np.arange(0, len(z), blk)) + 1e-20)
        i0, i1 = 4, 20; slope.append(np.polyfit(np.arange(i0, i1) * 0.05, e[i0:i1], 1)[0])
    return np.array(tone), np.array(slope)
ver = sys.argv[1]
print('tag    late tone unit-ours (norm 500/1k): ' + ' '.join('%6d' % b for b in B) + '   | decay dB/s unit/ours')
for t in sys.argv[2:]:
    th, sh = feats('r10/hw', t); to, so = feats('r10/o' + ver, t)
    d = th - to; d -= (d[2] + d[3]) / 2
    print('%-6s ' % t + ' ' * 33 + ' '.join('%+6.1f' % v for v in d) + '   | ' + ' '.join('%3.0f/%3.0f' % (a, b) for a, b in zip(sh, so)))
