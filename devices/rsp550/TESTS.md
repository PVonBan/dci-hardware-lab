# RSP-550 / SSP-550: the test list

Everything below runs every build, with one command (Linux, `-j2`):

```
devices/rsp550/run_all.sh            # gating tests, then the targets
devices/rsp550/run_all.sh --quick    # gating tests only
```

Paths are environment variables (see the script head): `SSP550_DIR` (the plug-in project, dci-effects
`imported/SSP550` or the working copy), `DCI_LAB_WORK` (runs 6-8 for replay), `RUN10_DIR`, `RUN10_CAP` (the unit's
run-10 captures, once they exist). Add a new test here and in `run_all.sh` in the same commit; nothing is tested "once".

## Gating: must pass

| Test | Program | What it proves |
|---|---|---|
| build | cmake `-j2`; g++ | SSP550Test, SSP550Checks (dci-core `tests/plugin_checks.cpp`) and render4 build from the same sources |
| plug-in suite | `SSP550Test` -> ALL CHECKS PASSED | all 199 programs at 48 / 96 / 44.1 kHz, state, UI pages, integrity (field extremes, block size, rate, determinism, reset, state reload, parameter jumps, MIDI abuse) |
| hostreset, every program | `SSP550Test --hostreset` | after `reset()` alone (what an AU host calls on stop, locate, offline bounce) each of the 199 programs renders exactly as a fresh instance (< -100 dB; 1.6.6: -300 dB) |
| dci-core checks | `SSP550Checks` -> CHECKS OK | blocks, latency (dry), denormals, badinput, state, dc, startup, tail, extremes, rates, jumps, reset, hostreset, determinism, midi |
| run-10 validate | `lab10.py validate` | the 28 test programs differ from their source only in the field they test; every battery render is finite and not silent; captures expected to clip are listed (the runner retakes them 10 dB lower) |
| run-10 self-test | `lab10.py simulate / hw / addnoise / measure / compare` | our renders put through the loop model (latency 1179, loop gain, -87 dBFS noise) and analysed as if they were the unit come back matching ours on >= 97 % of measures: slicing, calibration and every measure work before real captures are trusted |

Also before a build is delivered (dci-hardware-capture protocol): render parity (`parity.py`), analysis guards
(`guards.py`), and on the Mac auval on the installed AU.

## Targets: reported every run

| Target | Program | Notes |
|---|---|---|
| replay of runs 6-8 | `replay.py <SSP550Test> <tag>` -> `scores-<tag>.json`, `replay_diff.py` | per-test level and tone error of the real plug-in against every earlier recording; compare with the previous build (moves > 0.3 dB listed; baseline `scores-plug166.json` here) |
| render4 parity | `parity.py` | the fast engine-only renderer against the plug-in (fails since 1.6.4: no processor wet filters; check fits made with it on the plug-in) |
| run 10 against the unit | `lab10.py compare` (with `RUN10_CAP`) | the same battery on both sides, ours with the unit's own idle noise added; tolerance from the unit's own spread over its 4 impulses where that exists |
| listening | the unit's ABX page | read the saved results before the next build (8 of 10 or more = a real difference; "can't tell" counts as not right) |

## The run-10 battery (dci-reference-lab, adapted to a hardware unit)

Made by `make_run10.py` (stimuli are the reverb lab's own, `dci-effects tools/reverblab/make_run3.py`, so
`analyse_run3.py` measures the unit and ours with the same code). The runner plays them as kind `wav:<name>`.

| Stimulus | On | Measures |
|---|---|---|
| `labimp`: impulse x4 after 7.00 / 7.37 / 7.81 / 8.23 s, left-only, right-only | 12 factory programs (B), 8 wet-only reverbs (A), repeats of 1 and 8 at the end (Z) | variance per measure (fit tolerance); NED, energy-weighted echo density, band build-up, early/late, decay shape (EDT / T20 / late slope / curvature); cross-feed, mono loss; drift over the session |
| `sweepm12`: -12 dBFS exponential sweep | B, wet-only A, level A | octave T30, 1/3-octave tone |
| `sweepm24`, `sweep0` | 12 lowered-level programs (A) | level dependence (T30, tone) and distortion; Total Level lowered so the 0 dBFS sweep does not clip the interface |
| `labmisc`: 10 s silence, 2 s long tones 250 Hz-4 kHz, 4 Hz clicks, 2 s pink burst | B | noise; real modulation (spread in cents, rate, level wobble); click-to-click similarity from the unit's onset; steady tone |
| `imp1` with pre-delay 0 / 50 ms | Large Hall 1 (reverb and ER pre-delay), Warm Plate, Large Room (A) | what the pre-delay control moves (whole response or part) |
| `sweepm12_96`: the -12 dBFS sweep at 96 kHz | 1, 8, 50 (B) | T30 and tone at 96 kHz against 48 kHz |
| `std` | 1, 54 (Z) | the same capture as runs 6-9: the chain has not changed |

## History

- 2026-10-20 (SSP-550 1.6.6): the dci-core checks were run on the SSP-550 for the first time and found: no `reset()`
  override (tails and LFO phases survived a host stop), reverb LFO phases and line-length smoothing not reset, the
  vocoder's noise and saw state not reset, Auto Gain depending on the host's buffer size (-32 dB difference at 2048),
  NaN or infinity input sticking forever, DC passing (-22.6 dBFS driven asymmetrically), the legacy 'vintage'
  switch overriding a saved Bit Depth on reload. All fixed; replay of runs 6-8 with the plug-in unchanged (no measure
  moved > 0.3 dB).
- 2026-10-20: replay had been rendering with `render4`, which lacks the processor's wet filters since 1.6.4, and the
  plug-in's bank loader ignores SysEx addresses (a test bank alone lands in programs 1-28). Replay and run 10 now render
  the plug-in with the unit's bank in slot order and test programs overlaid in their slots.
- 2026-10-20: `replay/scores-v164.json` had been made before 1.6.4's last changes; 1.6.4 as published scores the same
  as 1.6.5 and 1.6.6 (`scores-v164check.json`). The large moves it showed (Hall3 direct off -12 dB, Wide Chorus and
  flanger click trains +3 dB) are 1.6.4's own changes, not regressions of later builds.
