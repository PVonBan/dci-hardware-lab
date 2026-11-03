#!/bin/bash
# DCI RSP-550 lab, run 11 (2026-11-03): loop check first, then the battery with the calibration loop.
# Patching: interface outputs 3/4 -> RSP-550 inputs; RSP-550 outputs -> interface inputs 7/8;
# calibration: interface output CAL_OUT patched straight to interface input CAL_IN (set below).
# Your part: answer the >>> prompts (two batch loads in the first 20 minutes, the restore at the end). About 3.5 hours.
# Log: ~/Downloads/RSP-550/lab/run11-log.txt
CAL_OUT=__CAL_OUT__; CAL_IN=__CAL_IN__
set -uo pipefail
LAB="$HOME/Downloads/RSP-550/lab"
WORK="$HOME/Library/Caches/DCI-RSP550-lab"
NH="$HOME/Library/Caches/NocturneHall-build"
LOG="$LAB/run11-log.txt"
mkdir -p "$WORK"
{
  echo "=== $(date)"
  CMAKE="$(command -v cmake || true)"; [[ -x "$CMAKE" ]] || CMAKE="$NH/cmake/CMake.app/Contents/bin/cmake"
  JUCE="$NH/JUCE"; [[ -d "$JUCE" ]] || JUCE="$HOME/Library/Caches/SSP550-build/JUCE"
  [[ -x "$CMAKE" && -d "$JUCE" ]] || { echo "Missing CMake or JUCE (expected in $NH)"; exit 1; }
  BIN="$WORK/build/rsplab_artefacts/Release/rsplab"
  if [[ ! -x "$BIN" || -n "$(find "$LAB/Source" -newer "$BIN" -type f | head -1)" ]]; then
    echo "=== building rsplab"
    "$CMAKE" -S "$LAB" -B "$WORK/build" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DJUCE_PATH="$JUCE" > "$WORK/configure.log" 2>&1 || { tail -20 "$WORK/configure.log"; exit 1; }
    "$CMAKE" --build "$WORK/build" --target rsplab -j "$(sysctl -n hw.ncpu)" > "$WORK/build.log" 2>&1 || { grep -E "error" "$WORK/build.log" | head -20; exit 1; }
  fi
  echo "=== loop check (80 s): during the noise, gently move the cables at both ends"
  "$BIN" loopcheck "$LAB" 3 4 7 8 || { echo "LOOP PROBLEM: fix the cable or jack it names and start this again"; exit 5; }
  echo "=== run 11"
  caffeinate -i "$BIN" run4 "$LAB" "$LAB/RSP550-backup-20261018-041833.syx" "$LAB/run11/plan11.txt" "$LAB/run4/restore-101-128.syx" "$LAB/run11/tests11A.syx" "$LAB/run5/empty.syx" "$LAB/run11/tests11C.syx" 3 4 7 8 run11 "$CAL_OUT" "$CAL_IN"
  echo "exit $?"
} 2>&1 | tee "$LOG"
