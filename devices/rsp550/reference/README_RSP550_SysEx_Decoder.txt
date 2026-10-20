Roland RSP-550 SysEx Decoder & Editor — Enhanced Metadata Edition
===================================================================

Core files
----------
RSP550_SysEx_Decoded_160_Programs.xlsx
    Workbook with the original full 160-program index, 2,905 mapped parameter
    values, all 15,360 payload bytes, algorithm address map and byte matrix.
    Note: the workbook export engine was unavailable during this metadata
    revision, so the workbook is the previous raw-count edition. Use the
    enriched CSVs below for the new ranges, conversion labels and confidence
    notes; those files are current.

rsp550_syx_tool.py
    Python 3.10+ command-line utility. Uses only the Python standard library.
rsp550_syx_parameter_map.json
    Full algorithm-by-algorithm parameter map enriched with documented raw
    ranges, conservative display rules, enums, source pages, URLs and notes.

Enriched CSV exports
--------------------
rsp550_parameter_values.csv
    2,905 actual program/parameter rows. Includes raw count, min/max raw range,
    human-readable interpretation where supported, conversion confidence,
    manual page, Parameter Guide URL and mapping notes.
rsp550_algorithm_parameter_map.csv
    683 algorithm-specific parameter definitions, with raw ranges, display
    rule, a valid sample interpretation, conversion confidence and sources.
rsp550_conversion_notes.csv
    Human-readable explanation of conversion rules and known limitations.
rsp550_program_index.csv
    Program names, algorithms, message and payload offsets.
rsp550_payload_bytes.csv
    Every byte in every 96-byte program payload.
rsp550_decoded_dump.json
    Parsed dump data in JSON.

Verified on the supplied file
-----------------------------
Input: Roland rsp-550_102_104 2.syx
- 16,960 bytes total: 160 messages × 106 bytes each.
- Each message has a 96-byte payload (payload offsets 0x00 through 0x5F).
- All 160 Roland 7-bit checksums validate.
- All 39 algorithm IDs appear in the dump.
- 683 documented algorithm/parameter definitions have raw min/max ranges.
- Editor test: program 102 Reverb Level changed from raw 100 to raw 85.
- Editor test: program 67 two-byte Delay Time changed from raw 35 to raw 200.
- Both test output dumps retained 160 messages with valid checksums and the
  source .syx remained untouched.

Conservative interpretation rules
---------------------------------
- Enumerations are converted to labels only where the Roland Parameter Guide
  describes the choices and ordering, e.g. LFO waveform and rotary slow/fast.
- Delay/predelay values are displayed in milliseconds only where the manual
  explicitly documents milliseconds and the raw range matches that unit.
- Tempo Delay uses the documented BPM scale.
- Reverb Time remains an encoded code from 1–247; the nonlinear code-to-seconds
  curve is not guessed.
- Fine pitch's raw-minus-50 display is marked provisional based on the
  documented -50..+50 span; validate using hardware/software read-back.
- EQ, levels, filters, damping, and other controls show raw counts and
  documented ranges when their physical mapping or selector code table is
  not established. A 0–100 range is not automatically described as percent.
- Two-byte values use the SysEx 7-bit packing rule: LSB + (MSB × 128).

Quick start (macOS / Linux)
---------------------------
Put rsp550_syx_tool.py and rsp550_syx_parameter_map.json in the same folder as
the .syx file. Open Terminal in that folder.

Inspect all programs and check framing/checksums:
    python3 rsp550_syx_tool.py inspect "Roland rsp-550_102_104 2.syx"

Show program 102:
    python3 rsp550_syx_tool.py show "Roland rsp-550_102_104 2.syx" --program 102

Change Reverb Level to raw encoded count 85 and write a new file:
    python3 rsp550_syx_tool.py set-param "Roland rsp-550_102_104 2.syx" "RSP550_modified.syx" --program 102 --parameter "Reverb Level" --value 85

Change a two-byte raw encoded value, e.g. payload offsets 0x21–0x22:
    python3 rsp550_syx_tool.py set-value "Roland rsp-550_102_104 2.syx" "RSP550_modified.syx" --program 102 --offset 0x21 --width 2 --value 200

Rename program 102:
    python3 rsp550_syx_tool.py rename "Roland rsp-550_102_104 2.syx" "RSP550_renamed.syx" --program 102 --name "Big Hall Rev"

Safety
------
- Input framing and checksums are validated before edits.
- The source path is never overwritten: provide a different output filename.
- Named edits match algorithm-specific parameter addresses and enforce known
  raw ranges; --value always means the raw encoded count, not a front-panel
  display value.
- Checksums are recalculated and verified after writing.
- If a parameter is not mapped or its encoding is not confirmed, set-value or
  set-byte can edit a known payload offset directly.
- rename accepts up to 16 ASCII bytes.
- Always test a new dump on a copy and read it back from the hardware before
  batch-editing valuable patches.

Official references
-------------------
Owner's Manual:
https://cdn.roland.com/assets/media/pdf/RSP-550_OM.pdf

Parameter/Algorithm Guide:
https://cdn.roland.com/assets/media/pdf/RSP-550_PA.pdf
