# Fast fit loop: render the wet-only reverbs' first stereo impulse with a test binary, compare with the unit's clean take.
import numpy as np, soundfile as sf, subprocess, sys, os
from scipy import signal
fs = 48000; S = os.path.dirname(os.path.abspath(__file__))
SLOT = {109: 'w001', 110: 'w008', 111: 'w002', 112: 'w004', 113: 'w005', 114: 'w007', 115: 'w009', 116: 'w033'}
B = [125, 250, 500, 1000, 2000, 4000, 8000]
def render(binp, out, env=None, slots=None):
    os.makedirs(out, exist_ok=True)
    subprocess.run([binp, '--render', out, S + '/imp.f32', S + '/bankA.syx'] + [str(s) for s in (slots or SLOT)], check=True,
                   stdout=subprocess.DEVNULL, env=dict(os.environ, **(env or {})))
def ours(out, slot):
    y = np.fromfile('%s/%03d.f32' % (out, slot), '<f4').reshape(-1, 2).astype(float); return y[48000:48000 + 336000]
def unit(tag): return sf.read(S + '/../r10/hw/renders/%s_imp_r1.wav' % tag)[0]
def env5(y, ms=5):
    w = int(ms * fs / 1000); e = np.add.reduceat(np.sum(y ** 2, 1), np.arange(0, len(y), w)); return 10 * np.log10(e + 1e-20)
def norm(e, ms=5): return e - 10 * np.log10(np.mean(10 ** (e[int(150 / ms):int(600 / ms)] / 10)))
def bandfeat(y):
    tone, slope = [], []
    for b in B:
        sos = signal.butter(3, [b / 2 ** 0.5, min(b * 2 ** 0.5, 23000)], 'band', fs=fs, output='sos')
        z = np.sum(signal.sosfiltfilt(sos, y, axis=0) ** 2, 1)
        tone.append(10 * np.log10(z[int(.15 * fs):int(.6 * fs)].sum()))
        blk = int(0.05 * fs); e = 10 * np.log10(np.add.reduceat(z, np.arange(0, len(z), blk)) + 1e-20)
        slope.append(np.polyfit(np.arange(4, 20) * 0.05, e[4:20], 1)[0])
    t = np.array(tone); return t - (t[2] + t[3]) / 2, np.array(slope)
def score(out, slot, show=False):
    tag = SLOT[slot]; u, o = unit(tag), ours(out, slot)
    eu, eo = norm(env5(u)), norm(env5(o))
    k = slice(0, 60)   # 0-300 ms
    env_err = np.mean(np.abs(np.maximum(eu[k], -15) - np.maximum(eo[k], -15)))
    tu, su = bandfeat(u); to, so = bandfeat(o)
    tone_err = np.mean(np.abs(tu - to)); dec_err = np.mean(np.abs(su - so) / np.abs(su))
    if show:
        print('%s env %.2f dB  tone %.2f dB  decay %.0f %%' % (tag, env_err, tone_err, 100 * dec_err))
        print('  tone u-o ' + ' '.join('%+5.1f' % v for v in tu - to) + '   decay u/o ' + ' '.join('%.0f/%.0f' % (a, b) for a, b in zip(su, so)))
        for i in range(0, 50, 1): print('   %3d  %6.1f %6.1f  %s' % (i * 5, eu[i], eo[i], ('#' * max(0, int((eu[i] + 20) / 2))).ljust(22) + '|' + '*' * max(0, int((eo[i] + 20) / 2))))
    return env_err, tone_err, dec_err
if __name__ == '__main__':
    binp, out = sys.argv[1], sys.argv[2]; show = sys.argv[3:] 
    if not os.path.exists(out + '/109.f32'): render(binp, out)
    tot = []
    for s in SLOT:
        r = score(out, s, SLOT[s] in show); tot.append(r)
        print('%s env %.2f tone %.2f decay %.0f%%' % (SLOT[s], *r[:2], 100 * r[2]))
    t = np.mean(tot, 0); print('MEAN env %.2f tone %.2f decay %.0f%%' % (t[0], t[1], 100 * t[2]))
