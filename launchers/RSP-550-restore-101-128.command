#!/bin/bash
# DCI RSP-550 lab, restore slots 101-128 from the backup (only needed if run 4 was interrupted).
set -uo pipefail
LAB="$HOME/Downloads/RSP-550/lab"
WORK="$HOME/Library/Caches/DCI-RSP550-lab"
NH="$HOME/Library/Caches/NocturneHall-build"
LOG="$LAB/restore-log.txt"
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
  "$BIN" restore "$R4/restore-101-128.syx"
  echo "exit $?"
} 2>&1 | tee "$LOG"
