#!/bin/bash
# DCI RSP-550 lab, run 10: the reference-lab battery (impulse x4 + left/right, sweeps at -24/-12/0 dBFS, long tones,
# silence, 4 Hz clicks, pink burst, pre-delay 0/50 ms, the -12 dBFS sweep at 96 kHz) on 12 factory programs, their
# wet-only reverb versions and lowered-level versions, and repeats at the end. Run it after run 9.
# Writes 28 test programs to slots 101-128 once (batch A, one Bulk Load), plays factory programs by program change
# (B, then Z), retakes any clipped capture 10 dB lower, then the follow-up rounds Claude prepares while the runner
# waits, then restores 101-128 from the backup. About 50 minutes plus rounds. The interface switches to 96 kHz for
# three captures and back; if it refuses, those lines are skipped and logged.
set -uo pipefail
LAB="$HOME/Downloads/RSP-550/lab"
WORK="$HOME/Library/Caches/DCI-RSP550-lab"
NH="$HOME/Library/Caches/NocturneHall-build"
LOG="$LAB/run10-log.txt"
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
  [[ -e "$LAB/run9-log.txt" ]] || echo "Note: run 9 has not been run yet (no run9-log.txt). Run 10 works on its own, but run 9 was meant to go first."
  caffeinate -i "$BIN" run4 "$LAB" "$LAB/RSP550-backup-20261018-041833.syx" "$LAB/run10/plan10.txt" "$R4/restore-101-128.syx" "$LAB/run10/tests10A.syx" "$LAB/run5/empty.syx" "$LAB/run5/empty.syx" 3 4 5 6 run10
  echo "exit $?"
} 2>&1 | tee "$LOG"
