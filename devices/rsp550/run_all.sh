#!/bin/bash
# RSP-550 / SSP-550: every test, every build (TESTS.md). Linux, -j2. Exit 0 only when every gating test passes.
#   devices/rsp550/run_all.sh [--quick]
# Paths (override with environment variables):
#   SSP550_DIR    the plug-in project (dci-effects imported/SSP550, or the working copy)   default /home/claude/ssp550
#   DCI_LAB_WORK  folder with runs 6-8 (plans, test banks) for replay                     default: replay.py's own
#   RUN10_DIR     make_run10.py output (stimuli, plan, test bank)                           default $WORK/run10
#   RUN10_CAP     the unit's run-10 captures (capture/run10), when they exist               default: none
#   RSPLAB        the lab tool binary (writes the run-4 stimuli for the render4 parity target)
#   BACKUP        the unit's bank backup .syx (renders use it in slot order, test programs overlaid in their slots)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; LAB="$(cd "$HERE/../.." && pwd)"; AN="$LAB/analysis"
SSP="${SSP550_DIR:-/home/claude/ssp550}"
WORK="${WORK:-$(mktemp -d)}"; mkdir -p "$WORK"
RL="${REVERBLAB:-/home/claude/dci-effects/tools/reverblab}"
BACKUP="${BACKUP:-/mnt/user-data/uploads/Downloads/RSP-550/lab/RSP550-backup-20261018-041833.syx}"
QUICK=0; [[ "${1:-}" == "--quick" ]] && QUICK=1
fail=0; gate() { if [[ $1 -eq 0 ]]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=1; fi; }

echo "== build (SSP550Test, SSP550Checks, render4)"
cmake -S "$SSP" -B "$SSP/build" -DSSP_BUILD_TESTS=ON > "$WORK/cfg.log" 2>&1 && cmake --build "$SSP/build" -j2 --target SSP550Test SSP550Checks > "$WORK/build.log" 2>&1
gate $? "build"
T="$SSP/build/SSP550Test_artefacts/Release/SSP550Test"; C="$SSP/build/SSP550Checks_artefacts/Release/SSP550Checks"
g++ -O2 -std=c++17 -I"$SSP/Source" "$AN/render4.cpp" "$SSP/Source/AlgorithmTable.cpp" "$SSP/Source/Effects.cpp" "$SSP/Source/Programs.cpp" -o "$WORK/render4"
gate $? "build render4 (analysis renderer) from the same sources"

echo "== plug-in"
( cd "$WORK" && "$T" > "$WORK/test.log" 2>&1 ); tail -1 "$WORK/test.log" | grep -q "ALL CHECKS PASSED"
gate $? "SSP550Test: programs at 3 rates, state, UI pages, integrity (extremes, blocks, rates, determinism, reset, state reload, jumps, MIDI)"
"$T" --hostreset > "$WORK/hostreset.log" 2>&1; awk '/^worst:/ { exit !($(NF-1)+0 <= -100) }' "$WORK/hostreset.log"
gate $? "hostreset on all 199 programs: after reset() the output equals a fresh instance's (< -100 dB)"
"$C" > "$WORK/checks.log" 2>&1; tail -1 "$WORK/checks.log" | grep -q "CHECKS OK"
gate $? "dci-core plug-in checks (blocks, latency, denormals, badinput, state, dc, startup, tail, extremes, rates, jumps, reset, hostreset, determinism, midi)"

echo "== run 10 battery on ours"
R10="${RUN10_DIR:-$WORK/run10}"
if [[ ! -f "$R10/plan10.txt" ]]; then python3 "$HERE/make_run10.py" "$RL" "$BACKUP" "$HERE/fields.tsv" "$R10" > /dev/null; fi
rm -rf "$WORK/ours10" "$WORK/sim10"
python3 "$AN/lab10.py" ours "$T" "$R10" "$WORK/ours10" "$BACKUP" && python3 "$AN/lab10.py" validate "$R10" "$WORK/ours10" "$BACKUP" > "$WORK/validate10.log" 2>&1
gate $? "run 10 validate: test programs change one field each, every render finite and not silent"
# self-test: our renders sent through the loop model (latency, gain, -87 dBFS noise) as if they were the unit must
# come back as matching: proves slicing, calibration and every measure before real captures are trusted
python3 "$AN/lab10.py" simulate "$WORK/ours10" "$R10" "$WORK/simcap" > /dev/null && python3 "$AN/lab10.py" hw "$WORK/simcap" "$R10" "$WORK/sim10" \
  && python3 "$AN/lab10.py" measure "$WORK/sim10" "$RL" > /dev/null 2>&1 && cp -r "$WORK/ours10" "$WORK/ours10n" \
  && python3 "$AN/lab10.py" addnoise "$WORK/ours10n" "$WORK/sim10" && python3 "$AN/lab10.py" measure "$WORK/ours10n" "$RL" > /dev/null 2>&1 \
  && python3 "$AN/lab10.py" compare "$WORK/sim10" "$WORK/ours10n" --json "$WORK/selftest10.json" > "$WORK/selftest10.log" \
  && python3 -c "
import json,sys; r=json.load(open('$WORK/selftest10.json')); n=sum(len(v) for k,v in r.items() if not k.startswith('_')); ok=sum(x['ok'] for k,v in r.items() if not k.startswith('_') for x in v.values())
print('   self-test: %d of %d measures match' % (ok, n)); sys.exit(0 if ok >= 0.97 * n else 1)"
gate $? "run 10 analysis self-test (ours through the loop model reads as ours, >= 97 % of measures)"

if [[ $QUICK -eq 0 ]]; then
  echo "== targets (reported, not gating)"
  ( DCI_LAB_WORK="${DCI_LAB_WORK:-}" python3 "$AN/replay.py" "$T" current 2>&1 | tail -4 ) || echo "   replay: not available here (needs runs 6-8)"
  # render4 (the fast engine-only renderer some fits use) against the plug-in: since 1.6.4 it lacks the processor's
  # per-algorithm wet filters and scaling, so fits made with it must be checked on the plug-in (replay does that)
  "${RSPLAB:-$LAB/lab-tool/build/rsplab_artefacts/Release/rsplab}" stims "$WORK/stims" > /dev/null 2>&1 || true
  if [[ -f "$WORK/stims/stim-std.wav" ]]; then
    python3 -c "import soundfile as sf; x,_=sf.read('$WORK/stims/stim-std.wav',dtype='float32'); x.astype('<f4').tofile('$WORK/std.f32')"
    mkdir -p "$WORK/parp" "$WORK/para"; "$T" --render "$WORK/parp" "$WORK/std.f32" "$BACKUP" 1 8 33 50 54 60 70 83 > /dev/null
    for n in 1 8 33 50 54 60 70 83; do "$WORK/render4" "$BACKUP" "$WORK/std.f32" "$WORK/para" $n > /dev/null; done
    python3 "$AN/parity.py" "$WORK/parp" "$WORK/para" "$WORK/std.f32" | tail -1 | sed 's/^/   render4 parity: /'
  fi
  if [[ -n "${RUN10_CAP:-}" && -d "$RUN10_CAP" ]]; then
    python3 "$AN/lab10.py" hw "$RUN10_CAP" "$R10" "$WORK/hw10" && python3 "$AN/lab10.py" measure "$WORK/hw10" "$RL" > /dev/null 2>&1 \
      && python3 "$AN/lab10.py" addnoise "$WORK/ours10" "$WORK/hw10" && python3 "$AN/lab10.py" measure "$WORK/ours10" "$RL" > /dev/null 2>&1 \
      && python3 "$AN/lab10.py" compare "$WORK/hw10" "$WORK/ours10" --json "$WORK/run10-vs-unit.json"
  else echo "   run 10 against the unit: no captures yet (RUN10_CAP)"; fi
  echo "   listening: read the saved ABX results on the unit's listening page before the next build"
fi
echo "logs in $WORK"
[[ $fail -eq 0 ]] && echo "ALL GATING TESTS PASS" || echo "GATING FAILURES"
exit $fail
