"""Analysis guards for hardware-vs-plug-in comparisons (DCI lab protocol, from RSP-550 run 9).

Each guard exists because a mistake got through without it:
  check_capture()   clipped captures (run-6 Wide Chorus / Soft Rotary) were analysed as if valid
  agree()           the 1.6.3 low-pass was fitted to one measure (full-window sweep transfer) that disagreed with the
                    echoes alone, noise and music; a tone conclusion now needs two independent measures to agree
  late_energy_shift()  late energy in the sweep window moving the top end (checked on the whole bank: never > 1 dB)
  per_channel()     a mono sum turned a 2-sample L/R offset into "5 dB brighter" (Light Flanger)
  holdout()         per-mode fits that matched their own recording and failed elsewhere (phaser modes 1/4)
  field_regression()  a parameter-driven error (reverb EQ High) hidden among single-program errors
  channel_timing()  per-algorithm L/R timing (the flanger's 2 samples) found only by accident
Round 2 (2026-10-21, from the DCI Overdrive chat, where each of these mistakes happened first):
  self_test()       every analyser here on known answers before it is used (a Hann window read a pure sine as -46 dB
                    "aliasing"; a band-summed coherence read a linear band-pass as 0.42): run it at the top of an analysis
  aligned()         the fractional lag between two renders/captures; a comparison more than 0.25 sample out is not
                    evidence (two alignment bugs showed as a lag before they showed as a bad null)
  transfer()        a transfer function with its coherence per bin, power-weighted per band: a band below 0.99 is
                    distortion or noise, not a transfer (full-band noise into a high-gain stage read 1 dB "off"); one
                    band dipping alone is a notch (leakage at a deep null reads 0.96), so the gate is the share of
                    coherent bands, and the level goes down until most are
  linear_level()    the quietest-needed level: a "small-signal" measure must agree with one 10 dB quieter (0.1 dB)
  masked_excess()   a residual per critical band against a masking threshold from the reference (with the threshold
                    of hearing at 0 dBFS = 100 dB SPL): how far above audibility a difference is (dB; below 0: inaudible)
  attack_nulls()    the first 20 ms after each onset nulled on its own (an overall null hides a softened attack)

Use them in every analysis; a guard that fires means the number is not evidence.
"""
import numpy as np

FS = 48000


class GuardError(Exception):
    pass


def check_capture(y, name='capture', clip=0.99, flat_run=4):
    """Reject a capture that clipped: a peak at full scale, or a run of identical samples at a channel's peak (clipped
    before a gain change, e.g. the loop-gain correction). Run-6 check: Wide Chorus and Soft Rotary caught (234/416
    samples at full scale), the other music captures pass."""
    y = np.asarray(y, float)
    pk = np.abs(y).max()
    if pk >= clip:
        raise GuardError('%s clipped (peak %.3f): re-record lower, do not analyse' % (name, pk))
    for c in range(y.shape[1] if y.ndim > 1 else 1):
        ch = y[:, c] if y.ndim > 1 else y
        top = np.abs(ch) >= np.abs(ch).max() * (1 - 1e-5)   # identical samples at the channel's own peak (a flat top);
        if np.convolve(top, np.ones(flat_run), 'valid').max() >= flat_run:   # a crest within a few % is normal music
            raise GuardError('%s channel %d has %d+ samples pinned at its peak: clipped upstream' % (name, c, flat_run))
    return pk


def late_energy_shift(ir, seg, fs=FS, late=72000, bands=(4000, 6300, 8000, 10000, 12500, 16000)):
    """How much the high bands of a full-window spectrum (ir[:seg]) move when the last `late` samples of that window
    are removed, in dB (largest band). Above 1 dB the window holds late energy that matters (a long delay tail, leakage
    from earlier stimulus parts, or a time-varying effect smeared by the deconvolution): the full-window spectrum is
    not evidence; use gated IR spectra, noise or click trains. This is what inflated the 1.6.3 delay top end."""
    ir = np.asarray(ir, float)[:seg]
    def spec(h):
        H = np.abs(np.fft.rfft(h, seg)) ** 2; f = np.fft.rfftfreq(seg, 1 / fs)
        return np.array([10 * np.log10(H[(f >= c / 1.12) & (f < c * 1.12)].mean() + 1e-30) for c in bands])
    cut = ir.copy(); cut[seg - late:] = 0.0
    return float(np.max(np.abs(spec(ir) - spec(cut))))


def assert_window_valid(ir, seg, name='', limit=1.0):
    d = late_energy_shift(ir, seg)
    if d > limit:
        raise GuardError('%s: late energy moves the 4-16 kHz bands by %.1f dB; the full-window spectrum is not valid' % (name, d))
    return d


def agree(measures, tol=1.5):
    """measures: {name: array of band errors (hw - plug, dB) on the same bands}. At least two independent measures
    (e.g. gated sweep IR, noise, music, click train) must agree within tol dB in every band before an error is
    fitted. Returns the mean; raises when they disagree."""
    if len(measures) < 2:
        raise GuardError('only one measure (%s): a tone fit needs two independent measures that agree' % list(measures))
    m = np.array(list(measures.values()), float); spread = m.max(0) - m.min(0)
    if np.any(spread > tol):
        k = int(np.argmax(spread))
        raise GuardError('measures disagree by %.1f dB in band %d (%s): find out why before fitting' % (spread[k], k, ', '.join(measures)))
    return m.mean(0)


def per_channel(fn, hw, plug):
    """Apply a per-channel measure (fn(signal_1d) -> array) to both channels and return the mean hw - plug. Never
    sum channels: L/R timing differences become comb filtering in a mono sum."""
    hw = np.asarray(hw, float); plug = np.asarray(plug, float)
    if hw.ndim != 2 or plug.ndim != 2:
        raise GuardError('per_channel needs stereo arrays (n, 2); got %s and %s' % (hw.shape, plug.shape))
    return np.mean([np.asarray(fn(hw[:, c])) - np.asarray(fn(plug[:, c])) for c in (0, 1)], 0)


def mono_sum_forbidden(*a, **k):
    raise GuardError('mono sums are not allowed for stereo comparisons; use per_channel()')


def holdout(fit_items, check_items, evaluate, candidates, base):
    """Fit on fit_items, keep a candidate only if check_items (never used for fitting) also improve.
    evaluate(items, candidate) -> error (lower is better). Returns (best_candidate_or_base, report)."""
    b_fit = evaluate(fit_items, base); b_chk = evaluate(check_items, base)
    best = min(candidates, key=lambda c: evaluate(fit_items, c))
    f, k = evaluate(fit_items, best), evaluate(check_items, best)
    keep = f < b_fit and k < b_chk
    report = 'fit %.2f -> %.2f, held-out %.2f -> %.2f: %s' % (b_fit, f, b_chk, k, 'KEEP' if keep else 'REJECT (held-out recordings disagree)')
    return (best if keep else base), report


def field_regression(errors, fields, min_n=12, min_values=4):
    """errors: {program: error value}; fields: {program: {field name: value}}. Returns [(|rho|, rho, slope, n, field)]
    sorted by strength: the stored settings that an error follows across the bank. Rank correlation (one extreme
    program cannot carry it), at least min_n programs and min_values distinct settings."""
    def ranks(v):
        v = np.asarray(v, float); o = np.argsort(v); r = np.empty(len(v)); r[o] = np.arange(len(v))
        for u in np.unique(v): r[v == u] = r[v == u].mean()
        return r
    names = set()
    for f in fields.values(): names |= set(f)
    out = []
    for nm in names:
        xs, ys = [], []
        for p, e in errors.items():
            if p in fields and nm in fields[p] and np.isfinite(e):
                xs.append(fields[p][nm]); ys.append(e)
        if len(xs) >= min_n and len(set(xs)) >= min_values:
            rho = np.corrcoef(ranks(xs), ranks(ys))[0, 1]; out.append((abs(rho), rho, np.polyfit(xs, ys, 1)[0], len(xs), nm))
    return sorted(out, reverse=True)


def channel_timing(ir_l, ir_r, right_offset=0, search=48):
    """Sample index of the first strong arrival on each channel of a deconvolved IR (direct or first echo), after
    removing a known loop offset of the right channel. Returns (left, right, right - left)."""
    def first(h):
        h = np.abs(np.concatenate([h[-search:], h[:search * 4]])); return int(np.argmax(h > 0.5 * h.max())) - search
    l = first(np.asarray(ir_l, float)); r = first(np.roll(np.asarray(ir_r, float), right_offset))
    return l, r, r - l


# ---------------------------------------------------------------------------------- round 2 (2026-10-21)
def bh(n):
    """4-term Blackman-Harris window (sidelobes -92 dB; a Hann window leaks to about -46 dB)"""
    k = np.arange(n); p = 2 * np.pi * k / n
    return 0.35875 - 0.48829 * np.cos(p) + 0.14128 * np.cos(2 * p) - 0.01168 * np.cos(3 * p)


def aligned(ref, y, maxlag=48, limit=0.25):
    """The delay of y against ref (fractional samples, by a frequency-domain shift search) and the null there.
    Raises GuardError when more than `limit` samples: line them up before comparing (or find out why they differ)."""
    ref = np.asarray(ref, float); y = np.asarray(y, float); n = min(len(ref), len(y)); ref, y = ref[:n], y[:n]
    Y = np.fft.rfft(y); f = np.fft.rfftfreq(n, 1 / FS)
    def null(l):
        r = np.fft.irfft(Y * np.exp(2j * np.pi * f * l / FS), n) - ref
        return 10 * np.log10(np.mean(r ** 2) / (np.mean(ref ** 2) + 1e-30) + 1e-30)
    coarse = min(np.arange(-maxlag, maxlag + 1e-9, 0.5), key=null)
    lag = float(min(np.arange(coarse - 0.5, coarse + 0.5 + 1e-9, 0.025), key=null))
    if abs(lag) > limit:
        raise GuardError('the two are %.2f samples apart: align them (or explain the delay) before comparing' % lag)
    return lag, null(lag)


def transfer(x, y, bands, nper=16384):
    """Welch transfer of y against x per band (dB) and the band's coherence (per bin, weighted by the output's
    power). Returns (gain_db, coherence, share of bands at 0.99 or more)."""
    from scipy import signal
    f, Sxy = signal.csd(x, y, FS, window='hann', nperseg=nper); _, Sxx = signal.welch(x, FS, window='hann', nperseg=nper)
    _, Syy = signal.welch(y, FS, window='hann', nperseg=nper)
    C = np.abs(Sxy) ** 2 / (Sxx * Syy + 1e-300); g, co = [], []
    for lo, hi in bands:
        m = (f >= lo) & (f < hi)
        g.append(10 * np.log10(Syy[m].sum() / (Sxx[m].sum() + 1e-300) + 1e-30)); co.append((C[m] * Syy[m]).sum() / (Syy[m].sum() + 1e-300))
    co = np.array(co); return np.array(g), co, float(np.mean(co >= 0.99))


def linear_level(measure, level, step=10.0, tol=0.1, floor=-100.0):
    """measure(level_dbfs) -> array. Goes down in `step` dB until the measure agrees with one `step` quieter within
    tol dB; returns that level. Raises when nothing is linear above `floor`."""
    L = level
    while L - step >= floor:
        if np.max(np.abs(np.asarray(measure(L)) - np.asarray(measure(L - step)))) < tol: return L
        L -= step
    raise GuardError('no linear level above %.0f dBFS: the "small-signal" measure keeps moving with level' % floor)


BARK = [20, 100, 200, 300, 400, 510, 630, 770, 920, 1080, 1270, 1480, 1720, 2000, 2320, 2700, 3150, 3700, 4400, 5300,
        6400, 7700, 9500, 12000, 15500, 20000]


def masked_excess(ref, y):
    """Worst critical band of (y - ref) over a masking threshold from ref (spreading -25 dB/Bark down, -10 dB/Bark
    up, 18 dB under the masker; the threshold of hearing with 0 dBFS = 100 dB SPL). Returns (dB over, centre Hz)."""
    ref = np.asarray(ref, float); y = np.asarray(y, float); N = 1 << 15; w = bh(N)
    f = np.fft.rfftfreq(N, 1 / FS); Pr = np.zeros(len(BARK) - 1); Pe = np.zeros_like(Pr); cnt = 0
    for a in range(0, min(len(ref), len(y)) - N, N // 2):
        R = np.abs(np.fft.rfft(ref[a:a + N] * w)) ** 2; E = np.abs(np.fft.rfft((y[a:a + N] - ref[a:a + N]) * w)) ** 2; cnt += 1
        for b in range(len(Pr)):
            m = (f >= BARK[b]) & (f < BARK[b + 1]); Pr[b] += R[m].sum(); Pe[b] += E[m].sum()
    if cnt == 0: raise GuardError('masked_excess needs at least %d samples' % N)
    Lr = 10 * np.log10(Pr + 1e-30); Le = 10 * np.log10(Pe + 1e-30); thr = np.full_like(Lr, -1e9)
    for i in range(len(Lr)):
        for j in range(len(Lr)):
            d = i - j; s = (Lr[j] - 18) - (25 * -d if d < 0 else 10 * d); thr[i] = 10 * np.log10(10 ** (thr[i] / 10) + 10 ** (s / 10))
    fc = np.sqrt(np.array(BARK[:-1]) * np.array(BARK[1:])) / 1000
    ath = 3.64 * fc ** -0.8 - 6.5 * np.exp(-0.6 * (fc - 3.3) ** 2) + 1e-3 * fc ** 4 - 100
    thr = np.maximum(thr, 10 * np.log10(cnt * np.sum(w ** 2) * N / 2) + ath)
    ex = Le - thr; i = int(np.argmax(ex)); return float(ex[i]), float(np.sqrt(BARK[i] * BARK[i + 1]))


def attack_nulls(ref, y, onsets, length=0.02):
    """The null (dB re ref) over the first `length` s after each onset (seconds)."""
    ref = np.asarray(ref, float); y = np.asarray(y, float); out = []
    for t in onsets:
        a, b = int(t * FS), int((t + length) * FS)
        out.append(10 * np.log10(np.mean((y[a:b] - ref[a:b]) ** 2) / (np.mean(ref[a:b] ** 2) + 1e-30) + 1e-30))
    return np.array(out)


def self_test():
    """Every analyser above on known answers. Returns a list of failures (empty: all good). Run it first."""
    from scipy import signal
    bad = []; rng = np.random.default_rng(5); t = np.arange(4 * FS) / FS
    # spectrum window: a pure sine, nothing away from it above the sidelobes
    N = 1 << 16; s = np.sin(2 * np.pi * 1234.5 * t[:N]); P = np.abs(np.fft.rfft(s * bh(N))) ** 2; f = np.fft.rfftfreq(N, 1 / FS)
    if 10 * np.log10(P[np.abs(f - 1234.5) > 8 * FS / N].max() / P.max()) > -90: bad.append('bh window leaks above -90 dB')
    # lag: a known 1.5-sample delay
    x = rng.normal(size=FS) ; b, a = signal.butter(4, 14000, fs=FS); x = signal.lfilter(b, a, x)
    X = np.fft.rfft(x); fx = np.fft.rfftfreq(len(x), 1 / FS); d = np.fft.irfft(X * np.exp(-2j * np.pi * fx * 1.5 / FS), len(x))
    try: aligned(x, d, limit=10)
    except GuardError as e: bad.append('aligned: ' + str(e))
    if abs(aligned(x, d, limit=10)[0] - 1.5) > 0.05: bad.append('aligned did not find a 1.5-sample delay')
    # transfer: identity 0 dB coherence 1; a linear band-pass coherence 1; distortion low coherence
    xx = rng.normal(size=8 * FS) * 0.1; xx = signal.lfilter(b, a, xx); bands = [(c / 1.41, c * 1.41) for c in (125, 250, 500, 1000, 2000, 4000, 8000)]
    g, co, share = transfer(xx, xx, bands)
    if np.max(np.abs(g)) > 0.01 or share < 1: bad.append('transfer(identity) not 0 dB / coherent')
    bb, ba = signal.butter(1, [720, 884], 'bandpass', fs=FS); g, co, share = transfer(xx, signal.lfilter(bb, ba, xx), bands)
    if share < 1: bad.append('transfer: a linear band-pass read as incoherent (%.2f)' % co.min())
    g, co, share = transfer(xx, np.tanh(30 * xx), bands)
    if share > 0.5: bad.append('transfer: a hard clipper read as coherent')
    # masked: a tiny residual inaudible, a -10 dB noise residual audible
    m1, _ = masked_excess(xx, xx + 1e-7 * rng.normal(size=len(xx))); m2, _ = masked_excess(xx, xx + 0.3 * np.std(xx) * rng.normal(size=len(xx)))
    if not (m1 < -10 and m2 > 0): bad.append('masked_excess: %.0f dB (tiny) / %.0f dB (-10 dB noise)' % (m1, m2))
    # linear_level: a soft clipper is linear well below its knee
    try:
        L = linear_level(lambda lv: [20 * np.log10(np.std(np.tanh(10 ** (lv / 20) * xx / np.std(xx))) / (10 ** (lv / 20)))], 0)
        if L > -10: bad.append('linear_level stopped at %.0f dBFS on tanh' % L)
    except GuardError as e: bad.append('linear_level: ' + str(e))
    # attack nulls: identical 0 (very low), a softened attack high
    an = attack_nulls(xx, xx, [1.0]); soft = xx.copy(); soft[FS:FS + 480] *= 0.5; an2 = attack_nulls(xx, soft, [1.0])
    if an[0] > -200 or an2[0] < -10: bad.append('attack_nulls')
    return bad
