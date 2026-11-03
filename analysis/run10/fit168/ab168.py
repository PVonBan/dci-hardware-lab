# Listening pairs for SSP-550 1.6.7: the unit's run-10b music captures (inputs 7/8, clean) against the real plug-in
# (SSP550Test --render, the unit's bank in slot order), loudness-matched (BS.1770 gated).
import numpy as np, subprocess, sys, os, soundfile as sf
from scipy import signal
sys.path.insert(0, 'run9'); import lab10

def lufs(y):
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]; a1 = [1, -1.69065929318241, 0.73248077421585]
    b2 = [1, -2, 1]; a2 = [1, -1.99004745483398, 0.99007225036621]
    z = signal.lfilter(b2, a2, signal.lfilter(b1, a1, y, axis=0), axis=0)
    blk = int(0.4 * 48000); hop = int(0.1 * 48000)
    L = np.array([np.sum(np.mean(z[i:i + blk] ** 2, 0)) for i in range(0, len(z) - blk, hop)])
    ab = L[10 * np.log10(L + 1e-20) - 0.691 > -70]; rel = 10 * np.log10(ab.mean()) - 0.691 - 10
    g = ab[10 * np.log10(ab) - 0.691 > rel]; return -0.691 + 10 * np.log10(g.mean())
VER, BIN = sys.argv[1], sys.argv[2]
OUT = '/mnt/user-data/outputs/AB' + VER.replace('.', ''); os.makedirs(OUT, exist_ok=True)
U = '/mnt/user-data/uploads/Downloads/RSP-550/lab/capture/run10b/'
BK = '/mnt/user-data/uploads/Downloads/RSP-550/lab/RSP550-backup-20261018-041833.syx'
lab10.slotbank(BK, 'v168/bk.syx')
x, _ = sf.read(U + 'stim-filelo.wav', always_2d=True); N = len(x); x.astype('<f4').tofile('v168/filelo.f32')
LAT, G = 1133, np.array([10 ** (-4.1 / 20), 10 ** (-4.6 / 20)])   # inputs 7/8, corrected 2026-11-03 (see lab10.py)
names = {1: 'Large Hall 1', 8: 'Warm Plate', 50: 'Wide Chorus', 54: 'Light Flanger', 58: 'Shimmer', 87: 'Soft Rotary'}
os.makedirs('v168/abr', exist_ok=True)
subprocess.run([BIN, '--render', 'v168/abr', 'v168/filelo.f32', 'v168/bk.syx'] + [str(n) for n in names], check=True, capture_output=True)
notes = []
for i, (n, nm) in enumerate(names.items(), 1):
    raw, _ = sf.read(U + 'r4B-%03d-filelo.wav' % n, always_2d=True)
    hw = np.zeros((N, 2)); seg = raw[LAT:LAT + N] / G; hw[:len(seg)] = seg
    pl = np.fromfile('v168/abr/%03d.f32' % n, '<f4').reshape(-1, 2)[:N].astype(float)
    lh, lp = lufs(hw), lufs(pl); plm = pl * 10 ** ((lh - lp) / 20)
    # the unit's own hiss (its quietest quarter second) added to the plug-in file, as the 1.6.6 kit did: without it the
    # plug-in is dead silent in quiet passages and X can be told by the noise floor (found 2026-11-03 on the first 1.6.8 pairs)
    w = int(0.25 * 48000); e = np.array([np.mean(hw[i:i + w] ** 2) for i in range(0, N - w, w // 5)]); i0 = int(np.argmin(e)) * (w // 5); seg = hw[i0:i0 + w]
    rng = np.random.default_rng(550 + n)
    for c in range(2):
        f, P = signal.welch(seg[:, c], 48000, nperseg=4096); fq = np.fft.rfftfreq(N, 1 / 48000)
        h = np.fft.irfft(np.fft.rfft(rng.standard_normal(N)) * np.sqrt(np.interp(fq, f, P)), N)
        plm[:, c] += h * np.sqrt((seg[:, c] ** 2).mean()) / (np.sqrt((h ** 2).mean()) + 1e-20)
    pk = max(np.abs(hw).max(), np.abs(plm).max()); trim = min(1.0, 0.89 / pk)
    for tag, y in (('A RSP-550 hardware', hw * trim), ('B SSP-550 ' + VER, plm * trim)):
        sf.write('%s/%02d %s - %s.wav' % (OUT, i, nm, tag), np.clip(y, -1, 1), 48000, subtype='PCM_24')
    notes.append('%02d %-14s plug-in %+.1f dB against the hardware before matching%s' % (i, nm, lp - lh, '; both trimmed %.1f dB to avoid clipping' % (20 * np.log10(trim)) if trim < 1 else ''))
    print(notes[-1])
open(OUT + '/00 levels.txt', 'w').write('A/B pairs, loudness-matched (ITU-R BS.1770, gated) so only tone and character differ.\n'
    'Hardware: run 10b (Nov 3), music 10 dB below full level, interface inputs 7/8. Plug-in: SSP-550 ' + VER + ' rendered by its own processor.\n'
    'Raw level differences before matching:\n' + '\n'.join(notes) + '\n')
