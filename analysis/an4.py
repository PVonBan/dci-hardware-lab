#!/usr/bin/env python3
"""Run-4 analysis: one function per stimulus kind, the same code for hardware captures and plug-in renders.

usage: an4.py <recordings dir> <stims dir> <plan4.txt> <out.json> [--plug]
  recordings dir: r4<batch>-<prog>-<kind>.wav (hardware) or .f32 (plug-in render, interleaved stereo, 48 kHz)
  Hardware: loop latency and per-channel loop gain come from the converter run on the dry reference
  (r4A-101-conv), and every other recording is shifted and gain-corrected with them. --plug: latency 0, gain 1.
"""
import sys, os, json, numpy as np
from scipy.io import wavfile
from scipy import signal

FS = 48000

def load(path):
    if path.endswith('.f32'):
        return np.fromfile(path, '<f4').reshape(-1, 2).astype(np.float64)
    fs, x = wavfile.read(path)
    x = x.astype(np.float64) / (2**31 if x.dtype == np.int32 else 1)
    return x if x.ndim == 2 else np.stack([x, x], 1)

def markers(stims, kind):
    out = []
    for line in open(os.path.join(stims, 'stim-%s.txt' % kind)):
        p = line.split()
        if len(p) >= 3 and p[-1].lstrip('-').isdigit() and p[-2].lstrip('-').isdigit():
            out.append((' '.join(p[:-2]), int(p[-2]), int(p[-1])))
        elif len(p) >= 3 and p[1].isdigit() and p[2].isdigit():      # run 1-3 stimulus: "<name> <start> <length> ..."
            out.append((' '.join([p[0]] + p[3:]), int(p[1]), int(p[2])))
    return out

def db(x): return 20 * np.log10(np.abs(x) + 1e-12)
def rms(x): return np.sqrt(np.mean(np.square(x)) + 1e-30)
def rmsdb(x): return 20 * np.log10(rms(x))

def tone_amp(x, f, fs=FS):
    """amplitude of a sinusoid at f (Hann-windowed single-bin DFT, coherent gain corrected)"""
    n = len(x); w = np.hanning(n); t = np.arange(n) / fs
    return 2 * np.abs(np.sum(x * w * np.exp(-2j * np.pi * f * t))) / np.sum(w)

def octave3(f, P):
    cs = 1000 * 2 ** (np.arange(-17, 14) / 3); out = []
    for c in cs:
        m = (f >= c * 2 ** (-1 / 6)) & (f < c * 2 ** (1 / 6))
        out.append(10 * np.log10(np.mean(P[m]) + 1e-30) if m.any() else None)
    return [round(float(c), 1) for c in cs], [None if v is None else round(float(v), 2) for v in out]

# ---------------------------------------------------------------------------------------------------- calibration
class Cal:
    def __init__(self, lat=0, gain=(1.0, 1.0)): self.lat, self.gain = lat, np.array(gain)
    def apply(self, y, n):
        y = y[self.lat:self.lat + n] / self.gain
        if len(y) < n: y = np.vstack([y, np.zeros((n - len(y), 2))])
        return y

def calibrate(y, stim, mk):
    """latency from the cross-correlation of the converter stimulus with its return, gain from 1 kHz at -20 dBFS"""
    a = stim[:, 0][:FS * 20]; b = y[:, 0][:FS * 20]
    c = signal.fftconvolve(b, a[::-1], 'full'); lat = int(np.argmax(np.abs(c))) - (len(a) - 1)
    lat = max(lat, 0)
    g = []
    for ch in (0, 1):
        for nm, s0, n in mk:
            if nm == 'thd 1000 -20':
                g.append(tone_amp(y[lat + s0 + 2400: lat + s0 + n - 2400, ch], 1000) / tone_amp(stim[s0 + 2400: s0 + n - 2400, ch], 1000))
    return Cal(lat, g)

# ---------------------------------------------------------------------------------------------------- kinds
def an_conv(y, x, mk):
    r = {}
    seg = {nm: (s0, n) for nm, s0, n in mk}
    s0, n = seg['silence']; z = y[s0 + 4800:s0 + n - 4800]
    r['noise_dbfs'] = [round(rmsdb(z[:, c]), 1) for c in (0, 1)]
    # A-weighted noise
    f, P = signal.welch(z[:, 0], FS, nperseg=8192)
    f2 = f ** 2; ra = 12194 ** 2 * f2 ** 2 / ((f2 + 20.6 ** 2) * np.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))
    r['noise_dbfs_A'] = round(float(10 * np.log10(np.sum(P * (ra * 10 ** (2.0 / 20)) ** 2) * (f[1] - f[0]) + 1e-30)), 1)
    med = np.median(P[(f > 100) & (f < 20000)])
    idle = [(round(float(fi), 1), round(float(10 * np.log10(p / med)), 1)) for fi, p in zip(f, P) if 30 < fi < 22000 and p > 100 * med]
    r['idle_tones_db_over_floor'] = idle[:20]
    r['noise_spectrum_third_oct'] = octave3(f, P)
    lin = []
    for nm, s0, n in mk:
        if nm.startswith('low1k'):
            lvl = float(nm.split()[1]); a = tone_amp(y[s0 + 2400:s0 + n - 2400, 0], 1000)
            lin.append((lvl, round(float(db(a) - lvl), 2)))
    r['lowlevel_gain_db'] = lin
    thd = {}
    for nm, s0, n in mk:
        if nm.startswith('thd'):
            _, f0, lvl = nm.split(); f0 = float(f0); seg_ = y[s0 + 2400:s0 + n - 2400, 0]
            a1 = tone_amp(seg_, f0); hs = [tone_amp(seg_, f0 * h) for h in range(2, 8) if f0 * h < 23500]
            thd.setdefault(f0, []).append({'level': float(lvl), 'gain_db': round(float(db(a1) - float(lvl)), 2),
                                           'thd_db': round(float(10 * np.log10(sum(h * h for h in hs) / a1 ** 2 + 1e-20)), 1) if hs else None,
                                           'h_db': [round(float(db(h / a1)), 1) for h in hs]})
    r['thd'] = thd
    s0, n = seg['ccif 19000 20000 -12']; z = y[s0 + 4800:s0 + n - 4800, 0]
    a19 = tone_amp(z, 19000); r['ccif_db'] = {str(f): round(float(db(tone_amp(z, f) / a19)), 1) for f in (1000, 2000, 18000, 21000, 17000)}
    s0, n = seg['smpte 60 7000 4:1 -6peak']; z = y[s0 + 4800:s0 + n - 4800, 0]
    a7 = tone_amp(z, 7000); sb = [tone_amp(z, 7000 + k * 60) for k in (-2, -1, 1, 2)]
    r['smpte_imd_db'] = round(float(20 * np.log10(np.sqrt(sum(s * s for s in sb)) / a7 + 1e-12)), 1)
    s0, n = seg['sweep 20 23900 -12']
    X = np.fft.rfft(x[s0:s0 + n, 0], 1 << 20); Y = np.fft.rfft(y[s0:s0 + n + 24000, 0], 1 << 20)
    fr = np.fft.rfftfreq(1 << 20, 1 / FS); H = Y / (X + 1e-9 * np.max(np.abs(X)))
    pts = [20, 50, 100, 1000, 5000, 10000, 12000, 14000, 15000, 16000, 17000, 18000, 19000, 20000, 21000, 22000, 23000]
    ref = np.median(np.abs(H[(fr > 500) & (fr < 2000)]))
    r['sweep_db'] = {str(p): round(float(db(np.median(np.abs(H[(fr > p * 0.98) & (fr < p * 1.02)])) / ref)), 2) for p in pts}
    hf = {}
    for nm, s0, n in mk:
        if nm.startswith('hf'):
            f0 = float(nm.split()[1]); z = y[s0 + 2400:s0 + n - 2400, 0]
            F, P = signal.periodogram(z, FS, window='hann'); a = tone_amp(z, f0)
            mask = np.abs(F - f0) > 200; k = np.argmax(P * mask)
            hf[str(int(f0))] = {'gain_db': round(float(db(a) + 12), 1), 'largest_other_hz': round(float(F[k]), 0),
                                'largest_other_db': round(float(10 * np.log10(P[k] / (a * a / 2 / (F[1] - F[0]) * 0.375) + 1e-30) ), 1)}
    r['hf_tones'] = hf
    xt = {}
    for nm, s0, n in mk:
        if nm.startswith('xtalk'):
            side, f0 = nm.split()[0][-1], float(nm.split()[1]); z = y[s0 + 2400:s0 + n - 2400]
            on, off = (0, 1) if side == 'L' else (1, 0)
            xt['%s->%s %d' % (side, 'R' if side == 'L' else 'L', f0)] = round(float(db(tone_amp(z[:, off], f0) / tone_amp(z[:, on], f0))), 1)
    r['crosstalk_db'] = xt
    for key in ('noiseIndep -20rms', 'noiseMono -20rms'):
        s0, n = seg[key]; z = y[s0 + 2400:s0 + n - 2400]
        f, C = signal.coherence(z[:, 0], z[:, 1], FS, nperseg=4096)
        r['coherence_' + key.split()[0]] = octave3(f, C)[1][::3]
    return r

def ir_from_std(y, x, mk):
    seg = {nm.split()[0]: (s0, n) for nm, s0, n in mk}
    s0 = [s for nm, s, n in mk if nm.startswith('sweep')][0]; n = [n for nm, s, n in mk if nm.startswith('sweep')][0]
    L = 1 << 19
    X = np.fft.rfft(x[s0:s0 + n, 0], L)
    irs = []
    for c in (0, 1):
        Y = np.fft.rfft(y[s0:s0 + n + 144000, c], L)
        H = Y * np.conj(X) / (np.abs(X) ** 2 + 1e-6 * np.max(np.abs(X)) ** 2)
        irs.append(np.fft.irfft(H, L)[:FS * 4])
    return np.array(irs).T

def schroeder_t30(ir, band=None):
    if band:
        sos = signal.butter(4, band, 'bandpass', fs=FS, output='sos'); ir = signal.sosfiltfilt(sos, ir)
    e = np.cumsum(ir[::-1] ** 2)[::-1]; e = 10 * np.log10(e / e[0] + 1e-30)
    try:
        i5 = np.argmax(e < -5); i25 = np.argmax(e < -25)
        if i25 <= i5: return None
        return round(float(3 * (i25 - i5) / FS), 3)
    except Exception: return None

def an_std(y, x, mk):
    ir = ir_from_std(y, x, mk); r = {}
    m = ir[:, 0] + ir[:, 1]
    r['level_db'] = round(rmsdb(y[:, 0]) - rmsdb(x[:, 0]), 2)
    r['t30'] = {'broad': schroeder_t30(m), '500': schroeder_t30(m, (354, 707)), '1k': schroeder_t30(m, (707, 1414)),
                '2k': schroeder_t30(m, (1414, 2828)), '4k': schroeder_t30(m, (2828, 5657)), '8k': schroeder_t30(m, (5657, 11314)),
                '250': schroeder_t30(m, (177, 354)), '125': schroeder_t30(m, (88, 177))}
    env = np.abs(m); thr = np.max(env) * 10 ** (-30 / 20)
    r['first_arrival_ms'] = round(float(np.argmax(env > thr) / FS * 1000), 2)
    k = np.argmax(env > np.max(env) * 10 ** (-20 / 20))
    r['onset_-20dB_ms'] = round(float(k / FS * 1000), 2)
    # echo density: fraction of samples beyond 1 std in 20 ms windows (Abel & Huang), normalised to Gaussian 0.3173
    ed = []
    for t in (5, 10, 20, 40, 80, 160):
        a = int(t * FS / 1000); w = m[a:a + 960]
        ed.append((t, round(float(np.mean(np.abs(w) > np.std(w)) / 0.3173), 2)))
    r['echo_density'] = ed
    f, P = signal.welch(m[int(0.004 * FS):], FS, nperseg=4096)
    r['spectrum_third_oct'] = octave3(f, P)
    # notches of the first 50 ms (static phaser / flanger): local minima >= 10 dB below the 1/3-octave smoothed level
    H = np.abs(np.fft.rfft(m[:int(0.05 * FS)], 1 << 16)); fr = np.fft.rfftfreq(1 << 16, 1 / FS); Hd = db(H)
    k = np.arange(1, len(Hd) - 1); loc = k[(Hd[k] < Hd[k - 1]) & (Hd[k] <= Hd[k + 1])]
    notches = []
    for i in loc:
        f = fr[i]
        if f < 40 or f > 20000: continue
        win = (fr > f / 1.25) & (fr < f * 1.25)
        if np.max(Hd[win]) - Hd[i] >= 10: notches.append(round(float(f), 1))
    r['notches_hz'] = notches[:24]
    r['lr_corr_tail'] = round(float(np.corrcoef(ir[int(0.08 * FS):int(0.5 * FS), 0], ir[int(0.08 * FS):int(0.5 * FS), 1])[0, 1]), 3)
    return r

def inst_delay(z, f0):
    """instantaneous delay (ms) of a sinusoid at f0 relative to the stimulus phase, plus envelope"""
    a = signal.hilbert(z); ph = np.unwrap(np.angle(a)); t = np.arange(len(z)) / FS
    ph_rel = ph - 2 * np.pi * f0 * t
    ph_rel -= 2 * np.pi * np.round(np.median(ph_rel) / (2 * np.pi))
    return -ph_rel / (2 * np.pi * f0) * 1000, np.abs(a)

def modspec(v, fs):
    v = v - np.mean(v); n = len(v); F = np.fft.rfftfreq(n * 8, 1 / fs); S = np.abs(np.fft.rfft(v * np.hanning(n), n * 8))
    m = (F > 0.05) & (F < 20); k = np.argmax(S * m)
    return float(F[k])

def an_tone(y, x, mk, f0=500.0):
    nm, s0, n = mk[0]; r = {}
    sos = signal.butter(4, (f0 / 1.6, f0 * 1.6), 'bandpass', fs=FS, output='sos')
    for c, lab in ((0, 'L'), (1, 'R')):
        z = signal.sosfiltfilt(sos, y[s0 + 9600:s0 + n - 4800, c])
        d, e = inst_delay(z, f0)
        dec = 48; d2 = d[::dec]; e2 = e[::dec]
        rate = modspec(d2, FS / dec); ratea = modspec(db(e2), FS / dec)
        r[lab] = {'delay_mean_ms': round(float(np.mean(d2)), 3), 'delay_pp_ms': round(float(np.percentile(d2, 99) - np.percentile(d2, 1)), 3),
                  'fm_rate_hz': round(rate, 3), 'am_pp_db': round(float(np.percentile(db(e2), 99) - np.percentile(db(e2), 1)), 2),
                  'am_rate_hz': round(ratea, 3), 'level_db': round(float(rmsdb(z) - (-12 - 3.01)), 2)}
    return r

def an_tone440(y, x, mk):
    seg = {nm.split()[0]: (s0, n) for nm, s0, n in mk}
    s0, n = seg['tone']; r = {}
    z = y[s0 + 9600:s0 + n - 4800, 0]
    F, P = signal.periodogram(z, FS, window='hann', nfft=1 << 20)
    k = np.argmax(P[F > 50]) + np.argmax(F > 50)
    r['out_freq_hz'] = round(float(F[k]), 2); r['ratio_semitones'] = round(float(12 * np.log2(F[k] / 440.0)), 3)
    e = np.abs(signal.hilbert(z)); e = e[::24]
    r['am_rate_hz'] = round(modspec(db(e), FS / 24), 2)
    r['am_pp_db'] = round(float(np.percentile(db(e), 99) - np.percentile(db(e), 1)), 2)
    s0, n = seg['clicks']; z = y[s0:s0 + n, 0]
    # response to a click: duration until -40 dB of its peak (crossfade window length)
    seg_ = z[:int(0.25 * FS)]; env = np.abs(signal.hilbert(seg_)); pk = np.max(env)
    above = np.where(env > pk * 0.01)[0]
    r['click_resp_ms'] = round(float((above[-1] - above[0]) / FS * 1000), 2) if len(above) else None
    r['click_first_ms'] = round(float(above[0] / FS * 1000), 2) if len(above) else None
    return r

def an_fb(y, x, mk):
    nm, s0, n = mk[0]; z = y[:, 0] + y[:, 1]
    hop = 480; e = np.array([rmsdb(z[i:i + hop]) for i in range(s0, len(z) - hop, hop)])
    t = np.arange(len(e)) * hop / FS
    pk = int(np.argmax(e)); tail = e[pk:]; tt = t[pk:]
    good = tail > np.max(tail) - 60
    slope = np.polyfit(tt[good][:max(3, good.sum())], tail[good][:max(3, good.sum())], 1)[0] if good.sum() > 3 else 0
    return {'peak_db': round(float(e[pk] + 20), 1), 'peak_at_s': round(float(t[pk]), 2), 'decay_db_per_s': round(float(slope), 2),
            'level_at_6s_db': round(float(e[min(len(e) - 1, int(6 * FS / hop))] + 20), 1), 'level_at_11s_db': round(float(e[min(len(e) - 1, int(11 * FS / hop))] + 20), 1)}

def env_db(z, win=0.002):
    h = int(win * FS); k = np.ones(h) / h
    return 10 * np.log10(np.convolve(z ** 2, k, 'same') + 1e-20)

def an_gate(y, x, mk):
    z = (y[:, 0] + y[:, 1]) / 2; e = env_db(z); out = []
    for nm, s0, n in mk:
        seg = e[s0 - 480: s0 + n + int(1.4 * FS)]; pk = np.max(seg); t = np.arange(len(seg)) / FS * 1000 - 10
        on = np.where(seg > pk - 3)[0]
        a10 = np.argmax(seg > pk - 20); a90 = np.argmax(seg > pk - 1)
        endin = 480 + n
        last = np.where(seg > pk - 6)[0][-1] if len(np.where(seg > pk - 6)[0]) else 0
        r40 = np.where(seg > pk - 40)[0][-1] if len(np.where(seg > pk - 40)[0]) else 0
        out.append({'burst': nm, 'attack_ms_20to1dB': round(float((a90 - a10) / FS * 1000), 2), 'open_ms': round(float(t[a10]), 2),
                    'hold_after_input_ms': round(float((last - endin) / FS * 1000), 1), 'release_6to40_ms': round(float((r40 - last) / FS * 1000), 1)})
    return out

def an_gsweep(y, x, mk):
    z = (y[:, 0] + y[:, 1]) / 2; out = []
    for nm, s0, n in mk:
        lvl = float(nm.split()[-1])
        a = s0 + n + 480; b = a + 14400
        out.append((lvl, round(rmsdb(z[s0 + 2400:s0 + n - 2400]) - lvl, 1), round(rmsdb(z[a:b]), 1)))
    return out

def an_bursts(y, x, mk):
    z = (y[:, 0] + y[:, 1]) / 2; out = []
    for nm, s0, n in mk:
        lab = nm.split()[-1]
        out.append((lab, round(rmsdb(z[s0 + 2400:s0 + n]), 2), round(rmsdb(z[s0 + n + 2400:s0 + n + 24000]), 2)))
    return out

def an_enh(y, x, mk):
    fr = [97, 203, 511, 1013, 2027, 4001, 7919]; r = {'multitone': [], 'tone1k': []}
    for nm, s0, n in mk:
        zl, xl = y[s0 + 4800:s0 + n - 4800, 0], x[s0 + 4800:s0 + n - 4800, 0]
        if nm.startswith('multitone'):
            gains = [round(float(db(tone_amp(zl, f) / tone_amp(xl, f))), 2) for f in fr]
            F, P = signal.periodogram(zl, FS, window='hann'); tot = np.sum(P)
            mask = np.ones_like(F, bool)
            for f in fr: mask &= np.abs(F - f) > 8
            r['multitone'].append({'level': float(nm.split()[1]), 'gain_db': gains, 'distortion_db': round(float(10 * np.log10(np.sum(P[mask & (F > 20)]) / tot + 1e-20)), 1)})
        elif nm.startswith('tone'):
            a1 = tone_amp(zl, 1000)
            r['tone1k'].append({'level': float(nm.split()[-1]), 'gain_db': round(float(db(a1 / tone_amp(xl, 1000))), 2),
                                'h_db': [round(float(db(tone_amp(zl, 1000 * h) / a1)), 1) for h in range(2, 8)]})
        elif nm.startswith('noise'):
            f, Pxy = signal.csd(xl, zl, FS, nperseg=4096); f, Pxx = signal.welch(xl, FS, nperseg=4096)
            r['noise_tf'] = octave3(f, np.abs(Pxy / Pxx) ** 2)
    return r

def an_pcgap(y, x, mk, events):
    z = (y[:, 0] + y[:, 1]) / 2; e = env_db(z, 0.001); out = []
    nm, s0, n = mk[0]; base = np.median(e[s0 + 4800:s0 + int(1.8 * FS)])
    for ev in events:
        at = ev[1] if ev[1] >= 0 else ev[0]
        seg = e[at - 2400: at + int(0.8 * FS)] - base
        low = np.where(seg < -40)[0]; dip = np.where(seg < -3)[0]
        out.append({'event': ev[2], 'sent_sample': at,
                    'mute_start_ms': round(float((dip[0] - 2400) / FS * 1000), 1) if len(dip) else None,
                    'below_-40dB_ms': round(float(len(low) / FS * 1000), 1),
                    'dip_ms': round(float((dip[-1] - dip[0]) / FS * 1000), 1) if len(dip) else 0.0,
                    'min_db': round(float(np.min(seg)), 1)})
    return out

def an_rotsw(y, x, mk, events):
    nm, s0, n = mk[0]; z = y[:, 0]
    e = db(np.abs(signal.hilbert(signal.sosfiltfilt(signal.butter(4, (700, 1400), 'bandpass', fs=FS, output='sos'), z))))[::48]
    fs2 = FS / 48; win = int(1.0 * fs2); hop = int(0.1 * fs2); traj = []
    for i in range(int(s0 / 48), int((s0 + n) / 48) - win, hop):
        traj.append((round(i / fs2 - s0 / FS + 0.5, 2), round(modspec(e[i:i + win], fs2), 2)))
    return {'am_rate_traj': traj}

def read_events(path):
    ev = []
    if os.path.exists(path):
        for line in open(path).read().splitlines()[1:]:
            p = line.split('\t')
            ev.append((int(p[0]), int(p[1]) if p[1].lstrip('-').isdigit() else -1, p[2]))
    return ev

def main():
    rec, stims, plan, outp = sys.argv[1:5]; plug = '--plug' in sys.argv
    lines = [l.rstrip('\n').split('\t') for l in open(plan) if l.strip()]
    def path(b, nn, kind):
        for ext in ('.wav', '.f32'):
            p = os.path.join(rec, 'r4%s-%03d-%s%s' % (b, int(nn), kind, ext))
            if os.path.exists(p): return p
    stimcache = {}
    def stim(kind):
        if kind not in stimcache: stimcache[kind] = (load(os.path.join(stims, 'stim-%s.wav' % kind)), markers(stims, kind))
        return stimcache[kind]
    cal = Cal()
    res = {}
    if not plug:
        # Loop latency and gain come from run 1's direct calibration (1179 samples, L +0.9 dB, R -4.6 dB) and are
        # confirmed by the impulse peaks of every std capture. Don't derive them from the conv capture: its
        # periodic tones fool the cross-correlation, and its gain includes the dry program's own +6.4 dB.
        cal = Cal(1179, (10 ** (0.9 / 20), 10 ** (-4.6 / 20)))
        res['_cal'] = {'latency': cal.lat, 'gain_db': [0.9, -4.6]}
    for b, nn, kind, desc in lines:
        p = path(b, nn, kind)
        if not p: continue
        x, mk = stim(kind); y = cal.apply(load(p), len(x))
        ev = read_events(p.rsplit('.', 1)[0] + '-events.txt')
        ev = [(a, (c - cal.lat if c >= 0 else c), l) for a, c, l in ev]
        fn = {'conv': an_conv, 'std': an_std, 'note': an_std, 'tone': an_tone, 'tone440': an_tone440, 'fb': an_fb, 'gate': an_gate,
              'gsweep': an_gsweep, 'cc': an_bursts, 'pb': an_bursts, 'vel': an_bursts, 'enh': an_enh}.get(kind)
        try:
            if kind == 'pcgap': r = an_pcgap(y, x, mk, ev)
            elif kind == 'rotsw': r = an_rotsw(y, x, mk, ev)
            else: r = fn(y, x, mk)
        except Exception as e:
            r = {'error': repr(e)}
        res['%s-%s-%s' % (b, nn, kind)] = {'desc': desc, 'result': r}
    json.dump(res, open(outp, 'w'), indent=1)
    print(len(res), 'analysed ->', outp)

if __name__ == '__main__':
    main()
