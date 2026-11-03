import numpy as np, soundfile as sf, sys
fs = 48000
def env(d, tag, k, ms=5):
    y = sf.read('%s/renders/%s_%s.wav' % (d, tag, k))[0]; w = int(ms * fs / 1000)
    e = np.add.reduceat(np.sum(y ** 2, 1), np.arange(0, len(y), w)); return 10 * np.log10(e + 1e-20)
tag, ver = sys.argv[1], sys.argv[2]; k = sys.argv[3] if len(sys.argv) > 3 else 'impL'
h, o = env('r10/hw', tag, k), env('r10/o' + ver, tag, k)
ref = lambda e: 10 * np.log10(np.mean(10 ** (e[60:120] / 10)))   # 300-600 ms
h -= ref(h); o -= ref(o)
for i in range(0, 64): print('%4d ms  unit %6.1f  ours %6.1f  %s' % (i * 5, h[i], o[i], '#' * max(0, int((h[i] + 30) / 2))))
print('late decay dB per 100 ms (300-1500 ms): unit %.2f ours %.2f' % tuple(np.polyfit(np.arange(60, 300) * 5, e[60:300], 1)[0] * 100 for e in (h, o)))
