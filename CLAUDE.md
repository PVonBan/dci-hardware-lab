# dci-hardware-lab — read this first

The DCI Hardware Lab: tools for measuring real hardware (effects units, amps, pedals) over MIDI and an
audio interface, and comparing it with DCI plug-ins. Moved here from the user's Mac folder
`~/Downloads/DCI-HardwareLab` on 2026-10-20; that folder is still the working copy the launchers run from.

- Read `README.md` and `NOTES.md` first, and follow the `dci-hardware-capture` skill.
- `lab-tool/` rsplab (JUCE console app), `analysis/` analysis, fitting and run-9 protocol tools
  (`abx/` makes the blind listening pages), `devices/<unit>/` per-unit generators, plans and field tables,
  `launchers/` the `.command` files the user double-clicks.
- Recordings (`.wav`, `.f32`) stay on the Mac and are never committed.
- Keep the Mac folder and this repo in step: after changing files there, commit them here; verify with md5.
- Append each run's lessons to `NOTES.md` and commit.
- Commit after each verified step, with the session attribution lines.
