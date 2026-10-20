# Listening test for a hardware build (the last step of every hardware-model build).
# Turns a folder of loudness-matched A/B pairs ("NN Name - A <unit>.wav" / "NN Name - B <plug> <build>.wav", plus an
# optional "00 levels.txt") into the blind ABX page: 24-bit WAVs with the unit's measured hiss added to the plug-in
# files, and index.html from template.html. Publish the output folder's index.html with the Artifact tool, with
# capabilities {db: {}, user: {}}, to the SAME artifact URL for that unit every build (results carry the build).
# usage: python3 make_abx.py <pairs dir> <out dir> --unit RSP-550 --plug SSP-550 --build 1.6.5 [--kind "01=Hall 1" ...]
import argparse, glob, json, os, re, html
import numpy as np, soundfile as sf
from scipy import signal

ap = argparse.ArgumentParser()
ap.add_argument('pairs'); ap.add_argument('out')
ap.add_argument('--unit', required=True); ap.add_argument('--plug', required=True); ap.add_argument('--build', required=True)
ap.add_argument('--kind', nargs='*', default=[], help='NN=algorithm or type shown under the program name')
ap.add_argument('--note', action='append', default=[], help='extra paragraph for the notes section')
a = ap.parse_args()
kinds = dict(k.split('=', 1) for k in a.kind)
os.makedirs(os.path.join(a.out, 'audio'), exist_ok=True)
rng = np.random.default_rng(550)
pairs = []
for fa in sorted(glob.glob(os.path.join(a.pairs, '* - A *.wav'))):
    m = re.match(r'(\d\d) (.+) - A ', os.path.basename(fa)); n, name = m.groups()
    fb = glob.glob(os.path.join(a.pairs, '%s * - B *.wav' % n))[0]
    x, sr = sf.read(fa); y, _ = sf.read(fb)
    seg = x[int(0.02 * sr):int(0.27 * sr)]               # the unit's idle hiss before the material starts
    for c in range(y.shape[1]):
        f, P = signal.welch(seg[:, c], sr, nperseg=4096)
        N = len(y); fq = np.fft.rfftfreq(N, 1 / sr)
        h = np.fft.irfft(np.fft.rfft(rng.standard_normal(N)) * np.sqrt(np.interp(fq, f, P)), N)
        y[:, c] += h * np.sqrt((seg[:, c] ** 2).mean()) / (np.sqrt((h ** 2).mean()) + 1e-20)
    sf.write(os.path.join(a.out, 'audio', '%s-a.wav' % n), x, sr, subtype='PCM_24')
    sf.write(os.path.join(a.out, 'audio', '%s-b.wav' % n), y, sr, subtype='PCM_24')
    pairs.append({'id': n, 'name': name, 'kind': kinds.get(n, '')})
lv = os.path.join(a.pairs, '00 levels.txt')
notes = ['    <p>The pairs are matched in loudness (ITU-R BS.1770), so level differences can\'t give X away.%s</p>' % (
    (' Before matching: ' + '; '.join(html.escape(l.strip()) for l in open(lv) if re.match(r'\d\d ', l)) + '.') if os.path.exists(lv) else '')]
notes.append('    <p>The plug-in files carry the %s\'s own measured hiss, so you judge the sound, not the noise floor.</p>' % html.escape(a.unit))
notes += ['    <p>%s</p>' % html.escape(t) for t in a.note]
notes.append('    <p>Plug-in: %s %s. Hardware: captured through the lab interface with latency and loop gain removed.</p>' % (html.escape(a.plug), html.escape(a.build)))
t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template.html')).read()
t = (t.replace('{{UNIT}}', html.escape(a.unit)).replace('{{PLUG}}', html.escape(a.plug)).replace('{{BUILD}}', a.build)
      .replace('{{PAIRS}}', json.dumps(pairs)).replace('{{NOTES}}', '\n'.join(notes)))
open(os.path.join(a.out, 'index.html'), 'w').write(t)
print('%d pairs -> %s (publish index.html with files audio/*.wav, capabilities {db:{}, user:{}}, same URL as last build)' % (len(pairs), a.out))
