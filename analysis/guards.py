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
