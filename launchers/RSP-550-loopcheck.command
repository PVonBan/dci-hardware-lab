#!/bin/bash
# DCI RSP-550 lab: audio loop check (no MIDI, nothing written to the unit). About 80 s plus a build the first time.
# Plays tones and noise on interface outputs 3/4 and records inputs 5/6 through the RSP-550 as it is set now (leave it on
# a normal stereo program, e.g. 3 Medium Hall 1). During the last 60 s, gently move the cables at both ends.
# Log: ~/Downloads/RSP-550/lab/loopcheck-log.txt
set -uo pipefail
LAB="$HOME/Downloads/RSP-550/lab"
WORK="$HOME/Library/Caches/DCI-RSP550-lab"
NH="$HOME/Library/Caches/NocturneHall-build"
LOG="$LAB/loopcheck-log.txt"
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
  "$BIN" loopcheck "$LAB" 3 4 5 6
  echo "exit $?"
} 2>&1 | tee "$LOG"
