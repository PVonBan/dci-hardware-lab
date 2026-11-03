# Which absolute gain for inputs 7/8? Compare the plug-in's level with the unit's on the captures shared by run 9 (inputs
# 5/6, right channel healthy, calibration from run 1) and run 10b (7/8). Right channel only.
import sys, os, numpy as np, soundfile as sf, subprocess
C = '/mnt/user-data/uploads/Downloads/RSP-550/lab/capture'; S = '/tmp/claude-0/-home-claude/43821833-de77-5012-b98f-e22767bd5dd6/scratchpad'
T = '/home/claude/ssp550/build/SSP550Test_artefacts/Release/SSP550Test'
lv = lambda y: 10 * np.log10(np.mean(y ** 2) + 1e-30)
caps = [(1, 'filelo'), (1, 'file2lo'), (8, 'filelo'), (8, 'file2lo'), (50, 'filelo'), (54, 'filelo'), (54, 'std'), (58, 'filelo'), (87, 'filelo'), (61, 'std')]
os.makedirs('anc', exist_ok=True)
print('prog stim      unit R raw dB: run9 run10b | plug R | hw-plug run9(R-4.6)  run10b(R-0.1)  run10b(R-4.6)')
for p, k in caps:
    x, _ = sf.read(f'{C}/run10b/stim-{k}.wav', always_2d=True, dtype='float32'); x.tofile('anc/x.f32')
    subprocess.run([T, '--render', 'anc', 'anc/x.f32', f'{S}/v168/bankA.syx', str(p)], check=True, stdout=subprocess.DEVNULL)
    pl = np.fromfile(f'anc/{p:03d}.f32', '<f4').reshape(-1, 2)[:len(x), 1]
    r9 = sf.read(f'{C}/run9/r4B-{p:03d}-{k}.wav')[0][1179:1179 + len(x), 1]; r10 = sf.read(f'{C}/run10b/r4B-{p:03d}-{k}.wav')[0][1133:1133 + len(x), 1]
    a, b, c = lv(r9), lv(r10), lv(pl)
    print('%3d %-8s   %6.2f %6.2f | %6.2f | %+6.2f %+6.2f %+6.2f' % (p, k, a, b, c, a + 4.6 - c, b + 0.1 - c, b + 4.6 - c))
