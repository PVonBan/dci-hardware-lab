# Roland RSP-550: device notes

## MIDI and SysEx

- **Identity:** Roland 0x41, model 0x38, device ID 0 (MIDI ch 1). Port "USB Midi".
- **Messages:** RQ1 0x11, DT1 0x12. Checksum = (128 − sum(address+data) % 128) % 128.

### Address map

| Address | Contents |
|---|---|
| 00 00 00 | System flags (5 bytes) |
| 00 01 00 | MIDI map (256 bytes; replies come back as 00 01 / 00 02) |
| 02 00 00 | Temp/edit buffer (96 bytes); 02 00 60 = sound change request. Ignored in normal mode. |
| 03 nn 00 | Programs 1–128 |
| 04 nn 00 | Programs 129–160 |

### Bulk Load and program changes

- **Bulk Load "Waiting":** stores DT1 to internal memory but answers no RQ1. Memory protect must be off.
- **Copy slots:** programs 101–160 are "*" copies of 1–60. Slots 101–128 are the scratch area for test programs.
- **Program Change:** a PC to the current program is ignored; step away first.

## Program layout (96 bytes)

| Offset | Contents |
|---|---|
| 0–15 | Name |
| 0x11 | Algorithm |
| 0x12–0x13 | Bypass / block on-off bits (alg-specific; e.g. alg 5 modulation = bit 1 of 0x13) |
| 0x14… | Parameters (offsets per algorithm: SSP-550 `Source/RawMap.inc`) |
| 0x45 | Total level |
| 0x46 | External control on/off, bits 0–3 = assigns 1–4 |
| 0x47 + 6k | Assign k: source (Table 40), target (Table nA), min MSB, min LSB, max MSB, max LSB |

- **2-byte fields:** low 7 bits first, e.g. Rev Time 30 = `1e 00`.
- **Ext control:** the min/max values are MSB first.

### Table 40: ext control source

| Code | Source |
|---|---|
| 0 | Control SW (rear jack) |
| 1 | Pitch bend |
| 2 | Channel aftertouch |
| 3 | Note number |
| 4 | Velocity |
| 5–36 | CC 0–31 (CC1 = 6) |
| 37–93 | CC 64–120 |

## Corrections to the manual

- **Simple Delay (alg 3):** echo level is at 20H and direct level at 21H, not the manual's 1FH (Mix) / 20H (Direct). The unit zeroes 1FH when a program loads.
- **Simple Delay routing:** the echo is the mono sum of both inputs. The right input's direct path is about 11 dB down.
- **After Bulk Load:** the unit keeps playing the old sound for about 11 s.

## Measured (runs 1–3)

- **Analog path:** no clipping up to 0 dBFS from the MHLink. THD about −55 dB at 1 kHz. Dry path flat to 16 kHz, −14 dB at 20 kHz.
- **Reverb time:** hardware T30 ≈ 0.4 + 1.1 × displayed seconds (superseded by run 4).

## Measured (run 4)

- **Converters:** flat 20 Hz–20 kHz; −4 dB at 21 kHz, −28 dB at 22 kHz, −62 dB at 23 kHz; 1 kHz THD −81 dB at −20 dBFS.
- **Reverb time (T30 at 1 kHz) against display:**

  | Display | T30 |
  |---|---|
  | 0.2 | 0.47 s |
  | 0.5 | 0.77 s |
  | 1.0 | 1.40 s |
  | 2.0 | 2.68 s |
  | 3.0 | 4.07 s |
  | 5.0 | 6.43 s |
  | 7.0 | 8.02 s |
  | 9.0 | 8.23 s (ceiling ~8.3 s) |

- **Reverb onset:** the late field starts at pre-delay + 54 ms. Hall 2, Room 2 and the plates have no early reflections.
- **Gate:** Thr 30 → −31 dBFS, 50 → −29, 70 → −23; Hold 10 ms/step; Release time constant 4.6 + 3.4 ms/step; Attack ramp about 6 ms/step.
- **Ext control:** all sources scale the target linearly. A repeated controller value is ignored (the unit acts on change).
- **Program change:** the output mutes for about 150 ms.

## Measured (run 5)

- **Delay feedback:** exactly setting/100 per repeat (Simple and Stereo Delay). 100 repeats forever with no loss; 110 and 120 grow until the loop saturates at full scale.
- **Stereo Flanger delay vs Manual:** left 10.75 ms at 0, falling 0.1067 ms per step to about 0.3 ms at 100. Right is 0.65 ms shorter (0.42 ms minimum). The direct sound is on the left output only.
- **Dry converter path:** flat within 0.7 dB 20 Hz-20 kHz; -4 dB at 21 kHz, -27 dB at 22 kHz, -60 dB at 23 kHz. Noise -87 dBFS (-89 A-weighted); THD about -75 dB (H2 dominant); crosstalk -62 dB at 1 kHz, -44 dB at 10 kHz.
- **Program change:** output below -40 dB for 150-170 ms (repeatable).

## Next session (run 10): include the reference-lab additions
See `NOTES.md`, "Additions from the DCI Reverb reference lab (2026-10-20)":
- per reverb program, impulse repeats at 4 starts, the sweep at -24 / -12 / 0 dBFS, 2 s long tones, a 4 Hz click
  train and pre-delay 0 / 50 ms;
- decay shape, weighted echo density and band build-up computed from the existing recordings first;
- the plug-in's `reset()` override before the next build.

Time: about 1 minute of recording per reverb program, plus the analysis without the unit.

