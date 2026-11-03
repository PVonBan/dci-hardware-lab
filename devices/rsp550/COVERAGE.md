# RSP-550 hardware coverage per algorithm (runs 1-10b, as of 2026-11-03)

How much of each of the 39 algorithms has been measured on the real unit, from the run indexes
(`lab/capture/run*/run4-index.tsv`, run-1 `index.txt`), the plans/generators here, and the test
SysEx of each run decoded against the unit's bank (so "varied" below is what the stored test program
really changed, not only what its description says). Controls are the plug-in's field table
(`ssp550/Source/RawMap.inc`); the plug-in-only extras at 0x60+ (Vocoder Carrier, Quad PS MIDI Mode,
8 Tap Time/FB Scale, Tempo Delay Sync) are not on the unit and are left out of every count.

Legend
- **FB**: programs in the plug-in factory bank (`FactoryBank.h`, 160 incl. the 60 "*" copies) using the algorithm.
- **Factory captures**: runs with a B row (or run-1 file) of a factory program of that algorithm. Run 1 = every
  unit program 1-128 plus 160 with the standard stimulus (impulses, sweep, 1 kHz tones); 056/067/160 are in the
  capture folder but not in its `index.txt`. Run 1 also has gate sweeps on programs 38 and 40.
- **Varied**: the control was the stated variable of a test program series (A/C/R rows), values listed
  (raw codes unless a unit is given); "1 step" = one deliberate change of that control alone against the captured
  factory program. **Setup** = changed only to isolate something else (depth 0, feedback 0, direct off, EQ flat,
  damping off in reverb-time series) and not counted as varied.
- Run 10b rows repeat run-9 tests whose left return had dropped out, plus the Stereo Delay / reverb EQ round.
  Run 7 R1-R4 are the follow-up rounds recorded in the run-7 capture folder (no index rows; plans
  `run7/round1-4-plan.txt` in the lab working copy, `DCI_LAB_WORK`, not in this repo). Runs 5 and 8 have no index
  file; their rows come from `plan5.txt` / `gen5.py` and `run8/plan8.txt` / `gen8.py` (working copy).
- The run-4 Simple Delay feedback series wrote the manual's addresses (echo level landed at 0); run 5 is the valid series.

## 1. Per algorithm

| Alg | Name (category) | FB | Factory captures | Controls varied in test programs | Never varied (setup-only in brackets) | Varied / total |
|---|---|---|---|---|---|---|
| 1 | Multi Phaser (mod) | 7 | r1 (70,71,72,74); r6 stereo 71,72; r7 noise 71, R1 70,74; r9 noise 74; r10 lab 70; r10b 74 | Mode 0-5 (r8, LFO stopped; r7 1; r7R 0,2,4; r9 4); Rate 1 (r3/r4 static), 14 (r7R); Depth 0 (r3,r4,r8,r9), 89 (r7R); Manual 0/33/66/100 (r4), 10 (r7R), 0/25/50/75/100 x Reso 0/+92 % in mode 4 (r9); Reso 0 % (r4,r7,r9); Step Rate 0 (r7), 50 (r7R); Phase +180 deg (r7R, 1 step); Trem 0 and 59 (r7); Total Lvl 35/76 (r7R), 50 (r9), 31 (r10) | none | 9/9 |
| 2 | Stereo Flanger (mod) | 4 | r1 (54,55,75); r6 stereo+music 54; r7 noise/click 54; r9 54 ref+music; r10 lab 54; r10b 54 | Rate 10/50 (r4), 5 (r6,r7 click), 20 (r7); Depth 0/100 (r4), 0 (r3,r5,r8,r9); Manual 0/25/50/75/100 (r5 static), 0/20/41/60/80/100 (r8 click train), 50 (r4,r6,r7); Reso 0 % (r7, 1 step; setup elsewhere); Phase 0/+90 deg (r6 tone, r7 click) vs factory +180; Mix 0 (r7; r9/r10b Jet Flanging direct only); Dir Mix off (r7; r9/r10b Jet Flanging effect only); Total Lvl 100 (r5), 32 (r10) | Mode (Normal/Bi), Reso Mode [Trem] | 8/11 |
| 3 | Simple Delay (delay) | 1 | r1 (067, unindexed); r6 stereo routing 67 | FB 40/80/100/110/120 (r5; r4 series invalid, see legend); Mix 0/100 (r4,r5), 100 (r3); Dir Lvl 0 (r5 setup; r9/r10b 1 step) | Total Lvl [Dly Time: 100 in FB series vs factory 35] | 3/5 |
| 4 | Vocoder (other) | 3 | r1 (100); r4 note; r6 stereo +/- note; r7 noise lo/hi; r8 steady tones | Mic Mix 0/33/66/100 (r6), 75/85/92 (r7), 96-99 (r7R); Total Lvl 25 (r6,r7), 50 (r7) | Gate Thr, Hiss Mix, Band 200-4.4k (8 bands) | 2/12 |
| 5 | Stereo Delay (delay) | 5 | r1 (58,59,60,93); r6 stereo 93, music 58; r9 music 58; r10 lab 60; r10b 58 | FB 30/60/100 (r5); Mod Wave Tri/Sin (r6); Mod Rate 20/60 (r4); Mod Depth 100/30 (r4; 0 setup r9); EQ Hi -12/-6/+6/+12 (r9), +-6 (r10b); EQ Mid Frq 500/1k/2k/4k (r10b); EQ Mid -12..+12 at 2k, +-12 at 500/1k/4k (r10b); EQ Lo +-12 (r9), +-6 (r10b); Total Lvl 50/75 (r3,r4), 30 (r10) | Cross FB, Damp Lvl, Dly Mix, L/R Polarity, EQ Total [Dly Time 100, Damp Frq off, FB Filter off, Dly Dir Lvl 0] | 9/18 |
| 6 | Multi 3 Flg/Dly/Rev (multi) | 2 | r1 (84,92) | Rev Time 10/40 (r6, reverb only) | 26 others (flanger, delay, EQ, reverb filters/damp, levels) [r9 effect path: Flg Depth 0, Dly Mix 0, Rev Lvl 0, EQ flat] | 1/27 |
| 7 | Multi 1 Cho/Dly/Rev (multi) | 3 | r1 (77,79); r8 click trains 77,79 | Rev Time 10/40 (r6, reverb only) | 26 others [r9 effect path: Cho Depth/Cross Mix/Dir 0, Dly FB/Mix 0, Rev Lvl 0, EQ flat] | 1/27 |
| 8 | Multi 2 PS/Dly/Rev (multi) | 3 | r1 (80,82) | none | all 31 [r9 effect path: PS Dir 0, Dly FB/Mix 0, Rev Lvl 0, EQ flat] | 0/31 |
| 9 | Multi 4 Ph/Cho/Pan/Dly/Rev (multi) | 5 | r1 (76,78,81); r6 stereo 78 | Rev Time 10/40 (r6, reverb only) | 25 others [r9 effect path: Ph/Cho/Pan Depth 0, Cho Dir 0, Dly FB/Mix 0, Rev Lvl 0] | 1/26 |
| 10 | Dynamic Phaser (mod) | 1 | r1 (73); r6 stereo; r7 noise lo/hi | none | all 11: Mode, Sens, Rate Max, Range, Manual, Step Rate, Phase, Trem, Total Lvl [Depth 0, Reso 0 in r9 effect path] | 0/11 |
| 11 | Penta Chorus (mod) | 4 | r1 (51,52); r8 click trains 51,52 | none | all 10 [Cho Depth 0 in r9 effect path] | 0/10 |
| 12 | Space Chorus (mod) | 2 | r1 (45); r6 stereo routing 45 | Dir Mix off (r9/r10b, 1 step) | Space Mode (only mode 3 in the bank), Total Lvl | 1/3 |
| 13 | Stereo Chorus (mod) | 3 | r1 (50); r6 2 kHz tone + music 50; r8 click train; r9 music; r10 lab 50; r10b music | Cho Rate 10/50/100 (r4); Cho Depth 100/30 (r4), 0 (r9); Cho Mix 0/50/100 (r6), 100 (r4); Cho Dir Lvl 100/50/0 (r6), 0 (r9); Total Lvl 15 (r10) | EQ Mid Frq, EQ Total, Cho Mode, Cho LFO Wave, Cho PreDly [EQ Hi/Mid/Lo flat in r9] | 5/13 |
| 14 | 4 Band Chorus (mod) | 6 | r1 (46,48,49); r8 click trains 46,48,49 | none | all 26 [r9 effect path: all four Depths 0, Dir Lvl 0] | 0/26 |
| 15 | Ambience (reverb) | 7 | r1 (35,36,37); r6 stereo 36; r7 noise lo/hi 36,37, stereo 35 | Amb Mix 100/50/0 (r7, r7R); Amb Dir Lvl 0/100/50 (r7, r7R) | EQ (5), Edge Sens, Edge Rel, Edge Mix, Amb PreDly, Amb ER Lvl, Total Lvl | 2/13 |
| 16 | Gate Reverb (reverb) | 3 | r1 (40,41,42; gate sweep on 40) | none | all 15 (Gate Mode, Gate Time, PreDly, Density, Thickness, Accent Delay/Lvl, levels, EQ) | 0/15 |
| 17 | Reverse Gate (reverb) | 4 | r1 (43,44) | none | all 15 | 0/15 |
| 18 | 2 Band Chorus (mod) | 2 | r1 (47); r8 click train 47 | none | all 13 incl. X-Over Freq [r9: Lo/Hi Depth 0, Dir Lvl 0] | 0/13 |
| 19 | Ensemble (mod) | 3 | r1 (89); r9/r10b "effect path" = program 89 unchanged, sweep | none | Ensemble Mode (only mode 3 in the bank), Total Lvl | 0/2 |
| 20 | 2 Band Pitch Shifter (pitch) | 1 | r1 (97); r6 stereo routing 97 | none | all 23 | 0/23 |
| 21 | Stereo Pitch Shifter (pitch) | 2 | r1 (53,96) | PS1 Pitch +12/-12/+1 semis (r4, 440 Hz tone) | 13 others incl. PS Mode, PreDly, FB, Dir Lvl [PS1 Fine 0, PS2 Mix 0 setup] | 1/14 |
| 22 | Quad Pitch Shifter (pitch) | 7 | r1 (94,95,98,99); r6 stereo 94/95/98/99 +/- note, 98 tone; r7 94 note/tone; r7R 94 velocity assign | PS4 Mode HiQuality/HiSpeed (r6, 1 step); PS4 Pitch unison/+5 (r6); PS4 Mix 100/50 (r6) | 24 others: PS1-3 all, PS4 Fine/PreDly/Pan, FB, Total Lvl [PS1-3 Mix 0, PS4 Fine 0, Dir Lvl 0 setup] | 3/27 |
| 23 | Rotary 2 (other) | 4 | r1 (86) | none | all 14 | 0/14 |
| 24 | Hall 1 (reverb) | 14 | r1 (1,3,12,13,15,18,19,27,32,38 + 8 copies; gate sweep 38); r4/r5 pcgap 1; r6 steady tones + music 1; r9 ref + music 1 (+Z); r10 lab 1; r10b music 1 (+Z) | Rev Time 2/5/10/20/30/50/70/90 (r4); Rev PreDly 0/50/150/400 (r4), 0/50 (r10); Damp Frq 1/3/5/7 x Damp Lvl 0/2 (r4; 4 = Thru in RT series); Diffusion 1/6/12 (r4); ER PreDly 0/50 (r10); ER Lvl 0 (r10b, 1 step); EQ Hi -12/-6/+6/+12, EQ Lo +-12, EQ Mid +-12 at 2 kHz (r9, wet-only Baroque Hall; r10b Hi +-12 with ER 0); Gate Thr 30/50/70 (r3/r4; sweep r1); Gate Atk 1/40, Hold 0/60, Rel 1/60 (r4); Dir Lvl 0 (r10); Total Lvl 18 (r10) | EQ Mid Frq, EQ Total, Gate Left, Rev Lvl (varied only by MIDI controller on Hall 2) | 16/20 |
| 25 | Hall 2 (reverb) | 4 | r1 (4,14,17 + copies); r6 steady tones 4; r10 lab 4 | Rev Time 10/30/60 (r4); Rev Lvl swept by CC1, pitch bend, velocity; Total Lvl by aftertouch (r4 ext-control tests); Dir Lvl 0 (r10); Total Lvl 17 (r10) | EQ (5), Rev PreDly, Diffusion [Damp Frq/Lvl off in r4] | 4/13 |
| 26 | Hall 3 (reverb) | 6 | r1 (2,16,22,83 + copies); r10 lab 2 | Rev Time 5/10/20/30/60 (r6); Dir Lvl 0 (r6 on 83; r10 on 2); Total Lvl 16 (r10) | EQ (5), Rev PreDly, Diffusion, ER PreDly, ER Lvl, Rev Lvl [Damp off in r6] | 3/15 |
| 27 | Room 1 (reverb) | 7 | r1 (5,6,23,25,26,29,30 + copies); r6 steady tones 5; r7 repeat 123; r10 lab 5 | Rev Time 3/6/10/20/40 (r6); Rev PreDly 0/10/50 (r10); ER Lvl 0 (r9, 1 step on Church *); Dir Lvl 0 (r6 on 29,30; r10 on 5); Total Lvl 15 (r10) | Gate Thr/Hold/Atk/Rel/Left (gate measured only on Hall 1), EQ Mid Frq, EQ Total, Diffusion, ER PreDly, Rev Lvl [EQ Hi/Mid/Lo set flat together r9; Damp off r6] | 5/20 |
| 28 | Room 2 (reverb) | 4 | r1 (7,24,28,31 + copies); r7 repeat 107; r10 lab 7 | Dir Lvl 0 (r10); Total Lvl 22 (r10) | Rev Time, Rev PreDly, Damp Frq/Lvl, Diffusion, Rev Lvl, EQ (5) | 2/13 |
| 29 | Plate 1 (reverb) | 5 | r1 (9,10,20,39 + copies); r7 repeat 109; r10 lab 9 | Diffusion 80 -> 120 % (r9/r10b, 1 step); Dir Lvl 0 (r10); Total Lvl 15 (r10) | Rev Time, Rev PreDly, Damp Frq/Lvl, Gate (5), Rev Lvl, EQ Mid Frq/Total [EQ Hi/Mid/Lo flat together r9] | 3/18 |
| 30 | Plate 2 (reverb) | 4 | r1 (8,11,21 + copies); r6 steady tones + music 8; r9 music 8; r10 lab 8 (+Z); r10b music | Rev Time 30 (r4; factory 35), 2.0 s vs 5.0 s (r9/r10b Industrial *); Rev PreDly 0 (r9), 0/50 (r10); Damp Lvl -9 dB -> -3 dB (r9/r10b, 1 step on Industrial *; Thru only as setup in r4); Dir Lvl 0 (r10); Total Lvl 17 (r10) | EQ (5), Diffusion, Rev Lvl [Damp Frq off r4] | 5/13 |
| 31 | 8 Tap Delay (delay) | 5 | r1 (61,63,64); r9 ref 61 (+Z); r10b 61 | none | all 39 (8 taps x time/FB/pan/mix, EQ, Dir, Total) [T8 FB 0 in r9 effect path] | 0/39 |
| 32 | 4 Tap Delay (delay) | 5 | r1 (62,65,66) | none | all 28 [r9 effect path: T1/T2 Pan Depth 0, FB 0, FB Position 0, FB Damp 0, Dir 0] | 0/28 |
| 33 | Tempo Delay (delay) | 4 | r1 (056 unindexed, 57) | none | all 18 (Tempo, Interval, FB, damp, filter, Separation, mod, EQ, levels) [Dly FB 0, Dir 0, Mod Depth 0 in r9] | 0/18 |
| 34 | Enhancer (other) | 4 | r1 (68,69) | L+R Freq 10/40 (r4; 90 from the Exciting Female base), L+R Mix Bal 50/100 vs factory 15 (r4); Total Lvl 100 vs 60/70 (r4). L and R always moved together | none separately (L vs R never separated) | 5/5 |
| 35 | Multi 5 Vib/Dly/Rev (multi) | 2 | r1 (85,90) | Rev Time 10/40 (r6, reverb only) | 21 others [r9 effect path: Vib/Panning Depth 0, Dly FB/Mix 0, Rev Lvl 0] | 1/22 |
| 36 | Modulation Reverb (reverb) | 5 | r1 (33,34); r10 lab 33 | Rev Dir Lvl 0 (r10); Total Lvl 7 (r10) | Rev Time, Rev PreDly, LPF/HPF, Damp, Mod Wave/Rate/Depth, Rev Lvl, Cross Mix, EQ (5) | 2/18 |
| 37 | Reverb/Reverb/Delay (multi) | 2 | r1 (160 unindexed) | Rev 1 Time and Rev 2 Time 10/40 together (r6, reverbs only); Total Lvl 100 vs 50 (r3/r4) | 21 others incl. input selects, delay, filters [Rev 1 Mix 0, Rev 2 Lvl 0, Dly FB 0 in r9] | 3/24 |
| 38 | Modulation Delay/Reverb (multi) | 2 | r1 (91) | Rev Time 10 (r6, 1 step, reverb only) | 29 others [Rev Lvl 100/0, Dir Lvl 0, Dly Mod Depth 0, Dly FB 0, Cross Mix 0 setup] | 1/30 |
| 39 | Rotary 1 (other) | 5 | r1 (87,88); r6 music 87; r9 music 87; r10b music 87 | Speed Slow/Fast (r4 tone; switched by CC1 in r4) | Horn/Rotor Fast and Slow, Rise/Fall (4), Mix Bal, OD Drive, OD Lvl, Total Lvl [OD Gain 0 in all r4 rotary tests] | 1/14 |

## 2. Algorithms by coverage

No hardware measurement at all: none (every algorithm has at least one run-1 factory capture; 3, 33 and 37 only
through the unindexed files 067, 056 and 160).

Measured only through factory programs, no control varied (13 algorithms):
8 Multi 2, 10 Dynamic Phaser, 11 Penta Chorus, 14 4 Band Chorus, 16 Gate Reverb, 17 Reverse Gate,
18 2 Band Chorus, 19 Ensemble, 20 2 Band Pitch Shifter, 23 Rotary 2, 31 8 Tap Delay, 32 4 Tap Delay,
33 Tempo Delay. Of these, 8, 10, 11, 14, 18, 19, 31, 32, 33 have a run-9/10b "effect path" isolation capture
(direct off, depth/feedback 0, EQ flat); 16, 17, 20, 23 have only the run-1 standard capture (16 also a run-1
gate sweep; 20 a run-6 stereo routing capture). Nearly factory-only: 28 Room 2 and 36 Modulation Reverb (only
direct level 0 and a lowered Total Level in run 10), 12 Space Chorus (direct off), 38 and 39 (one step each).

Algorithms with a single stored program in the unit's memory 1-100, so the factory data is one setting of every
control: 3, 4, 10, 12, 13, 18, 19, 20, 23, 38 (and 37 only as program 160).

## 3. Counts (controls varied / total, unit fields only)

| Category | Algorithms | Varied / total |
|---|---|---|
| Reverb | 15, 16, 17, 24-30, 36 | 42 / 173 |
| Delay | 3, 5, 31, 32, 33 | 12 / 108 |
| Modulation | 1, 2, 10-14, 18, 19 | 23 / 98 |
| Pitch | 20, 21, 22 | 4 / 64 |
| Multi-effect | 6, 7, 8, 9, 35, 37, 38 | 8 / 187 |
| Dynamics / other (vocoder, rotary, enhancer) | 4, 23, 34, 39 | 8 / 45 |
| **All** | 1-39 | **97 / 675** (14 %) |

Shared blocks measured once and assumed elsewhere: the program EQ (on Hall 1 wet-only and Stereo Delay effect-only),
the gate (Hall 1 only), HF damping and reverb time law (Hall 1; RT also on Hall 2/3, Room 1, Plate 2 and the
multi-effect reverbs at two codes), delay feedback law (Simple and Stereo Delay), Mic Mix (Vocoder).

## 4. Largest gaps

1. The three pitch shifters (20, 21, 22): 4 of 64 controls. Only PS1 Pitch of the Stereo PS and one Quad PS voice
   (mode, +5, mix) were tested; no Fine, Pre-Delay, Feedback or Pan on any voice, nothing on the 2 Band PS.
2. The tap delays and Tempo Delay (31, 32, 33): 0 of 85 controls; per-tap time/pan/mix, FB position, damping and
   the tempo/interval law all rest on three factory programs each.
3. The gated reverbs (16, 17): 0 of 30; Gate Mode, Gate Time, Density, Thickness and Accent were never changed
   (the gate parameters measured in run 4 are the Hall 1 gate, a different block).
4. Rooms and plates: Room 2 and Plate 1 never had Rev Time, pre-delay or damping varied; Plate 2 only one or two
   values. Modulation Reverb (36) has no modulation or reverb control varied.
5. The multi-effects (6-9, 35, 37, 38): only the reverb block's time at 10/40; nothing on their chorus, flanger,
   phaser, pitch or delay blocks beyond the run-9 "effect path" isolation.
6. Rotary (23, 39): only the Slow/Fast switch; no horn/rotor speed, rise/fall or overdrive values.
