
## Run-1 re-analysis (SSP-550 1.5.8)
- **Align each channel to its own arrival before windowing.** In this loop the right channel arrives 33 samples
  (0.69 ms) before the left on every program, dry ones included, so it is the capture path, not the unit.
  A direct-sound window centred on the left arrival read the right direct as -11 to -29 dB; aligned, it matches within 0.7 dB.
- **Make sure the "old" side of a comparison is the shipped build, not a trial render.**
- Direct-path window (first ~1.5 ms of the sweep IR, per channel) separates direct-level errors from effect-level
  errors: it found the Vocoder Mic Mix (+12 dB on the unit) and SDD-320 (whole output -6 dB).

## Run 6 (SSP-550 1.5.9)
- **Level fields are absolute.** Test each effect/direct level at 100 and 50 with the other at 0; a plug-in that turns
  them into a ratio is wrong whenever both are below 100.
- **One-sided noise (stereo kind) finds routing errors the bank sweep can't:** pan laws (linear on this unit),
  mono-summing effects (SDD-320), carrier/modulator inputs (vocoder).
- **Check that MIDI notes reached the unit** before concluding it ignores them (run 6: identical with and without).
- **Keep test programs clean:** a base program's other blocks (alg 38's 62 % delay feedback) contaminate a reverb test.
- **Tone tracking fails on the unit's flanger**; use the AM rate or a click train instead.
- **Two stimuli can disagree on level** for level-dependent effects (vocoder, possibly Ambience); fit to both, say so.

## Run 7 (SSP-550 1.6.0): follow-up rounds
- **Interactive rounds work:** after the planned batches the runner waits; Claude analyses, drops roundN-tests.syx then
  roundN-plan.txt (plan last, unique staged names, mv into place, md5), and the user presses Return. Four rounds
  settled what a separate run would have needed. Extra Returns before the files exist are harmless.
- **Swap one setting at a time from a matching program into a mismatching one** to find the cause (phaser Mode).
- **Click trains track modulation where tones fail:** the RSP-550 flanger sweeps exponentially over 1.5 octaves;
  tone tracking had read 0.7 ms. Search for the echo after the direct sound (the unit kept its direct on).
- **A per-channel offset that equals the loop's channel lead is the loop**, not the unit (run 5 flanger "R 0.65 ms").
- **Sweep vs noise disagreement on resonant effects** means a tonal difference (pink vs white weighting), not level.
- **Test programs can fit while factory programs don't** (Ambience): check the bank before keeping a fit.
- **Pick test notes away from the likely reference** (note 48 may be the chord root) and confirm notes act at all.

## Data-only pass and run 8 (SSP-550 1.6.1-1.6.2)
- **Compare tone on noise, not only on the sweep, for anything modulated or level-dependent.** The sweep sees a
  different modulation state per frequency; a sweep-vs-noise level disagreement usually means a tonal difference
  (Ambience: a +26 dB low shelf on the unit explained it).
- **Validate per-mode fits on recordings they were not fitted to.** The phaser per-mode fit improved its own test
  but worsened independent ones for two of six modes; keep only what generalises.
- **Shared blocks (program EQ) can be fitted on the cleanest programs** (wet-only reverb copies) and benefit all.
- **Click trains also measure chorus voices** (position and swing); the earlier Doppler estimate was 2x off.
- **Keep the scratch disk clean during fits**: a full disk silently truncated renders (empty files, absurd results).
- **Watch for one recording that no model can match** (Vocoder sweep passing 20 Hz): flag it rather than fit to it.

## RSP-550 v1.6.3 (brightness, A/B levels)
- "Everything a bit brighter": the unit band-limits the effect path of its delay/modulation algorithms at about 11 kHz (2-pole). Plug-in now does the same (AlgoInfo::bandLimit, wetLp); bank HF error for those programs went from -1.6/-2.1/-3.0 dB to -0.2/+0.3/+2.3 dB at 10k/12.5k/16k.
- A/B pairs must be loudness-matched (BS.1770 gated) or the louder side sounds "better/brighter". Keep the raw level difference in a note next to them.
- WAV files delivered to the Mac get a C2PA chunk appended, so whole-file md5 never matches. Verify WAVs by hashing the data chunk only.

## RSP-550 v1.6.4 (tone from existing recordings, no session)
- The 1.6.3 low-pass was fitted to one measure (the full-window sweep transfer) that disagreed with the echoes measured alone (gated IR from 4 ms), noise and music. Run-9 preparation ruled out late energy in the window as the cause (never > 1 dB on any program); the cause is open. Rule since: a tone fit needs two independent measures that agree (guards.agree).
- Never judge stereo effects on a mono sum. The unit's Stereo Flanger puts its right output 2 samples behind the left; summed, that flips phase near 12 kHz and looked like "5 dB brighter". Compare per channel (power sum).
- A tone test cannot tell one voice sweeping both ways from two voices in opposite phase (both give equal up/down lines). A click train can: per-channel delay tracks and the L/R lag of the pattern. The two-voice guess made Wide Chorus mono.
- Look for parameter-driven errors across the bank: regress the per-program error on each stored field. Reverb top end followed EQ High at -0.7 dB/dB (the unit's high shelf acts at about half gain).
- Fit on one recording, keep only if held-out recordings of the same mode/algorithm also improve (phaser mode 1 kept, mode 4 dropped).
- Run-9 queue: phaser mode 4 tone (recordings disagree), Bright Plate*/Industrial*/Church* wet levels, Shimmer and Soft Rotary levels (re-record music at -20 so nothing clips), Jet Flanging +3.7 dB.

## Protocol from run 9 (guards, replay, parity, integrity)
- Before any session: generate the tests from the plug-in's own field tables (devices/rsp550/fields.tsv, made by a
  dump of the algorithm table) so "direct off, depth 0, feedback 0, EQ flat" uses real value tables, not guessed raws;
  render every test through the plug-in and run analysis/validate_tests.py (direct really off, effect present, EQ steps
  change the sound, nothing above 0.89 peak). Run 9's first pass caught a multi-effect test with a direct level
  left at 100 and a phaser test that would have clipped.
- Effect-only tests need the stages after the measured one set to pass through (direct 100, effect 0), not just
  switched off: a switched-off block may not behave as a bypass on the unit.
- Runner (Run4.h): a clipped capture is retaken at once 10 dB lower ("-m10"); repeat recordings never overwrite
  ("-rep2"); batch Z replays repeatability references at the end of the session (drift); filelo/file2lo/file3lo
  play music 10 dB below "file" (ab-source.wav / ab-source2.wav / ab-source3.wav).
- After every build, without the unit:
  1. Plug-in integrity (in the plug-in's own test): every field at min and max, block-size and sample-rate
     independence (transfer per octave, not absolute level), determinism and reset, state reload, parameter jumps
     (high-frequency burst against both steady states, -40 dB re signal floor; time, switch and filter controls
     reported only), 20 s of random MIDI. SSP-550 1.6.5: found clicks on level knobs (fixed with a knob glide).
  2. Render parity (analysis/parity.py): the analysis renderer against the real processor on every program; load
     the program before preparing (or the 12 ms algorithm switch shifts every LFO); load the bank in slot order.
     Found: renderers did not clamp out-of-range stored values like the plug-in (Gate Mode 3).
  3. Replay (analysis/replay.py + replay_diff.py): every targeted test of all earlier runs re-rendered and scored per
     channel (level, tone); scores saved per build and diffed.
  4. Bank check (analysis/bankcheck.py): per-program L/R timing of the first arrival, late-energy flags,
     setting regression (rank correlation, >= 12 programs, >= 4 distinct values).
- Guards (analysis/guards.py), used by all analysis: check_capture (full scale or identical samples at the peak; a
  crest within a few % is normal music), per_channel (never a mono sum), agree (two independent measures before a
  tone fit), holdout (fit on some recordings, keep only if held-out ones improve), field_regression, channel_timing.
- Blind ABX page for listening checks: loudness-matched pairs, the unit's measured hiss added to the plug-in files
  (~60 dB under the music, audible in gaps), results saved where Claude reads them.

## Listening test closes every hardware build (user rule, 2026-10-19)
- A hardware-model build is not finished until its blind listening test is published: make loudness-matched A/B
  pairs from the build (hardware capture vs plug-in render of the same material), run
  `analysis/abx/make_abx.py <pairs> <out> --unit <unit> --plug <plug-in> --build <version>` (adds the unit's measured
  hiss to the plug-in files, fills `analysis/abx/template.html`), and publish `<out>/index.html` with `audio/*.wav`
  and capabilities `{db: {}, user: {}}` to the SAME page URL as the unit's previous build. Results are saved per
  build in the page's `abx` collection; read them (ArtifactData list) before the next build and say what they show.
- Listening pages: RSP-550 / SSP-550 https://claude.ai/artifact/WJeoiRSpCVW1TLNfLQNrVz

## Listening results, SSP-550 1.6.5 (2026-10-19)
- Warm Plate 9/10 (chance 1.1 %): reliably heard. Loudness-matched music, unit minus plug-in: 250-500 Hz -1.6/-2.6 dB, 1 kHz +2.2, 2-8 kHz +0.5..+1.0. The plug-in has more low-mid and less 1 kHz: the program's EQ (Mid -3 dB at 400 Hz, Low -3 dB) acts differently. Run 9's EQ series (Mid/Low/High at +-12 on a reverb and a delay) measures exactly this.
- Large Hall 1 8/10 (chance 5.5 %), note "overall brighter": borderline. Unit minus plug-in: 250 Hz +1.8, 500 Hz-1 kHz -1.4/-1.6, 2-16 kHz about -0.5: the plug-in has less low end and slightly more mids/top, so it reads brighter.
- Not tested yet: Wide Chorus, Light Flanger, Shimmer, Soft Rotary.

## Additions from the DCI Reverb reference lab (2026-10-20): check before the next session
Source: dci-effects `docs/REFERENCE_LAB_PROTOCOL.md`, skill `dci-reference-lab`. Run 9's protocol already covers
replay, parity, guards, hold-out, repeatability and ABX. These were missing; add them to the next run's batches:
- **Variance per measure:** the same impulse or click several times at different moments (4 starts 0.37-1.2 s apart),
  per reverb program. The spread of each measure (T30 per band, echo density, build-up, early/late) becomes the fit
  tolerance. Batch Z measures drift over the session, but not this. The 480L Random Hall varied 37 ms in build-up
  between repeats; the 224 almost nothing.
- **Level steps on the reverbs:** the same sweep at -24, -12 and 0 dBFS per reverb program. Look at T30, tone and
  distortion. The 224 Plate's decay changed with level (2.3 s at -24, 5.5 s at -12 dBFS), and a level-dependent unit
  looks wrong in every other test unless this is known. Re-take any clipped capture lower, as the runner already does.
- **Long tones for reverb modulation:** 2 s tones at 250 / 500 / 1000 / 2000 / 4000 Hz. Measure spectral spread
  (cents), modulation rate and level wobble over the last 1.5 s. Short windows overstated modulation about 4x. Click
  trains remain right for flangers and choruses.
- **Click-to-click similarity on reverbs:** a 4 Hz click train for 3 s. Correlate each click's first 100 ms, measured
  from the unit's own onset (a long pre-delay otherwise gives a silent window and NaN). Static reverbs read 0.9 or
  more; randomised ones (480L Random Hall) read 0.05.
- **Pre-delay meaning:** the impulse with pre-delay 0 and 50 ms. This shows whether the onset moves by the full amount
  or from the unit's own minimum (the 224's counted from about 25 ms).
- **No session needed, from recordings you already have:**
  - decay shape: EDT, T20, late slope and curvature at 500 Hz / 1 kHz / 4 kHz (the 480L halls bow: curvature 0.53-0.71);
  - energy-weighted echo density at 0-50 / 50-150 / 150-300 ms;
  - band build-up peaks at 250 Hz / 1 kHz / 4 kHz.
- **The same battery through the plug-in:** run every new test through the SSP-550 plug-in too (replay does this
  once the test is in a plan), so each measure is compared on both sides.
- **Plug-in reset:** the SSP-550 processor has no `AudioProcessor::reset()` override. An AU host's stop, locate or
  offline bounce leaves its tail running, and AU renders differ from VST3. DCI Reverb rendered -5 to -20 dB apart
  Mac/Linux because of this; matched, -122 dB. Add the override (clear as prepare does, no allocation) and the
  dci-core plug-in check `hostreset` (dci-core 3554554).
- **Installs on the Mac:** remove the old bundle before copying, or macOS kills every host that loads it ("Code
  Signature Invalid"). That happened to DCI Reverb and Tape Echo on 2026-10-20.

## Run 10 prepared: the reference-lab battery on the RSP-550 (2026-10-20, SSP-550 1.6.6)
- Everything in the section above is in run 10 (`devices/rsp550/make_run10.py`, `plan10.txt`, `slots10.json`;
  launcher `RSP-550-run10.command`; 103 captures, about 50 min). Run 9 has not been run yet; run 10 is meant to follow
  it but works on its own.
- The runner (`lab-tool/Source/Run4.h`) gained kind `wav:<name>`: it plays `run10/stim/<name>.wav` at that file's rate,
  switching the interface to 96 kHz and back for the 96 kHz sweep (a refused rate is logged and skipped). The stimuli
  are the reverb lab's own (`dci-effects tools/reverblab/make_run3.py`), so `analyse_run3.py` measures the unit and
  ours with the same code. `analysis/lab10.py` cuts captures (loop latency and gain removed) and our renders into the
  reverb lab's file layout, adds the unit's idle noise to ours, measures both and compares them, tolerance from the
  unit's own spread over its 4 impulses.
- The 0 dBFS sweep would clip the interface on every factory program (our renders peak +4 to +18 dBFS), so the level
  series runs on copies with Total Level lowered; the factory programs get the -12 dBFS sweep only. Our model's
  output at 0 dBFS input goes far above full scale (Light Flanger +20 dBFS): the unit cannot, so run 10 shows where
  its converters or internal word length clip, which the model does not have yet.
- Decay measures (EDT, shape, density, build-up) on factory programs are dominated by the direct sound; wet-only
  copies of the 8 reverb programs carry them.
- Self-test before trusting captures: our renders put through the loop model and analysed as the unit match ours
  on 97 % or more of measures (gating in `run_all.sh`).
- **Replay was scoring the wrong renderer.** `render4` has only the effect engines; since 1.6.4 the plug-in adds per-
  algorithm wet low-pass and shelf and output scaling in its processor. Parity render4 vs plug-in failed on 7 of 8
  programs (up to 11 dB in a band). `replay.py` now renders with the plug-in's own `SSP550Test --render` when given
  that binary; `render4` parity is reported every run. Fits made with render4 since 1.6.4 need checking on the plug-in.
- **The plug-in's bank loader ignores SysEx addresses**: it fills programs 1, 2, 3 ... in file order. A test bank
  loaded alone (slots 101-128) lands in programs 1-28, so `--render` of program 106 played the factory copy. Renders
  now load the unit's whole backup in slot order with the test programs overlaid in their own slots
  (`lab10.py slotbank`; replay caches one per test bank, keyed by path: runs 6 and 7 both have a `tests4C.syx`).
- Replay with the real plug-in (baseline `scores-plug166.json`): run 6 median level 0.84 dB, tone 0.79 dB; run 7
  1.46 / 0.81; run 8 1.31 / 1.15. 1.6.6 = 1.6.5 (no measure moved > 0.3 dB). The render4 scores (`scores-v16x`) are
  kept for history only; `scores-v164.json` was also made before 1.6.4's last changes.
- Test list: `devices/rsp550/TESTS.md` and `run_all.sh`.

## 2026-10-21: test round 2 (from the DCI Overdrive chat)
- `analysis/guards.py` round 2: `self_test()` (run it first: every analyser on known answers), `aligned()` (fractional
  lag; more than 0.25 sample is not evidence), `transfer()` (coherence per bin, power-weighted per band; the gate is the
  share of coherent bands, since a deep notch alone reads 0.96), `linear_level()`, `masked_excess()` (audibility of a
  difference), `attack_nulls()`. Each came from a mistake made first in the Overdrive's own analysis (a Hann window
  read a pure sine as -46 dB aliasing; a band-summed coherence read a linear band-pass as 0.42; a "reference" at the
  same internal rate as the render it was judging).
- `analysis/stimuli_round2.py`: what the next unit's capture battery should add (coherent-level noise, SMPTE and chord
  intermodulation, burst recovery, a level staircase, plucks for attack nulls), 50 s in all.

## Listening results, SSP-550 1.6.6 (2026-11-02)
| Program | Right of 10 | Reading |
|---|---|---|
| Large Hall 1 | 9 | real difference (1.6.5: 8, "overall brighter") |
| Soft Rotary | 8 | real difference (8 or more) |
| Light Flanger | 7 | not reliable |
| Wide Chorus | 6 | no difference (saved by Claude from the chat: the page's Save button stuck after one save, fixed) |
| Shimmer | 6 | no difference |
| Warm Plate | not retested | 1.6.5: 9 of 10 |
Next work: Large Hall 1 and Warm Plate (run 10 measures both in full, with and without the direct sound), then Soft
Rotary (not in run 10's battery: needs its own rotary tests in a later run).

## Run 9 (2026-11-02, SSP-550 1.6.6): the left return dropped out
- 86 captures, none clipped. 38 of them (A-111 to B-087, about 01:14-01:33, plus the start of C-101) have the left
  return dead in places: -100 to -113 dBFS on the left, below the unit's own idle noise (-88 to -91), while the right
  carried signal. A loose cable or socket between the RSP-550's left output and interface input 5; batches C (after
  C-101) and Z were clean. Runs 6-8 show no such dropout.
- New guard `guards.check_dropout` (a 0.25 s block below -97 dBFS on one channel while the other is above -80);
  replay applies it, and the runner (`Run4.h`) now says "LEFT/RIGHT RETURN DEAD" in the log and retakes the capture
  once. Guards now look at the capture as recorded: `check_capture` after the loop-gain correction had called C-108
  clipped (1.10) when its real peak was 0.68.
- The 38 lost captures are retaken as run 10's follow-up round 1 (`devices/rsp550/run10-round1-plan.txt`).
- The user was asked to reseat or replace that cable before run 10.
- Run 9's clean captures (`analysis/run9/`): the program EQ shelves are 2nd order with Q about 0.48, low at 394 Hz
  and high at 3842 Hz (Stereo Delay and wet-only hall agree; fit 0.08 / 0.05 dB rms). The plug-in had 160 Hz / 6 kHz
  at Q 0.71. On the hall, high-shelf cuts saturate where the early reflections dominate while boosts and the low
  shelf act in full: possibly the EQ acts on the late field only (that fits the high shelf, not the low one).
  Any Mid setting moved the whole hall by -6 dB below 1 kHz: run 10 round 2 measures the Mid band on the delay
  (`gen_run10_round2.py`) and tests the late-only idea (ER level 0).
- SSP-550 1.6.7 candidate (not released): the new shelves, Stereo Chorus output 1.4 -> 1.06, Ambience +2 dB
  (both refitted after the shelves; held across runs 6-9). Replay with the plug-in: medians better in every run
  (run 6 level 0.84 -> 0.70, tone 0.79 -> 0.73; run 9 1.54 / 1.82 -> 1.17 / 1.08). On music, Large Hall 1 still
  lacks 1-2.4 dB at 100-250 Hz (heard as "brighter") and Warm Plate has 1.5 dB too much at 100-250 Hz and 2 dB too
  little at 1 kHz: run 10 (wet-only decay per band) and round 2 (Mid EQ) address those.
- 2026-11-03 loop check (`rsplab loopcheck`): the left return was dead on input 5 (floor -113 dBFS, tones 30-50 dB
  down). The user moved the RSP-550's outputs to interface inputs 7/8 and reseated the output cables at the RSP-550;
  then LOOP OK (both floors -86/-89 dBFS, no dropouts while the cables were moved). Run 10 and the loop check now read
  returns 7/8. Loop gain on 7/8 is not yet calibrated: run 10's Z captures (1 and 54, `std`) against run 9's clean
  B-001/Z captures give the per-channel change (the 5/6 calibration was L +0.9, R -4.6 dB).

## Runs 10 and 10b (2026-11-03) and SSP-550 1.6.7
- Calibration on returns 7/8: the direct impulse arrives at 1133 samples on both channels; on 5/6 input 5 delivered the
  left 32 samples late, which was the "right 33 samples early" of every earlier run. Gains L +0.4, R -0.1 dB from the
  unit's own symmetric signals in the same session (`lab10.py`, `LATS` / `GAIN`; `LAB10_CAL=56` selects the old ones).
  An energy comparison of whole captures across sessions had given R -4.9 dB and made cross-feed look 6 dB lopsided.
  Absolute level on 7/8 is still uncertain (music pairs read +2 to +4 dB plug-in excess everywhere): do not fit levels
  from runs 10/10b.
- Sweep deconvolution reads the unit's top octave low because the unit runs on its own clock (the sweep drifts against
  the inverse filter). For high-frequency tone use steady pink noise or music: there LH1 and Warm Plate are within ~1 dB.
- Program EQ (run 10b round 2, Stereo Delay, `analysis/run10/mideq.py`, `fitmid*.py`): Mid is a peak at the full set
  gain, Q 0.98 for cuts and 0.79 for boosts (500 Hz - 4 kHz, -12 to +12 dB). Shelves 394 Hz Q 0.47, 3842 Hz Q 0.49.
- Reverbs: with ER level 0 the EQ moves the hall fully, so the program EQ acts on the late field only; the early
  reflections bypass it and are high-passed near 1.2 kHz (`grid_erhp.py`). A non-zero Mid lowers the late field by
  |gain|/2 dB (the "whole hall -6 dB" of run 9 at Mid +-12).
- Pre-delay test (imp1 with 0 / 50 ms): the direct sound dominates the onset and lag measures, so it says nothing about
  the reverb's pre-delay; only Large Hall 1's ER pre-delay showed a move (49.6 ms on the unit, 0 on ours, old
  calibration). Redo wet-only.
- Run 10b: C115-C119 have the left return 1-10 dB down and C120 dropped out (retaken). The intermittent left output
  fault is back; use the right channel only for those, and the guards need a partial-attenuation check.
- After the 96 kHz switch the MHLink stalled for the rest of the session: rate switching in the runner is unsafe.
- 1.6.7 released (EQ shapes, late-only reverb EQ, ER high-pass, Mid pad, Stereo Chorus 1.06, alg 15 1.07). Replay
  medians: run 6 level 0.84 -> 0.78, tone 0.79 -> 0.76; run 8 1.31 -> 0.81; run 9 1.54 / 1.82 -> 1.14 / 1.01. Run 10:
  493 of 1064 measures within the unit's own spread (1.6.6: 472). Pink-noise tone median 0.78 dB.
- Left to fit (time domain): early echo density (LH1 50-150 ms 0.17 vs the unit's 0.39), build-up timing, LH1 late
  slope and curvature, modulation level wobble (Warm Plate 500 Hz 5.8 vs 0.6 dB), click-to-click correlation (unit
  0.77-0.85, ours ~1.0), cross-feed sign on LH1, and the unit's strong left-to-right asymmetry on wet-only reverbs.
- The dci-core denormals check is a timing test; on the 2-core workspace it failed once (1.84x) under load and passed
  three reruns (0.6-1.3x). Rerun before believing it.

## SSP-550 1.6.8 (2026-11-03): fitted from runs 9-10b without a new run
- The user asked for the remaining differences to be fixed from the existing recordings. Listening results set the
  priority: Large Hall 1 9/10, Warm Plate 9/10, Soft Rotary 8/10 were heard; Wide Chorus 6, Light Flanger 7, Shimmer 6
  were not.
- Run 10's "stereo asymmetry" of the wet-only reverbs was the left cable: the late field's R-L balance of one program
  changed between takes (Large Hall 2 +2.3 dB on take 1, +11.5 to +12.6 on the others; Large Room +1.2 to +18.8). Fits
  use the first stereo impulse (`imp_r1`), whose balance is clean (+0.6 to +2.3 dB) on all eight programs.
- The unit's reverbs are not modulated: its long-tone pitch spread is the decay bandwidth (about 0.5 Hz at every
  frequency) and its level wobble is 0.03-0.6 dB; ours at modulation 0 matches on all six reverbs (`modtest.py`).
- Fit loop (`analysis/run10/fit168/fit.py`): render the eight wet-only slots on one impulse (5 s), score the 5 ms envelope
  0-300 ms (floor -15 dB), the late tone 150-600 ms and band decay; `tune.py` / `grid2.py` search the engine's shape
  controls through environment hooks (`-DSSP_TUNE_SHAPE` builds only). Rotary: `rotan.py` on three music clips (band
  gain, L/R coherence, band-level fluctuation).
- Found and fixed on the way: the new controls and 1.6.7's ER high-pass kept the first sample rate's coefficients
  (caught by SSP550Test's rate check); a random-sign build-up filter passed DC (dci-core `dc` -45 dBFS; now zero-sum).
- SSP550Test's rate check measured only 2 s of a 4-5 s reverb: its low octaves scattered +-1 dB between noise seeds on
  1.6.7 and 1.6.8 alike (`ratechk.py`). Now 8 s rendered, the last 6 s analysed; limit unchanged (worst 0.79 dB).
- Levels: wet loudness moved with the shape changes; compensating from music alone overshot the run-9 hall EQ tests.
  Each algorithm's wet level is set from the replay's signed level of its own tests (runs 6-9).

## Verification pass and SSP-550 1.6.9 (2026-11-03, afternoon)
The user asked that the information behind the model be verified before more listening (`analysis/verify/`).
- **Unit repeatability** (`repeat.py`): the same program and stimulus three days apart agrees to 0.01-0.1 dB in tone
  and 0.1 dB in level on the healthy channel; within a session 0.01 dB. The unit's gain is level-independent
  (-24 / -12 / 0 dBFS sweeps). Nothing below that is worth fitting; everything above it is real.
- **Input 7/8 calibration was anchored to the faulty input 5** (`anchor.py`): the raw right-channel level of every
  program shared by runs 9 and 10b is identical, so input 8 has input 6's gain (R -4.6 dB, L -4.1), not -0.1. The
  "uniform +2-4 dB plug-in excess" of run 10 was this error; the plug-in is in fact 1-2 dB quiet on several
  programs. `lab10.py` and every run-10 script corrected. Run 9's left channel was intermittently attenuated through
  the whole session (R-L median +9 dB against -0.2 in runs 6, 7, 10b): replay scores run 9 on the right channel only.
- **Measure sensitivity** (`sens.py`): injected changes (tail shelf -3 dB, reflections +10 ms, onset +20 ms, decay
  x1.2, modulation on, wet -2 dB) against the unchanged render. The sweep tone missed the 3 dB tail shelf, nothing
  measured level, and T30 at 125/250 Hz with the direct sound present fired on unrelated changes. `lab10.compare` now
  has `late tone` (150-600 ms per octave) and `level` (sweep energy; impulses understate the unit by 2 dB) and drops
  those T30s. NED flags everything (tolerance too tight) and is not informative.
- **EQ re-derived** (`eqfit.py`, `eqstruct*.py`): exact at +-12 dB (400 / 3.9 kHz, Q 0.47, 0.02 dB) but at +-6 the
  corners move (high shelf 2789 / 5344 Hz, low 568 / 284) and the mid Q runs 0.59 -> 0.98 (cuts 3 -> 12 dB) and
  1.20 -> 0.72 (boosts). No fixed structure (symmetric RBJ, feed-forward boost / feed-back cut, additive) fits every
  gain with one corner: a coefficient table per step. 1.6.9 interpolates the measured points on the Stereo Delay path
  (0.0-0.1 dB at every captured setting) - but the same shapes put Ambience and the multi-effects 1.7 dB off against
  runs 7-8, so the EQ differs per path and 1.6.9 applies the new shapes only where measured. Run 11 measures every
  step on the delay path and +-6 on the Ambience and chorus paths.
- **Replay of all 189 earlier targeted tests**: 92 are still off by more than 1.5 dB, concentrated in the Phaser
  (34 of 43) and the Vocoder (14 of 16), then the multi-effect reverbs; none of those were ever in a listening test.
- **Coverage** (`devices/rsp550/COVERAGE.md`): 97 of 675 controls ever varied (14 %); pitch shifters, tap/tempo
  delays and the gated reverbs are factory-only.
- **Listening pairs**: the 1.6.7 and first 1.6.8 pairs had no unit hiss on the plug-in side (the 1.6.6 kit added it);
  republished with it before the user's 1.6.8 round could be confirmed clean. `ab168.py` adds it now.
- **Audibility score** (`audib.py`): the band-level difference in the quiet parts of the loudness-matched pairs
  separated the 1.6.6 results (heard >= 3.3 dB rms, not heard <= 3.2) but predicted Large Hall 1 "not heard" on 1.6.8
  and the user scored 9/10. Six calibration points; not yet a gate on listening.
- **1.6.8 listening**: Large Hall 1 9, Warm Plate 7, Wide Chorus 5, Light Flanger 7, Shimmer 4, Soft Rotary 10 of 10.
- **1.6.9**: reverb wet levels with the corrected calibration (Hall 1 +2.0, Plate 2 +0.6, Plate 1 +0.5, Room 1 -0.3,
  Heaven -0.8), Hall 1 low-frequency decay ratio 1.021 -> 1.08 (wet-only T30 at 125 / 250 Hz 6 % short), the
  gain-dependent EQ on the delay path. Output scales for Wide Chorus, Light Flanger and Shimmer were tried and
  reverted: their direct-only tests in runs 6-7 are right and the effect-only deficit depends on the material (the
  program EQ on those paths, unmeasured). Soft Rotary: the unit is 5 dB louder relative to ours on the quiet clip
  (file3lo) and equal on the loud one - a level dependence in the unit's rotary that run 11's tones at three levels
  will characterise; likely what the user hears at 10/10.
- **Run 11** (`make_run11.py`): the first unattended run. Runner changes (`Run4.h`): plan lines recorded in file
  order (references every 20 lines), a return-sag guard (8 dB balance change for 0.5 s while the stimulus is
  balanced: retake once), a calibration loop capture at the start and end (an interface output patched straight to
  an input: exact latency and gain), no rate switching. Content: EQ steps on the delay path and +-6 on the Ambience
  and chorus paths (batch A), the never-varied controls and the wet-only pre-delay (batch C), the rotary, Large Hall 1
  and Wide Chorus on music and tones at three levels, and the whole bank with labimp + sweepm12 (261 factory lines,
  no user action). About 3.5 hours; the user is needed for 20 minutes at the start and the restore at the end.

## Additional tests (2026-11-03 evening): what they found
Proposed after the verification pass and started at once (the user: "do all that").
- **Reflection tables** (`verify/ertaps.py`, `devices/rsp550/reverb_ir_tables.json`): the unit's halls and Room 1 use
  one five-tap pattern at fixed offsets from the ER pre-delay (0 / 11.0 / 14.8 / 22.2 / 27.3 ms, 0 / -4 / -8 / -11 /
  -8 dB, both / R / L / L / R); Room 1 adds 70 quieter taps; Room 2 and Plate 2 are the same algorithm (identical taps
  and loops); Plate 1 and Mod Reverb share Hall 1's loops. Two reverb cores on the unit. Room 1's late field starts at
  the reverb pre-delay and builds; the others start 47-57 ms after it. The tables are in SSP-550 1.7.0.
- **Clicks and clock** (`verify/clickcorr.py`): the unit's reverbs are strictly deterministic (1.00) and the direct
  impulse arrives at the same sub-sample position over 30 s: no clock drift. Withdrawn: "click-to-click variation"
  and "the sweep's treble bias is clock drift". Run 11's periodic noise will show what the sweep bias is.
- **Null test** (`verify/nulltest.py`): Stereo Delay path -21..-30 dB over 250 Hz-8 kHz; residuals: 0.7 dB level,
  low-frequency phase lead on the unit (12-47 degrees below 400 Hz) with flat magnitude (converter coupling?); the
  unit's delay memory rolls off above 11-12 kHz with a -50 dB floor (ours -108). Reverbs do not null (different
  structure), as expected.
- **Run 11 additions**: in-phase / anti-phase noise on one program per algorithm (input routing), a 1 kHz level
  series and bursts on one program per family (gain curve, attack, release), periodic noise on the 12 battery
  programs (third method). Launcher delivered; calibration loop channels still to be named by the user.
- Owner request logged as dci-effects issue #11: every preset loads with the Mix at 30 % (in 1.7.0; the test app
  keeps the unit's balance for comparisons).

## Service notes (2026-11-04): what Roland's RSP-550 Service Notes (June 1991) settle
The user supplied the 17-page service manual (not committed; the user's copy).
- Two DSP LSIs (TC23SC260AF, IC43/IC44), each with its own 4 x 64k DRAM: the two reverb cores seen in the impulse
  responses (Hall 1 / Hall 3 / Room 1 / Plate 1 / Mod Reverb share loop lengths; Hall 2 / Room 2 / Plate 2 another).
- Everything, the direct sound included, goes through the converters; only the bypass relays (RL1/RL2) are a wire.
  The plug-in leaves its dry path untouched - a difference worth deciding on now that presets load at 30 % mix.
- Pre-emphasis before the A/D (IC15) and de-emphasis after the D/A (IC3): 12k / 1.2 nF = 14.4 us and about 46 us,
  close to the CD standard 50 / 15 us, about +10 dB at the top. Net flat at normal levels, but the A/D should clip
  high frequencies up to ~10 dB before 1 kHz. Run 11 now has a 10 kHz level series (-26 .. -2 dBFS) on three programs
  beside the 1 kHz one.
- Anti-alias: AFL89F modules, 20000D1 up to serial ZC62949, 22000D1 from ZC62950; output LPF F-V25 fc 21 kHz. The
  plug-in's fitted response (-3 dB at 21 kHz, -27 at 22 k) fits the later version; the user's serial number will
  confirm.
- Spec: 15 Hz - 21 kHz +1 / -3 dB "DSP through", so the unit itself rolls off the low end. The low-frequency phase lead
  of the null test is consistent with that, but the interface contributes too: only the calibration loop separates them.
- Test mode (power on holding PROGRAM/PAGE up + PARAM + BYPASS) has a DSP-generated sine test (10 Hz - 21 kHz, -20.5
  dBm) and an A/D-DSP-D/A "through" state: a converter-only measurement, but it needs front-panel steps and a MIDI
  loop cable (its MIDI check stops otherwise). Kept in reserve; the calibration loop plus run 11's effect-only delay
  captures give the same information unattended.
- ROM version: power on holding PROGRAM/PAGE down + VALUE down + PARM + CONTROL.
- 2026-11-04: SSP-550 1.7.1 adds the user's requested option "dry conv" (dry path through the same converter rate,
  bit depth and 48 kHz anti-alias response; off by default, bit-identical to 1.7.0 when off; verified aligned to the
  sample with the converted wet path). Emphasis clipping waits for run 11's 10 kHz level series.
