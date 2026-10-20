# DCI Hardware Lab

How DCI measures a real hardware unit and fits a plug-in to it. Built and proven on the Roland RSP-550 → SSP-550 project (October 2026). The tool, the analysis code and the lessons are general. The `devices/rsp550` folder is a worked example of the one part that changes per device.

## Results so far

On the SSP-550, the first hardware capture plus one fitting pass improved the plug-in as follows:

| Measure | Before | After |
|---|---|---|
| Median level error | 1.6 dB | 0.6 dB |
| Programs more than 3 dB off | 25 of 160 | 14 of 160 |
| Reverb T30 ratio (plug-in / hardware) | 1.36 | 1.07 |

Run 4 (this package) goes past program-by-program matching. It measures the parameter curves themselves, so a fix applies to every program that uses a parameter, not only the programs that were captured.

Run 4 results, applied in SSP-550 1.5.4 (details in the SSP-550 README and `RSP550-run4-vs-SSP550.csv`):
- reverb time curve and its 8.3 s ceiling, flat high-frequency decay, damping grid, 54 ms late-field onset;
- gate threshold, attack, hold and release;
- chorus, delay-modulation and flanger depth/rate, phaser Manual, pitch-shifter window/splices/intervals;
- rotary Doppler and AM depth, enhancer response, one wrong byte map (Simple Delay).

Whole bank after 1.5.4: 12 programs more than 3 dB off (was 14); reverb decay ratio 1.05, interquartile 0.98–1.09 (was 0.99–1.15).

## Folder map

| Path | What |
|---|---|
| `lab-tool/` | `rsplab`, a JUCE console app: MIDI/SysEx I/O, synchronous play-and-record through an interface, stimulus generators, bulk-write/verify/restore. Build: `cmake -S lab-tool -B build -DJUCE_PATH=… && cmake --build build --target rsplab` |
| `lab-tool/Source/Run4.h` | Kind-based stimulus generator (`makeStim4`) and the batch runner. Start here for a new device. |
| `analysis/an4.py` | One analysis function per stimulus kind. The same code runs on hardware `.wav` captures and on plug-in `.f32` renders. |
| `analysis/render4.cpp`, `plugrender.py` | Render the plug-in engine headlessly on the same stimulus and programs, for a like-for-like comparison. |
| `analysis/cmp4.py` | Side-by-side hardware vs plug-in summary of the run-4 measures. |
| `analysis/rvtune.cpp`, `fitdamp.py`, `onset.cpp`, `rotfit.py` | Fitting harnesses used for 1.5.4: reverb core decay and damping, reverb onset, rotary depth. |
| `analysis/legacy/` | Run 1–3 scripts: per-program 1/3-octave and T30 comparison (`an.py`, `summ.py`), RBJ shelf/LP voicing fits (`fitvoice.py`), reverb-time tuning (`rt.py`, `tune.py`). |
| `analysis/an6.py`, `an6mod.py` | Run-6/7 kinds: stereo routing (one side at a time), steady-tone ripple, LFO shape and left/right phase |
| `analysis/fit_multireverb.py`, `fit_pitchpan.py` | Grid fits used for SSP-550 1.5.9 (multi-effect reverb decay; pitch-shifter pan law and voice gain) |
| `devices/rsp550/gen6.py`, `gen7.py` | Run-6 and run-7 test generators (run 7 adds follow-up rounds: the runner waits while Claude prepares the next tests) |
| `devices/rsp550/` | Device profile: test-program generator (`gen4.py`) and plan (`plan4.txt`). |
| `launchers/` | Double-clickable `.command` files: build-if-needed, run, log to a file. |

## Method

1. **Probe and back up first.**
   - Find the unit on MIDI by sending a harmless read request on each port and device ID.
   - Dump everything to a dated `.syx` before anything else.
   - Every later write is checked against this backup.
2. **Find and calibrate the audio loop.**
   - Send a quiet burst out of each output and see which input returns it.
   - Run a dry-path converter battery (`conv` kind) to get:
     - loop latency (RSP-550 via MHLink: 1179 samples);
     - per-channel loop gain (L +0.9 dB, R −4.6 dB: patchbay/analog, not the unit);
     - the converter's noise, THD and band edge.
   - Remove the latency and gains from every later recording. Don't fit the plug-in to your patchbay.
3. **Capture the factory programs.** Use Program Change and the standard stimulus:
   - impulses L/R;
   - an exponential sweep 20 Hz–20 kHz;
   - 1 kHz steps at five levels;
   - all of it at −10 dB.
4. **Compare like with like.**
   - Render the plug-in on the identical stimulus, through the full output chain (mix stage, total level, program extras).
   - Compare:
     - 1/3-octave spectra of the time-gated wet signal (skip the first 4 ms);
     - level in the 200 Hz–5 kHz band;
     - band T30 (Schroeder, −5 to −25 dB × 3).
5. **Measure parameter curves (run 4).**
   - Write purpose-built test programs into scratch slots, varying one field at a time.
   - Pick a stimulus kind that isolates the property, e.g.:
     - steady tone → instantaneous delay for modulation;
     - burst → feedback decay;
     - stepped controller → control curve.
   - Fit the curve and replace the plug-in's estimate.
6. **Apply fits, then re-verify everything.**
   - Rebuild, re-render all programs and re-run the comparison.
   - Run the stability test (runaway detector below).
   - A fit that helps one program and hurts the median is wrong. Rebalance against full-output level, not wet-only level.

## Stimulus kinds (Run4.h)

| Kind | Stimulus | Measures |
|---|---|---|
| `std` | impulses, ESS, 1 kHz steps (−10 dB) | IR, spectra, T30, onset/pre-delay, echo density, L/R tail correlation, static notches |
| `conv` | silence; 1 kHz −100…−40; THD grid 50 Hz–10 kHz × 5 levels; CCIF 19+20 k; SMPTE 60 + 7 k; sweep to 23.9 kHz; HF tones 18–23.5 k; one-sided tones; independent and mono noise | noise floor (flat and A-weighted), idle tones, low-level linearity and dither, THD/harmonic profile, IMD, anti-alias edge, foldback, crosstalk, decorrelation |
| `tone` | 500 Hz, 10 s | modulation rate and depth (Hilbert phase → delay in ms), AM |
| `tone440` | 440 Hz, click train, chirp | pitch ratio, splice rate, crossfade window |
| `rotsw` | 1 kHz; CC1 switches speed | rotary speeds and rise/fall trajectory |
| `fb` | 50 ms burst, 12 s tail | feedback decay rate; behaviour past unity |
| `gate` / `gsweep` | bursts / level ladder | gate attack, hold and release; threshold |
| `cc` / `pb` / `vel` | noise bursts with stepped CC1+aftertouch / pitch bend / velocity | controller-to-parameter curves |
| `enh` | multitone at 4 levels, 1 kHz at 3 levels, noise | level-dependent EQ and harmonics |
| `pcgap` | tone with program changes | switching mute/crossfade time |
| `note` | std plus a held MIDI note | note-driven algorithms (vocoder, chord) |

Every stimulus is saved next to the captures (`stim-<kind>.wav` and markers). MIDI events are logged with the sample position at which they were actually sent.

## Lessons (each one cost a run)

### Safety with the user's hardware

- **Write stored memory only in scratch/copy slots** (RSP-550: the "*" copies 101–160).
  - Verify the slots match the backup before writing; stop if not.
  - Restore and verify at the end.
  - Ship a standalone restore launcher in case a run is interrupted.
- **Expect the edit buffer to be write-protected in normal mode.** The RSP-550 ignored DT1 to temp. It stores DT1 to internal memory only in Bulk Load "Waiting". In that state it does not answer reads, so verify after leaving Bulk Load.
- **Ask the user to press the front-panel buttons.** Prompt with ">>> … Then press Return here". Never guess the panel state.

### MIDI quirks

- **Filter SysEx replies by address.** Late replies to an earlier request otherwise shift every later read.
- **A Program Change to the current program is ignored.** Step away to another program first, then select.

### Levels and comparison

- **Leave headroom.** Some programs add +4 dB. The first stimulus clipped the interface inputs, so we dropped it by 10 dB.
- **Render through the plug-in's whole chain.** A bare effect render produced two false findings ("8-tap delay 10× short", "BarberPole silent"). The cause was the missing mix stage and makeProgram extras.
- **Wet-only level fits overcorrect.** Fit voicing gain against full-output level.

### Run 4 lessons
- **Let the unit settle after Bulk Load.** It kept playing the previous sound for about 11 s although the edit buffer already showed the new program. The runner now steps to program 1 and waits 15 s.
- **The manual's address tables can be wrong.** Simple Delay keeps its echo level at 20H and direct level at 21H, not 1FH/20H. Two checks catch this:
  - Compare what you wrote with the edit buffer after selecting the program; the unit silently zeroes bytes it doesn't accept. The runner now reports any difference.
  - Check that every test actually changes the audio.
- **Don't take loop gain from a program.** Use the impulse peaks of a known-dry program, or the run-1 direct calibration. Cross-correlating a stimulus made of steady tones locks onto the wrong lag, and a "dry" program can carry its own gain.
- **Multi-voice effects defeat phase tracking.** Two chorus voices beat, so the Hilbert-phase delay estimate is meaningless. Read rate and depth from a long, high-resolution spectrum instead:
  - Doppler-shifted lines at ±(2 × depth × rate × f0) give the depth;
  - their spacing gives the LFO rate.
- **Remove the direct path before timing a gate.** Estimate the direct gain from the first 20 ms (before any reverb) and subtract it.
- **Mind boost tests.** The enhancer adds up to +20 dB and clipped the noise and loud steps. Keep such tests at −20 dBFS or below, and fit from the clean multitone levels.
- **Fit inner blocks with a harness.** `rvtune.cpp` drives the reverb core directly and `fitdamp.py` fits it in minutes. Then confirm with full renders and the whole-bank comparison, because a parameter fix can still shift levels that were fitted earlier.

### Validation

- **Check modulation tests switch the block on.** Several fields only act when their block bit is set: alg 5 modulation needs bit 1 of 0x13. Render the plug-in on the test program first; a flat result means the test is wrong.
- **Run the analysis on plug-in renders before the hardware run.** It validates the scripts and shows which parameters the plug-in ignores. Before run 4 that showed:
  - gate attack ignored;
  - feedback clamped at 97 %;
  - delay modulation off unless the block bit was set;
  - no level dependence in the enhancer.
- **Use a runaway detector for stability tests, not a peak limit.** Hot but stable reverbs and delays tripped the old peak check. Flag a recording only if the last 1.5 s is louder than twice the preceding peak, or there is NaN or silence.

### Working with the user's Mac

- The user runs `.command` files by double-clicking; Claude can't type in Terminal.
- Stage every file under a unique name and verify md5 on the Mac. Re-using a staged path once delivered stale content.

## Checks after every build (no hardware)
See NOTES.md "Protocol from run 9". In short: plug-in integrity test, render parity, replay of all earlier runs,
bank check, and the guards in analysis/guards.py for every comparison. Validate every planned test on plug-in renders
(analysis/validate_tests.py) before a session.
The last step of every hardware-model build is the blind listening test (analysis/abx/make_abx.py; NOTES.md).

## Porting to a new device

1. Copy `lab-tool`. Change the MIDI identity and address map: `rq1`/`dt1`, model ID, slot addresses, checksum.
2. Write `devices/<name>/gen.py`. It reads the backup, builds test programs with one field changed each, writes `tests*.syx`, `restore*.syx` and the plan.
3. Keep stimulus kinds and `an4.py` as they are. Add a kind only for a new kind of behaviour.
4. Render the plug-in on the plan, analyse it, and fix the tests until every one shows something.
5. Run on hardware. Diff `hw.json` against `plug.json`, fit, apply, and re-verify.

## Guitar amps and pedals (dci-amps)

The same loop applies to reamping: interface out → reamp box → amp → load box/DI → interface in. Device swaps:

- **The `conv` kind becomes the reamp-chain calibration.** Run it with the amp bypassed and remove the chain from every capture.
- **Program changes become knob positions.** The user turns a knob when prompted, the same way as the Bulk Load prompts.
- **Most useful kinds for amps:**
  - THD grid and 1 kHz ladder at more levels: the H2/H3/H4 balance vs drive;
  - `gate`-style bursts: sag and recovery (attack and release of the supply);
  - multitone/`enh`: intermodulation;
  - `std` sweep per knob position: tone-stack curves and pot tapers;
  - `conv` silence: hum and noise spectrum;
  - HF tones: aliasing checks of the plug-in vs the real amp.
- **Not needed for amps:** MIDI controller curves, program-change gap, modulation tracking (except amp tremolo/vibrato, where `tone` applies directly).
