
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
