#!/bin/bash
# DCI RSP-550 lab, run 5: follow-ups from run 4 (about 8 minutes, one Bulk Load for the tests and one to restore).
# Simple Delay feedback and dry reference with the corrected byte map, Stereo Delay feedback, flanger Manual.
# Writes slots 101-114, records them, restores 101-128 and verifies. Keep monitors low (feedback past unity).
set -uo pipefail
LAB="$HOME/Downloads/RSP-550/lab"
WORK="$HOME/Library/Caches/DCI-RSP550-lab"
NH="$HOME/Library/Caches/NocturneHall-build"
LOG="$LAB/run5-log.txt"
mkdir -p "$WORK"
{
  echo "=== $(date)"
  CMAKE="$(command -v cmake || true)"; [[ -x "$CMAKE" ]] || CMAKE="$NH/cmake/CMake.app/Contents/bin/cmake"
  JUCE="$NH/JUCE"; [[ -d "$JUCE" ]] || JUCE="$HOME/Library/Caches/SSP550-build/JUCE"
  [[ -x "$CMAKE" && -d "$JUCE" ]] || { echo "Missing CMake or JUCE (expected in $NH)"; exit 1; }
  BIN="$WORK/build/rsplab_artefacts/Release/rsplab"
  if [[ ! -x "$BIN" || "$LAB/Source/Main.cpp" -nt "$BIN" || "$LAB/Source/Capture.h" -nt "$BIN" || "$LAB/Source/Run4.h" -nt "$BIN" ]]; then
    echo "=== building rsplab"
    "$CMAKE" -S "$LAB" -B "$WORK/build" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DJUCE_PATH="$JUCE" > "$WORK/configure.log" 2>&1 || { tail -20 "$WORK/configure.log"; exit 1; }
    "$CMAKE" --build "$WORK/build" --target rsplab -j "$(sysctl -n hw.ncpu)" > "$WORK/build.log" 2>&1 || { grep -E "error" "$WORK/build.log" | head -20; exit 1; }
  fi
  R4="$LAB/run4"
  caffeinate -i "$BIN" run4 "$LAB" "$LAB/RSP550-backup-20261018-041833.syx" "$LAB/run5/plan5.txt" "$R4/restore-101-128.syx" "$LAB/run5/tests5A.syx" "$LAB/run5/empty.syx" "$LAB/run5/empty.syx" 3 4 5 6 run5
  echo "exit $?"
} 2>&1 | tee "$LOG"
