
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
