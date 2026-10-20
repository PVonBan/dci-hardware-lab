#!/usr/bin/env python3
"""
Roland RSP-550 SysEx utility.

The source file is a concatenation of 106-byte DT1 messages, each carrying
96 data bytes. Edits are made in memory and written to a distinct output
file with each affected message's Roland 7-bit checksum recalculated.

Examples:
  python rsp550_syx_tool.py inspect "Roland rsp-550_102_104 2.syx"
  python rsp550_syx_tool.py show "Roland rsp-550_102_104 2.syx" --program 102
  python rsp550_syx_tool.py set-byte input.syx output.syx --program 102 --offset 0x2B --value 90
  python rsp550_syx_tool.py set-value input.syx output.syx --program 102 --offset 0x21 --width 2 --value 200
  python rsp550_syx_tool.py set-param input.syx output.syx --program 102 --parameter "Reverb Level" --value 85
  python rsp550_syx_tool.py rename input.syx output.syx --program 102 --name "Big Hall Rev"

Named parameter views include the manual's valid count ranges and conservative readable interpretations.
The tool translates only documented enumerations, tempo in BPM, and time values where the raw range
matches the stated millisecond range. It intentionally does not infer nonlinear reverb-time, EQ, filter,
damping, pitch-shift, or undocumented mode tables. `set-param --value` always accepts a RAW encoded count,
checks it against a documented range when available, and writes to a new output file.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

MESSAGE_SIZE = 106
PAYLOAD_START = 8
PAYLOAD_SIZE = 96
CHECKSUM_INDEX = 104
EOX_INDEX = 105
ALGORITHM_NAMES = {int(k): v for k, v in json.loads('{"1":"Multi Phaser","2":"Stereo Flanger","3":"Simple Delay","4":"Vocoder","5":"Stereo Delay","6":"Multi 3","7":"Multi 1","8":"Multi 2","9":"Multi 4","10":"Dynamic Phaser","11":"Penta Chorus","12":"Space Chorus","13":"Stereo Chorus","14":"4 Band Chorus","15":"Ambience","16":"Gate Reverb","17":"Reverse Gate","18":"2 Band Chorus","19":"Ensemble","20":"2 Band Pitch Shifter","21":"Stereo Pitch Shifter","22":"Quad Pitch Shifter","23":"Rotary 2","24":"Hall 1","25":"Hall 2","26":"Hall 3","27":"Room 1","28":"Room 2","29":"Plate 1","30":"Plate 2","31":"8 Tap Delay","32":"4 Tap Delay","33":"Tempo Delay","34":"Enhancer","35":"Multi 5","36":"Modulation Reverb","37":"Reverb/Reverb/Delay","38":"Modulation Delay/Reverb","39":"Rotary 1"}').items()}
PARAMS = {int(k): v for k, v in json.loads('{"1":[{"offset":20,"name":"Phasing Mode","width":1,"note":""},{"offset":25,"name":"Phasing Rate","width":1,"note":""},{"offset":26,"name":"Phasing Depth","width":1,"note":""},{"offset":27,"name":"Manual","width":1,"note":""},{"offset":28,"name":"Resonance","width":1,"note":""},{"offset":29,"name":"Step Rate","width":1,"note":""},{"offset":30,"name":"Modulation Phase","width":1,"note":""},{"offset":31,"name":"Tremolo Depth","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"2":[{"offset":20,"name":"Flange Mode","width":1,"note":""},{"offset":22,"name":"Flange Rate","width":1,"note":""},{"offset":23,"name":"Flange Depth","width":1,"note":""},{"offset":24,"name":"Flange Manual","width":1,"note":""},{"offset":25,"name":"Resonance Mode","width":1,"note":""},{"offset":26,"name":"Resonance","width":1,"note":""},{"offset":27,"name":"Modulation Phase","width":1,"note":""},{"offset":28,"name":"Mix Level","width":1,"note":""},{"offset":29,"name":"Tremolo Depth","width":1,"note":""},{"offset":30,"name":"Direct Mix","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"3":[{"offset":20,"name":"Delay Time","width":2,"note":""},{"offset":26,"name":"Feedback","width":1,"note":""},{"offset":31,"name":"Mix Level","width":1,"note":""},{"offset":32,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"4":[{"offset":20,"name":"Gate Threshold","width":1,"note":""},{"offset":21,"name":"Mic Mix Level","width":1,"note":""},{"offset":22,"name":"Hiss Mix Level","width":1,"note":""},{"offset":23,"name":"Voice Character (200 Hz)","width":1,"note":""},{"offset":24,"name":"Voice Character (320 Hz)","width":1,"note":""},{"offset":25,"name":"Voice Character (500 Hz)","width":1,"note":""},{"offset":26,"name":"Voice Character (800 Hz)","width":1,"note":""},{"offset":27,"name":"Voice Character (1 kHz)","width":1,"note":""},{"offset":28,"name":"Voice Character (1.8 kHz)","width":1,"note":""},{"offset":29,"name":"Voice Character (2.7 kHz)","width":1,"note":""},{"offset":30,"name":"Voice Character (4.4 kHz)","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"5":[{"offset":24,"name":"Delay Time","width":2,"note":""},{"offset":26,"name":"Feedback","width":1,"note":""},{"offset":27,"name":"Cross Feedback","width":1,"note":""},{"offset":28,"name":"HF Damp Frequency","width":1,"note":""},{"offset":29,"name":"HF Damp Level","width":1,"note":""},{"offset":30,"name":"Feedback Filter","width":1,"note":""},{"offset":31,"name":"Delay Mix Level","width":1,"note":""},{"offset":32,"name":"Delay Direct Level","width":1,"note":""},{"offset":33,"name":"Modulation LFO Waveform","width":1,"note":""},{"offset":34,"name":"Modulation Rate","width":1,"note":""},{"offset":35,"name":"Modulation Depth","width":1,"note":""},{"offset":36,"name":"L/R Polarity","width":1,"note":""},{"offset":37,"name":"EQ High Level","width":1,"note":""},{"offset":38,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":39,"name":"EQ Mid Level","width":1,"note":""},{"offset":40,"name":"EQ Low Level","width":1,"note":""},{"offset":41,"name":"EQ Total Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"6":[{"offset":24,"name":"EQ High Level","width":1,"note":""},{"offset":25,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":26,"name":"EQ Mid Level","width":1,"note":""},{"offset":27,"name":"EQ Low Level","width":1,"note":""},{"offset":28,"name":"EQ Total Level","width":1,"note":""},{"offset":29,"name":"Flanger Rate","width":1,"note":""},{"offset":30,"name":"Flanger Depth","width":1,"note":""},{"offset":31,"name":"Flanger Manual","width":1,"note":""},{"offset":32,"name":"Flanger Resonance","width":1,"note":""},{"offset":33,"name":"Flanger Modulation Phase","width":1,"note":""},{"offset":34,"name":"Flanger Mix Level","width":1,"note":""},{"offset":35,"name":"Flanger Tremolo Depth","width":1,"note":""},{"offset":48,"name":"Delay Time","width":2,"note":""},{"offset":50,"name":"Delay Feedback","width":1,"note":""},{"offset":51,"name":"Delay HF Damp Frequency","width":1,"note":""},{"offset":52,"name":"Delay HF Damp Level","width":1,"note":""},{"offset":53,"name":"Delay Mix Level","width":1,"note":""},{"offset":54,"name":"Delay Direct Level","width":1,"note":""},{"offset":55,"name":"Reverb Time","width":2,"note":""},{"offset":57,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":59,"name":"Reverb Filter LPF","width":1,"note":""},{"offset":60,"name":"Reverb Filter HPF","width":1,"note":""},{"offset":61,"name":"Reverb HF Damp Frequency","width":1,"note":""},{"offset":62,"name":"Reverb HF Damp Level","width":1,"note":""},{"offset":64,"name":"Reverb Level","width":1,"note":""},{"offset":65,"name":"Reverb Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"7":[{"offset":24,"name":"EQ High Level","width":1,"note":""},{"offset":25,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":26,"name":"EQ Mid Level","width":1,"note":""},{"offset":27,"name":"EQ Low Level","width":1,"note":""},{"offset":28,"name":"EQ Total Level","width":1,"note":""},{"offset":29,"name":"Chorus LFO Waveform","width":1,"note":""},{"offset":30,"name":"Chorus Pre-Delay","width":1,"note":""},{"offset":31,"name":"Chorus Rate","width":1,"note":""},{"offset":32,"name":"Chorus Depth","width":1,"note":""},{"offset":33,"name":"Chorus Mix Level","width":1,"note":""},{"offset":34,"name":"Chorus Cross Mix","width":1,"note":""},{"offset":35,"name":"Chorus Direct Level","width":1,"note":""},{"offset":48,"name":"Delay Time","width":2,"note":""},{"offset":50,"name":"Delay Feedback","width":1,"note":""},{"offset":51,"name":"Delay HF Damp Frequency","width":1,"note":""},{"offset":52,"name":"Delay HF Damp Level","width":1,"note":""},{"offset":53,"name":"Delay Mix Level","width":1,"note":""},{"offset":54,"name":"Delay Direct Level","width":1,"note":""},{"offset":55,"name":"Reverb Time","width":2,"note":""},{"offset":57,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":59,"name":"Reverb Filter LPF","width":1,"note":""},{"offset":60,"name":"Reverb Filter HPF","width":1,"note":""},{"offset":61,"name":"Reverb HF Damp Frequency","width":1,"note":""},{"offset":62,"name":"Reverb HF Damp Level","width":1,"note":""},{"offset":64,"name":"Reverb Level","width":1,"note":""},{"offset":65,"name":"Reverb Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"8":[{"offset":24,"name":"EQ High Level","width":1,"note":""},{"offset":25,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":26,"name":"EQ Mid Level","width":1,"note":""},{"offset":27,"name":"EQ Low Level","width":1,"note":""},{"offset":28,"name":"EQ Total Level","width":1,"note":""},{"offset":29,"name":"Pitch Shifter 1 Shift Mode","width":1,"note":""},{"offset":30,"name":"Pitch Shifter 1 Chromatic","width":1,"note":""},{"offset":31,"name":"Pitch Shifter 1 Fine","width":1,"note":""},{"offset":32,"name":"Pitch Shifter 1 Mix Level","width":1,"note":""},{"offset":33,"name":"Pitch Shifter 1 Pan","width":1,"note":""},{"offset":34,"name":"Pitch Shifter 2 Shift Mode","width":1,"note":""},{"offset":35,"name":"Pitch Shifter 2 Chromatic","width":1,"note":""},{"offset":36,"name":"Pitch Shifter 2 Fine","width":1,"note":""},{"offset":37,"name":"Pitch Shifter 2 Mix Level","width":1,"note":""},{"offset":38,"name":"Pitch Shifter 2 Pan","width":1,"note":""},{"offset":47,"name":"Delay Input Select","width":1,"note":""},{"offset":48,"name":"Delay Time","width":2,"note":""},{"offset":50,"name":"Delay Feedback","width":1,"note":""},{"offset":51,"name":"Delay HF Damp Frequency","width":1,"note":""},{"offset":52,"name":"Delay HF Damp Level","width":1,"note":""},{"offset":53,"name":"Delay Mix Level","width":1,"note":""},{"offset":54,"name":"Delay Direct Level","width":1,"note":""},{"offset":55,"name":"Reverb Time","width":2,"note":""},{"offset":57,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":59,"name":"Reverb Filter LPF","width":1,"note":""},{"offset":60,"name":"Reverb Filter HPF","width":1,"note":""},{"offset":61,"name":"Reverb HF Damp Frequency","width":1,"note":""},{"offset":62,"name":"Reverb HF Damp Level","width":1,"note":""},{"offset":64,"name":"Reverb Level","width":1,"note":""},{"offset":65,"name":"Reverb Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"9":[{"offset":20,"name":"Phaser Mode","width":1,"note":""},{"offset":25,"name":"Phaser Rate","width":1,"note":""},{"offset":26,"name":"Phaser Depth","width":1,"note":""},{"offset":27,"name":"Phaser Manual","width":1,"note":""},{"offset":28,"name":"Phaser Resonance","width":1,"note":""},{"offset":29,"name":"Phaser Step Rate","width":1,"note":""},{"offset":30,"name":"Phaser Modulation Phase","width":1,"note":""},{"offset":31,"name":"Phaser Tremolo Depth","width":1,"note":""},{"offset":36,"name":"Chorus Rate","width":1,"note":""},{"offset":37,"name":"Chorus Depth","width":1,"note":""},{"offset":38,"name":"Chorus Mix Level","width":1,"note":""},{"offset":39,"name":"Pan Rate","width":1,"note":""},{"offset":40,"name":"Pan Depth","width":1,"note":""},{"offset":48,"name":"Delay Time","width":2,"note":""},{"offset":50,"name":"Delay Feedback","width":1,"note":""},{"offset":53,"name":"Delay Mix Level","width":1,"note":""},{"offset":54,"name":"Delay Direct Level","width":1,"note":""},{"offset":55,"name":"Reverb Time","width":2,"note":""},{"offset":57,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":64,"name":"Reverb Level","width":1,"note":""},{"offset":65,"name":"Reverb Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"10":[{"offset":20,"name":"Phasing Mode","width":1,"note":""},{"offset":21,"name":"Sensitivity","width":1,"note":""},{"offset":22,"name":"LFO Rate Max","width":1,"note":""},{"offset":23,"name":"Control Range","width":1,"note":""},{"offset":26,"name":"Phasing Depth","width":1,"note":""},{"offset":27,"name":"Manual","width":1,"note":""},{"offset":28,"name":"Resonance","width":1,"note":""},{"offset":29,"name":"Step Rate","width":1,"note":""},{"offset":30,"name":"Modulation Phase","width":1,"note":""},{"offset":31,"name":"Tremolo Depth","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"11":[{"offset":20,"name":"Chorus Mode","width":1,"note":""},{"offset":21,"name":"LFO Waveform","width":1,"note":""},{"offset":22,"name":"Pre-Delay","width":1,"note":""},{"offset":23,"name":"Chorus Rate","width":1,"note":""},{"offset":24,"name":"Chorus Depth","width":1,"note":""},{"offset":25,"name":"Chorus Tone","width":1,"note":""},{"offset":26,"name":"Chorus Level","width":1,"note":""},{"offset":27,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"12":[{"offset":20,"name":"Space Mode","width":1,"note":""},{"offset":21,"name":"Direct Mix","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"13":[{"offset":22,"name":"EQ High Level","width":1,"note":""},{"offset":23,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":24,"name":"EQ Mid Level","width":1,"note":""},{"offset":25,"name":"EQ Low Level","width":1,"note":""},{"offset":26,"name":"EQ Total Level","width":1,"note":""},{"offset":27,"name":"Chorus Mode","width":1,"note":""},{"offset":28,"name":"Chorus LFO Waveform","width":1,"note":""},{"offset":29,"name":"Chorus Pre-Delay","width":1,"note":""},{"offset":30,"name":"Chorus Rate","width":1,"note":""},{"offset":31,"name":"Chorus Depth","width":1,"note":""},{"offset":32,"name":"Chorus Mix Level","width":1,"note":""},{"offset":33,"name":"Chorus Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"14":[{"offset":24,"name":"Low Band LFO Waveform","width":1,"note":""},{"offset":25,"name":"Low Band Pre-Delay","width":1,"note":""},{"offset":26,"name":"Low Band Rate","width":1,"note":""},{"offset":27,"name":"Low Band Depth","width":1,"note":""},{"offset":28,"name":"Low Band Pan","width":1,"note":""},{"offset":29,"name":"Low Band Mix Level","width":1,"note":""},{"offset":30,"name":"Low-Mid Band LFO Waveform","width":1,"note":""},{"offset":31,"name":"Low-Mid Band Pre-Delay","width":1,"note":""},{"offset":32,"name":"Low-Mid Band Rate","width":1,"note":""},{"offset":33,"name":"Low-Mid Band Depth","width":1,"note":""},{"offset":34,"name":"Low-Mid Band Pan","width":1,"note":""},{"offset":35,"name":"Low-Mid Band Mix Level","width":1,"note":""},{"offset":36,"name":"High-Mid Band LFO Waveform","width":1,"note":""},{"offset":37,"name":"High-Mid Band Pre-Delay","width":1,"note":""},{"offset":38,"name":"High-Mid Band Rate","width":1,"note":""},{"offset":39,"name":"High-Mid Band Depth","width":1,"note":""},{"offset":40,"name":"High-Mid Band Pan","width":1,"note":""},{"offset":41,"name":"High-Mid Band Mix Level","width":1,"note":""},{"offset":42,"name":"High Band LFO Waveform","width":1,"note":""},{"offset":43,"name":"High Band Pre-Delay","width":1,"note":""},{"offset":44,"name":"High Band Rate","width":1,"note":""},{"offset":45,"name":"High Band Depth","width":1,"note":""},{"offset":46,"name":"High Band Pan","width":1,"note":""},{"offset":47,"name":"High Band Mix Level","width":1,"note":""},{"offset":67,"name":"Crossover Frequency","width":1,"note":""},{"offset":68,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"15":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":28,"name":"Edge Sensitivity","width":1,"note":""},{"offset":29,"name":"Edge Release Time","width":1,"note":""},{"offset":30,"name":"Edge Mix Level","width":1,"note":""},{"offset":31,"name":"Ambience Pre-Delay","width":2,"note":""},{"offset":33,"name":"Ambience Early Reflection Level","width":1,"note":""},{"offset":34,"name":"Ambience Mix Level","width":1,"note":""},{"offset":35,"name":"Ambience Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"16":[{"offset":22,"name":"EQ High Level","width":1,"note":""},{"offset":23,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":24,"name":"EQ Mid Level","width":1,"note":""},{"offset":25,"name":"EQ Low Level","width":1,"note":""},{"offset":26,"name":"EQ Total Level","width":1,"note":""},{"offset":27,"name":"Gate Mode","width":1,"note":""},{"offset":28,"name":"Gate Time","width":2,"note":""},{"offset":30,"name":"Pre-Delay","width":2,"note":""},{"offset":32,"name":"Density","width":1,"note":""},{"offset":33,"name":"Thickness","width":1,"note":""},{"offset":34,"name":"Accent Delay","width":2,"note":""},{"offset":36,"name":"Accent Level","width":1,"note":""},{"offset":37,"name":"Reverb Level","width":1,"note":""},{"offset":38,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"17":[{"offset":22,"name":"EQ High Level","width":1,"note":""},{"offset":23,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":24,"name":"EQ Mid Level","width":1,"note":""},{"offset":25,"name":"EQ Low Level","width":1,"note":""},{"offset":26,"name":"EQ Total Level","width":1,"note":""},{"offset":27,"name":"Gate Mode","width":1,"note":""},{"offset":28,"name":"Gate Time","width":2,"note":""},{"offset":30,"name":"Pre-Delay","width":2,"note":""},{"offset":32,"name":"Density","width":1,"note":""},{"offset":33,"name":"Thickness","width":1,"note":""},{"offset":34,"name":"Accent Delay","width":2,"note":""},{"offset":36,"name":"Accent Level","width":1,"note":""},{"offset":37,"name":"Reverb Level","width":1,"note":""},{"offset":38,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"18":[{"offset":24,"name":"Low Band LFO Waveform","width":1,"note":""},{"offset":25,"name":"Low Band Pre-Delay","width":1,"note":""},{"offset":26,"name":"Low Band Rate","width":1,"note":""},{"offset":27,"name":"Low Band Depth","width":1,"note":""},{"offset":28,"name":"Low Band Mix Level","width":1,"note":""},{"offset":29,"name":"High Band LFO Waveform","width":1,"note":""},{"offset":30,"name":"High Band Pre-Delay","width":1,"note":""},{"offset":31,"name":"High Band Rate","width":1,"note":""},{"offset":32,"name":"High Band Depth","width":1,"note":""},{"offset":33,"name":"High Band Mix Level","width":1,"note":""},{"offset":67,"name":"Crossover Frequency","width":1,"note":""},{"offset":68,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"19":[{"offset":20,"name":"Ensemble Mode","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"20":[{"offset":24,"name":"Low 1 Chromatic","width":1,"note":""},{"offset":25,"name":"Low 1 Fine","width":1,"note":""},{"offset":26,"name":"Low 1 Pre-Delay","width":2,"note":""},{"offset":28,"name":"Low 1 Mix Level","width":1,"note":""},{"offset":29,"name":"Low 1 Pan","width":1,"note":""},{"offset":30,"name":"Low 2 Chromatic","width":1,"note":""},{"offset":31,"name":"Low 2 Fine","width":1,"note":""},{"offset":32,"name":"Low 2 Pre-Delay","width":2,"note":""},{"offset":34,"name":"Low 2 Mix Level","width":1,"note":""},{"offset":35,"name":"Low 2 Pan","width":1,"note":""},{"offset":36,"name":"High 1 Chromatic","width":1,"note":""},{"offset":37,"name":"High 1 Fine","width":1,"note":""},{"offset":38,"name":"High 1 Pre-Delay","width":2,"note":""},{"offset":40,"name":"High 1 Mix Level","width":1,"note":""},{"offset":41,"name":"High 1 Pan","width":1,"note":""},{"offset":42,"name":"High 2 Chromatic","width":1,"note":""},{"offset":43,"name":"High 2 Fine","width":1,"note":""},{"offset":44,"name":"High 2 Pre-Delay","width":2,"note":""},{"offset":46,"name":"High 2 Mix Level","width":1,"note":""},{"offset":47,"name":"High 2 Pan","width":1,"note":""},{"offset":67,"name":"Crossover Frequency","width":1,"note":""},{"offset":68,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"21":[{"offset":22,"name":"Pitch Shifter 1 Shift Mode","width":1,"note":""},{"offset":23,"name":"Pitch Shifter 1 Chromatic","width":1,"note":""},{"offset":24,"name":"Pitch Shifter 1 Fine","width":1,"note":""},{"offset":25,"name":"Pitch Shifter 1 Pre-Delay","width":2,"note":""},{"offset":27,"name":"Pitch Shifter 1 Feedback","width":1,"note":""},{"offset":28,"name":"Pitch Shifter 1 Mix Level","width":1,"note":""},{"offset":29,"name":"Pitch Shifter 1 Pan","width":1,"note":""},{"offset":30,"name":"Pitch Shifter 2 Shift Mode","width":1,"note":""},{"offset":31,"name":"Pitch Shifter 2 Chromatic","width":1,"note":""},{"offset":32,"name":"Pitch Shifter 2 Fine","width":1,"note":""},{"offset":33,"name":"Pitch Shifter 2 Pre-Delay","width":2,"note":""},{"offset":35,"name":"Pitch Shifter 2 Feedback","width":1,"note":""},{"offset":36,"name":"Pitch Shifter 2 Mix Level","width":1,"note":""},{"offset":37,"name":"Pitch Shifter 2 Pan","width":1,"note":""},{"offset":68,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"22":[{"offset":24,"name":"Pitch Shifter 1 Shift Mode","width":1,"note":""},{"offset":25,"name":"Pitch Shifter 1 Chromatic","width":1,"note":""},{"offset":26,"name":"Pitch Shifter 1 Fine","width":1,"note":""},{"offset":27,"name":"Pitch Shifter 1 Pre-Delay","width":2,"note":""},{"offset":29,"name":"Pitch Shifter 1 Mix Level","width":1,"note":""},{"offset":30,"name":"Pitch Shifter 1 Pan","width":1,"note":""},{"offset":31,"name":"Pitch Shifter 2 Shift Mode","width":1,"note":""},{"offset":32,"name":"Pitch Shifter 2 Chromatic","width":1,"note":""},{"offset":33,"name":"Pitch Shifter 2 Fine","width":1,"note":""},{"offset":34,"name":"Pitch Shifter 2 Pre-Delay","width":2,"note":""},{"offset":36,"name":"Pitch Shifter 2 Mix Level","width":1,"note":""},{"offset":37,"name":"Pitch Shifter 2 Pan","width":1,"note":""},{"offset":38,"name":"Pitch Shifter 3 Shift Mode","width":1,"note":""},{"offset":39,"name":"Pitch Shifter 3 Chromatic","width":1,"note":""},{"offset":40,"name":"Pitch Shifter 3 Fine","width":1,"note":""},{"offset":41,"name":"Pitch Shifter 3 Pre-Delay","width":2,"note":""},{"offset":43,"name":"Pitch Shifter 3 Mix Level","width":1,"note":""},{"offset":44,"name":"Pitch Shifter 3 Pan","width":1,"note":""},{"offset":45,"name":"Pitch Shifter 4 Shift Mode","width":1,"note":""},{"offset":46,"name":"Pitch Shifter 4 Chromatic","width":1,"note":""},{"offset":47,"name":"Pitch Shifter 4 Fine","width":1,"note":""},{"offset":48,"name":"Pitch Shifter 4 Pre-Delay","width":2,"note":""},{"offset":50,"name":"Pitch Shifter 4 Mix Level","width":1,"note":""},{"offset":51,"name":"Pitch Shifter 4 Pan","width":1,"note":""},{"offset":52,"name":"Feedback","width":1,"note":""},{"offset":68,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"23":[{"offset":24,"name":"Rotary Speed Select","width":1,"note":""},{"offset":25,"name":"Horn Speed Fast","width":1,"note":""},{"offset":26,"name":"Rotor Speed Fast","width":1,"note":""},{"offset":27,"name":"Horn Speed Slow","width":1,"note":""},{"offset":28,"name":"Rotor Speed Slow","width":1,"note":""},{"offset":29,"name":"Rise Time Horn","width":1,"note":""},{"offset":30,"name":"Rise Time Rotor","width":1,"note":""},{"offset":31,"name":"Fall Time Horn","width":1,"note":""},{"offset":32,"name":"Fall Time Rotor","width":1,"note":""},{"offset":33,"name":"Mix Balance","width":1,"note":""},{"offset":34,"name":"Overdrive Gain","width":1,"note":""},{"offset":35,"name":"Overdrive Drive","width":1,"note":""},{"offset":36,"name":"Overdrive Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"24":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":28,"name":"Gate Threshold Level","width":1,"note":""},{"offset":29,"name":"Gate Hold Time","width":1,"note":""},{"offset":30,"name":"Gate Attack Time","width":1,"note":""},{"offset":31,"name":"Gate Release Time","width":1,"note":""},{"offset":32,"name":"Gate Leftover","width":1,"note":""},{"offset":33,"name":"Reverb Time","width":2,"note":""},{"offset":35,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":37,"name":"HF Damp Frequency","width":1,"note":""},{"offset":38,"name":"HF Damp Level","width":1,"note":""},{"offset":39,"name":"Diffusion","width":1,"note":""},{"offset":40,"name":"Early Reflection Pre-Delay","width":2,"note":""},{"offset":42,"name":"Early Reflection Level","width":1,"note":""},{"offset":43,"name":"Reverb Level","width":1,"note":""},{"offset":44,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"25":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":33,"name":"Reverb Time","width":2,"note":""},{"offset":35,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":37,"name":"HF Damp Frequency","width":1,"note":""},{"offset":38,"name":"HF Damp Level","width":1,"note":""},{"offset":39,"name":"Diffusion","width":1,"note":""},{"offset":40,"name":"Reverb Level","width":1,"note":""},{"offset":41,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"26":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":28,"name":"Gate Threshold Level","width":1,"note":""},{"offset":29,"name":"Gate Hold Time","width":1,"note":""},{"offset":30,"name":"Gate Attack Time","width":1,"note":""},{"offset":31,"name":"Gate Release Time","width":1,"note":""},{"offset":32,"name":"Gate Leftover","width":1,"note":""},{"offset":33,"name":"Reverb Time","width":2,"note":""},{"offset":35,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":37,"name":"HF Damp Frequency","width":1,"note":""},{"offset":38,"name":"HF Damp Level","width":1,"note":""},{"offset":39,"name":"Diffusion","width":1,"note":""},{"offset":40,"name":"Early Reflection Pre-Delay","width":2,"note":""},{"offset":42,"name":"Early Reflection Level","width":1,"note":""},{"offset":43,"name":"Reverb Level","width":1,"note":""},{"offset":44,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"27":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":28,"name":"Gate Threshold Level","width":1,"note":""},{"offset":29,"name":"Gate Hold Time","width":1,"note":""},{"offset":30,"name":"Gate Attack Time","width":1,"note":""},{"offset":31,"name":"Gate Release Time","width":1,"note":""},{"offset":32,"name":"Gate Leftover","width":1,"note":""},{"offset":33,"name":"Reverb Time","width":2,"note":""},{"offset":35,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":37,"name":"HF Damp Frequency","width":1,"note":""},{"offset":38,"name":"HF Damp Level","width":1,"note":""},{"offset":39,"name":"Diffusion","width":1,"note":""},{"offset":40,"name":"Early Reflection Pre-Delay","width":2,"note":""},{"offset":42,"name":"Early Reflection Level","width":1,"note":""},{"offset":43,"name":"Reverb Level","width":1,"note":""},{"offset":44,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"28":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":33,"name":"Reverb Time","width":2,"note":""},{"offset":35,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":37,"name":"HF Damp Frequency","width":1,"note":""},{"offset":38,"name":"HF Damp Level","width":1,"note":""},{"offset":39,"name":"Diffusion","width":1,"note":""},{"offset":40,"name":"Reverb Level","width":1,"note":""},{"offset":41,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"29":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":28,"name":"Gate Threshold Level","width":1,"note":""},{"offset":29,"name":"Gate Hold Time","width":1,"note":""},{"offset":30,"name":"Gate Attack Time","width":1,"note":""},{"offset":31,"name":"Gate Release Time","width":1,"note":""},{"offset":32,"name":"Gate Leftover","width":1,"note":""},{"offset":33,"name":"Reverb Time","width":2,"note":""},{"offset":35,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":37,"name":"HF Damp Frequency","width":1,"note":""},{"offset":38,"name":"HF Damp Level","width":1,"note":""},{"offset":39,"name":"Diffusion","width":1,"note":""},{"offset":40,"name":"Reverb Level","width":1,"note":""},{"offset":44,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"30":[{"offset":23,"name":"EQ High Level","width":1,"note":""},{"offset":24,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":25,"name":"EQ Mid Level","width":1,"note":""},{"offset":26,"name":"EQ Low Level","width":1,"note":""},{"offset":27,"name":"EQ Total Level","width":1,"note":""},{"offset":33,"name":"Reverb Time","width":2,"note":""},{"offset":35,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":37,"name":"HF Damp Frequency","width":1,"note":""},{"offset":38,"name":"HF Damp Level","width":1,"note":""},{"offset":39,"name":"Diffusion","width":1,"note":""},{"offset":40,"name":"Reverb Level","width":1,"note":""},{"offset":44,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"31":[{"offset":20,"name":"Tap 1 Delay Time","width":2,"note":""},{"offset":22,"name":"Tap 1 Feedback","width":1,"note":""},{"offset":23,"name":"Tap 1 Pan","width":1,"note":""},{"offset":24,"name":"Tap 1 Mix Level","width":1,"note":""},{"offset":25,"name":"Tap 2 Delay Time","width":2,"note":""},{"offset":27,"name":"Tap 2 Feedback","width":1,"note":""},{"offset":28,"name":"Tap 2 Pan","width":1,"note":""},{"offset":29,"name":"Tap 2 Mix Level","width":1,"note":""},{"offset":30,"name":"Tap 3 Delay Time","width":2,"note":""},{"offset":32,"name":"Tap 3 Feedback","width":1,"note":""},{"offset":33,"name":"Tap 3 Pan","width":1,"note":""},{"offset":34,"name":"Tap 3 Mix Level","width":1,"note":""},{"offset":35,"name":"Tap 4 Delay Time","width":2,"note":""},{"offset":37,"name":"Tap 4 Feedback","width":1,"note":""},{"offset":38,"name":"Tap 4 Pan","width":1,"note":""},{"offset":39,"name":"Tap 4 Mix Level","width":1,"note":""},{"offset":40,"name":"Tap 5 Delay Time","width":2,"note":""},{"offset":42,"name":"Tap 5 Feedback","width":1,"note":""},{"offset":43,"name":"Tap 5 Pan","width":1,"note":""},{"offset":44,"name":"Tap 5 Mix Level","width":1,"note":""},{"offset":45,"name":"Tap 6 Delay Time","width":2,"note":""},{"offset":47,"name":"Tap 6 Feedback","width":1,"note":""},{"offset":48,"name":"Tap 6 Pan","width":1,"note":""},{"offset":49,"name":"Tap 6 Mix Level","width":1,"note":""},{"offset":50,"name":"Tap 7 Delay Time","width":2,"note":""},{"offset":52,"name":"Tap 7 Feedback","width":1,"note":""},{"offset":53,"name":"Tap 7 Pan","width":1,"note":""},{"offset":54,"name":"Tap 7 Mix Level","width":1,"note":""},{"offset":55,"name":"Tap 8 Delay Time","width":2,"note":""},{"offset":57,"name":"Tap 8 Feedback","width":1,"note":""},{"offset":58,"name":"Tap 8 Pan","width":1,"note":""},{"offset":59,"name":"Tap 8 Mix Level","width":1,"note":""},{"offset":60,"name":"EQ High Level","width":1,"note":""},{"offset":61,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":62,"name":"EQ Mid Level","width":1,"note":""},{"offset":63,"name":"EQ Low Level","width":1,"note":""},{"offset":64,"name":"EQ Total Level","width":1,"note":""},{"offset":68,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"32":[{"offset":20,"name":"Tap 1 Delay Time","width":2,"note":""},{"offset":22,"name":"Tap 1 Mix Level","width":1,"note":""},{"offset":23,"name":"Tap 1 LFO Waveform","width":1,"note":""},{"offset":24,"name":"Tap 1 Pan Rate","width":1,"note":""},{"offset":25,"name":"Tap 1 Pan Depth","width":1,"note":""},{"offset":26,"name":"Tap 2 Delay Time","width":2,"note":""},{"offset":28,"name":"Tap 2 Mix Level","width":1,"note":""},{"offset":29,"name":"Tap 2 LFO Waveform","width":1,"note":""},{"offset":30,"name":"Tap 2 Pan Rate","width":1,"note":""},{"offset":31,"name":"Tap 2 Pan Depth","width":1,"note":""},{"offset":32,"name":"Tap 3 Delay Time","width":2,"note":""},{"offset":34,"name":"Tap 3 Mix Level","width":1,"note":""},{"offset":35,"name":"Tap 3 LFO Waveform","width":1,"note":""},{"offset":36,"name":"Tap 3 Pan Rate","width":1,"note":""},{"offset":37,"name":"Tap 3 Pan Depth","width":1,"note":""},{"offset":38,"name":"Tap 4 Delay Time","width":2,"note":""},{"offset":40,"name":"Tap 4 Mix Level","width":1,"note":""},{"offset":41,"name":"Tap 4 LFO Waveform","width":1,"note":""},{"offset":42,"name":"Tap 4 Pan Rate","width":1,"note":""},{"offset":43,"name":"Tap 4 Pan Depth","width":1,"note":""},{"offset":44,"name":"Feedback Position","width":2,"note":""},{"offset":46,"name":"Feedback","width":1,"note":""},{"offset":47,"name":"Feedback HF Damp Frequency","width":1,"note":""},{"offset":48,"name":"Feedback HF Damp Level","width":1,"note":""},{"offset":49,"name":"Feedback Filter","width":1,"note":""},{"offset":60,"name":"EQ High Level","width":1,"note":""},{"offset":61,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":62,"name":"EQ Mid Level","width":1,"note":""},{"offset":63,"name":"EQ Low Level","width":1,"note":""},{"offset":64,"name":"EQ Total Level","width":1,"note":""},{"offset":68,"name":"Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"33":[{"offset":23,"name":"Delay Tempo","width":2,"note":""},{"offset":25,"name":"Delay Interval","width":1,"note":""},{"offset":26,"name":"Delay Feedback","width":1,"note":""},{"offset":28,"name":"HF Damp Frequency","width":1,"note":""},{"offset":29,"name":"HF Damp Level","width":1,"note":""},{"offset":30,"name":"Feedback Filter","width":1,"note":""},{"offset":31,"name":"Separation","width":1,"note":""},{"offset":32,"name":"Delay Mix Level","width":1,"note":""},{"offset":33,"name":"Delay Direct Level","width":1,"note":""},{"offset":35,"name":"Modulation LFO Waveform","width":1,"note":""},{"offset":36,"name":"Modulation Rate","width":1,"note":""},{"offset":37,"name":"Modulation Depth","width":1,"note":""},{"offset":40,"name":"EQ High Level","width":1,"note":""},{"offset":41,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":42,"name":"EQ Mid Level","width":1,"note":""},{"offset":43,"name":"EQ Low Level","width":1,"note":""},{"offset":44,"name":"EQ Total Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"34":[{"offset":21,"name":"Left Channel Frequency","width":1,"note":""},{"offset":23,"name":"Left Channel Mix Balance","width":1,"note":""},{"offset":24,"name":"Right Channel Frequency","width":1,"note":""},{"offset":25,"name":"Right Channel Mix Balance","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"35":[{"offset":24,"name":"Vibrato Rate","width":1,"note":""},{"offset":25,"name":"Vibrato Depth","width":1,"note":""},{"offset":26,"name":"Vibrato Rise Time","width":1,"note":""},{"offset":27,"name":"Vibrato Fall Time","width":1,"note":""},{"offset":28,"name":"Vibrato Pan Mode","width":1,"note":""},{"offset":29,"name":"Vibrato Pan Waveform","width":1,"note":""},{"offset":30,"name":"Vibrato Pan Rate","width":1,"note":""},{"offset":31,"name":"Vibrato Pan Depth","width":1,"note":""},{"offset":48,"name":"Delay Time","width":2,"note":""},{"offset":50,"name":"Delay Feedback","width":1,"note":""},{"offset":51,"name":"Delay HF Damp Frequency","width":1,"note":""},{"offset":52,"name":"Delay HF Damp Level","width":1,"note":""},{"offset":53,"name":"Delay Mix Level","width":1,"note":""},{"offset":54,"name":"Delay Direct Level","width":1,"note":""},{"offset":55,"name":"Reverb Time","width":2,"note":""},{"offset":57,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":59,"name":"Reverb Filter LPF","width":1,"note":""},{"offset":60,"name":"Reverb Filter HPF","width":1,"note":""},{"offset":61,"name":"Reverb HF Damp Frequency","width":1,"note":""},{"offset":62,"name":"Reverb HF Damp Level","width":1,"note":""},{"offset":64,"name":"Reverb Level","width":1,"note":""},{"offset":65,"name":"Reverb Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"36":[{"offset":30,"name":"EQ High Level","width":1,"note":""},{"offset":31,"name":"EQ Mid Frequency","width":1,"note":""},{"offset":32,"name":"EQ Mid Level","width":1,"note":""},{"offset":33,"name":"EQ Low Level","width":1,"note":""},{"offset":34,"name":"EQ Total Level","width":1,"note":""},{"offset":35,"name":"Modulation LFO Waveform","width":1,"note":""},{"offset":36,"name":"Modulation Rate","width":1,"note":""},{"offset":37,"name":"Modulation Depth","width":1,"note":""},{"offset":55,"name":"Reverb Time","width":2,"note":""},{"offset":57,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":59,"name":"Reverb Filter LPF","width":1,"note":""},{"offset":60,"name":"Reverb Filter HPF","width":1,"note":""},{"offset":61,"name":"Reverb HF Damp Frequency","width":1,"note":""},{"offset":62,"name":"Reverb HF Damp Level","width":1,"note":""},{"offset":64,"name":"Reverb Level","width":1,"note":""},{"offset":65,"name":"Reverb Cross Mix","width":1,"note":""},{"offset":66,"name":"Reverb Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"37":[{"offset":24,"name":"Reverb 1 Input Select","width":1,"note":""},{"offset":25,"name":"Reverb 1 Time","width":2,"note":""},{"offset":27,"name":"Reverb 1 Pre-Delay","width":2,"note":""},{"offset":29,"name":"Reverb 1 Filter LPF","width":1,"note":""},{"offset":30,"name":"Reverb 1 Filter HPF","width":1,"note":""},{"offset":31,"name":"Reverb 1 HF Damp Frequency","width":1,"note":""},{"offset":32,"name":"Reverb 1 HF Damp Level","width":1,"note":""},{"offset":33,"name":"Reverb 1 Mix Level","width":1,"note":""},{"offset":39,"name":"Delay Input Select","width":1,"note":""},{"offset":48,"name":"Delay Time","width":2,"note":""},{"offset":50,"name":"Delay Feedback","width":1,"note":""},{"offset":51,"name":"Delay HF Damp Frequency","width":1,"note":""},{"offset":52,"name":"Delay HF Damp Level","width":1,"note":""},{"offset":53,"name":"Delay Mix Level","width":1,"note":""},{"offset":54,"name":"Delay Direct Level","width":1,"note":""},{"offset":55,"name":"Reverb 2 Time","width":2,"note":""},{"offset":57,"name":"Reverb 2 Pre-Delay","width":2,"note":""},{"offset":59,"name":"Reverb 2 Filter LPF","width":1,"note":""},{"offset":60,"name":"Reverb 2 Filter HPF","width":1,"note":""},{"offset":61,"name":"Reverb 2 HF Damp Frequency","width":1,"note":""},{"offset":62,"name":"Reverb 2 HF Damp Level","width":1,"note":""},{"offset":64,"name":"Reverb 2 Level","width":1,"note":""},{"offset":65,"name":"Reverb Cross Mix","width":1,"note":""},{"offset":66,"name":"Reverb 2 Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"38":[{"offset":24,"name":"Delay EQ High Level","width":1,"note":""},{"offset":25,"name":"Delay EQ Mid Frequency","width":1,"note":""},{"offset":26,"name":"Delay EQ Mid Level","width":1,"note":""},{"offset":27,"name":"Delay EQ Low Level","width":1,"note":""},{"offset":28,"name":"Delay EQ Total Level","width":1,"note":""},{"offset":29,"name":"Reverb EQ High Level","width":1,"note":""},{"offset":30,"name":"Reverb EQ Mid Frequency","width":1,"note":""},{"offset":31,"name":"Reverb EQ Mid Level","width":1,"note":""},{"offset":32,"name":"Reverb EQ Low Level","width":1,"note":""},{"offset":33,"name":"Reverb EQ Total Level","width":1,"note":""},{"offset":34,"name":"Delay Modulation LFO Waveform","width":1,"note":""},{"offset":35,"name":"Delay Modulation Rate","width":1,"note":""},{"offset":36,"name":"Delay Modulation Depth","width":1,"note":""},{"offset":40,"name":"Delay Input Select","width":1,"note":""},{"offset":48,"name":"Delay Time","width":2,"note":""},{"offset":50,"name":"Delay Feedback","width":1,"note":""},{"offset":51,"name":"Delay HF Damp Frequency","width":1,"note":""},{"offset":52,"name":"Delay HF Damp Level","width":1,"note":""},{"offset":53,"name":"Delay Mix Level","width":1,"note":""},{"offset":54,"name":"Delay Direct Level","width":1,"note":""},{"offset":55,"name":"Reverb Time","width":2,"note":""},{"offset":57,"name":"Reverb Pre-Delay","width":2,"note":""},{"offset":59,"name":"Reverb Filter LPF","width":1,"note":""},{"offset":60,"name":"Reverb Filter HPF","width":1,"note":""},{"offset":61,"name":"Reverb HF Damp Frequency","width":1,"note":""},{"offset":62,"name":"Reverb HF Damp Level","width":1,"note":""},{"offset":64,"name":"Reverb Level","width":1,"note":""},{"offset":65,"name":"Reverb Direct Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}],"39":[{"offset":24,"name":"Rotary Speed Select","width":1,"note":""},{"offset":25,"name":"Horn Speed Fast","width":1,"note":""},{"offset":26,"name":"Rotor Speed Fast","width":1,"note":""},{"offset":27,"name":"Horn Speed Slow","width":1,"note":""},{"offset":28,"name":"Rotor Speed Slow","width":1,"note":""},{"offset":29,"name":"Rise Time Horn","width":1,"note":""},{"offset":30,"name":"Rise Time Rotor","width":1,"note":""},{"offset":31,"name":"Fall Time Horn","width":1,"note":""},{"offset":32,"name":"Fall Time Rotor","width":1,"note":""},{"offset":33,"name":"Mix Balance","width":1,"note":""},{"offset":34,"name":"Overdrive Gain","width":1,"note":""},{"offset":35,"name":"Overdrive Drive","width":1,"note":""},{"offset":36,"name":"Overdrive Level","width":1,"note":""},{"offset":69,"name":"Total Level","width":1,"note":""}]}').items()}


# Load the richer manual-derived map when the sidecar JSON ships with this script.
# The embedded copy above remains a fallback for users who only copy this file.
MAP_PATH = Path(__file__).with_name("rsp550_syx_parameter_map.json")
PARAMETER_METADATA = {}
if MAP_PATH.exists():
    try:
        _map_data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        if isinstance(_map_data.get("algorithms"), dict):
            ALGORITHM_NAMES = {int(k): v.get("name", "Unknown") for k, v in _map_data["algorithms"].items()}
            PARAMS = {int(k): v.get("parameters", []) for k, v in _map_data["algorithms"].items()}
            PARAMETER_METADATA = {
                (int(k), int(item["offset"]), item["name"].casefold()): item
                for k, v in _map_data["algorithms"].items()
                for item in v.get("parameters", [])
            }
    except (OSError, ValueError, TypeError, KeyError):
        # A malformed/missing sidecar should not make raw-byte commands unavailable.
        PARAMETER_METADATA = {}


def metadata_for_parameter(alg: int, parameter: dict) -> dict:
    """Return the range/interpretation metadata for a mapped parameter, if present."""
    return PARAMETER_METADATA.get((alg, int(parameter["offset"]), parameter["name"].casefold()), parameter)


def readable_value(parameter: dict, value: int) -> str:
    """Interpret only the conversions supported by the Roland documentation."""
    meta = parameter
    enum_map = meta.get("enum_map") or {}
    if str(value) in enum_map:
        return enum_map[str(value)]
    rule = meta.get("display_rule", "raw-count")
    unit = meta.get("unit_or_scale", "")
    lo, hi = meta.get("min_raw"), meta.get("max_raw")
    range_text = f"valid {lo}–{hi}" if lo is not None and hi is not None else "range not mapped"
    if rule == "fine-offset":
        # The Parameter Guide describes -50..+50 as the one-semitone fine-tune span;
        # this offset is documented only as provisional pending read-back verification.
        return f"{value - 50:+d} (Fine display; provisional raw−50)"
    if rule == "bpm-direct":
        return f"{value} BPM"
    if rule == "milliseconds-direct":
        return f"{value} ms"
    if rule == "scaled-time-unknown":
        return f"raw code {value} ({range_text}; nonlinear time scale)"
    if lo is not None and hi is not None:
        suffix = f"; {unit}" if unit else ""
        return f"{value} ({range_text}{suffix})"
    return f"{value} (raw count)"


def checksum_for(message: bytes | bytearray) -> int:
    return (-sum(message[5:8]) - sum(message[8:104])) & 0x7F


def parse_messages(data: bytes, require_valid_checksums: bool = True):
    if not data:
        raise ValueError("Input file is empty.")
    if len(data) % MESSAGE_SIZE:
        raise ValueError(
            f"File length {len(data)} is not divisible by {MESSAGE_SIZE}; "
            "this tool expects a concatenated RSP-550 program dump."
        )
    if not data.startswith(bytes([0xF0, 0x41])):
        raise ValueError("File does not start with a Roland SysEx message (F0 41).")
    messages = []
    for n in range(len(data) // MESSAGE_SIZE):
        msg = bytearray(data[n*MESSAGE_SIZE:(n+1)*MESSAGE_SIZE])
        if msg[0] != 0xF0 or msg[1] != 0x41 or msg[3] != 0x38 or msg[4] != 0x12 or msg[105] != 0xF7:
            raise ValueError(f"Message {n+1} does not match RSP-550 DT1 framing.")
        expected = checksum_for(msg)
        ok = (msg[104] == expected and (sum(msg[5:8]) + sum(msg[8:105])) % 128 == 0)
        if require_valid_checksums and not ok:
            raise ValueError(
                f"Message {n+1} checksum invalid (stored {msg[104]:02X}, expected {expected:02X}). "
                "Fix the source dump or inspect it with a hex editor before editing."
            )
        messages.append(msg)
    return messages


def program_name(message: bytearray) -> str:
    return bytes(message[8:24]).decode("ascii", errors="replace").rstrip()


def algorithm_id(message: bytearray) -> int:
    return message[8 + 0x11]


def value_for(payload: bytearray, offset: int, width: int) -> int:
    if offset < 0 or offset >= PAYLOAD_SIZE or width not in (1, 2) or offset + width > PAYLOAD_SIZE:
        raise ValueError(f"Data offset/width is outside payload (0x00–0x5F): offset={offset:#x}, width={width}")
    if width == 1:
        return payload[offset]
    return payload[offset] + (payload[offset+1] << 7)


def set_value_in_payload(payload: bytearray, offset: int, width: int, value: int):
    if offset < 0 or offset >= PAYLOAD_SIZE or width not in (1, 2) or offset + width > PAYLOAD_SIZE:
        raise ValueError(f"Data offset/width is outside payload (0x00–0x5F): offset={offset:#x}, width={width}")
    limit = 0x7F if width == 1 else 0x3FFF
    if not 0 <= value <= limit:
        raise ValueError(f"Value must be between 0 and {limit} for width={width}.")
    if width == 1:
        payload[offset] = value
    else:
        payload[offset] = value & 0x7F
        payload[offset+1] = (value >> 7) & 0x7F


def rebuild_message(message: bytearray) -> bytearray:
    message[CHECKSUM_INDEX] = checksum_for(message)
    return message


def write_output(messages, output_path: Path):
    combined = b"".join(bytes(rebuild_message(m)) for m in messages)
    parsed = parse_messages(combined, require_valid_checksums=True)
    if len(parsed) != len(messages):
        raise RuntimeError("Internal verification failed: message count changed.")
    output_path.write_bytes(combined)
    print(f"Wrote {output_path} ({len(combined)} bytes; {len(parsed)} messages; checksums verified).")


def load_source(path: str):
    p = Path(path)
    data = p.read_bytes()
    return p, parse_messages(data, require_valid_checksums=True)


def ensure_distinct_paths(input_path: Path, output_arg: str) -> Path:
    out = Path(output_arg)
    if input_path.resolve() == out.resolve():
        raise ValueError("Choose a different output path so the original file remains unchanged.")
    return out


def cmd_inspect(args):
    p, messages = load_source(args.input)
    numbers = [args.program] if args.program else range(1, len(messages)+1)
    print(f"File: {p}")
    print(f"Bytes: {p.stat().st_size}; messages: {len(messages)}; all checksums valid.")
    print("Program | Address     | Alg | Algorithm                  | Stored name")
    print("-"*96)
    for n in numbers:
        if n < 1 or n > len(messages):
            raise ValueError(f"Program must be 1..{len(messages)}.")
        m = messages[n-1]
        alg = algorithm_id(m)
        address = " ".join(f"{v:02X}" for v in m[5:8])
        print(f"{n:7d} | {address:11s} | {alg:3d} | {ALGORITHM_NAMES.get(alg, 'Unknown'):26s} | {program_name(m)}")


def cmd_show(args):
    p, messages = load_source(args.input)
    if args.program < 1 or args.program > len(messages):
        raise ValueError(f"Program must be 1..{len(messages)}.")
    m = messages[args.program-1]
    payload = bytearray(m[8:104])
    alg = payload[0x11]
    print(f"Program {args.program}: {program_name(m)}")
    print(f"Memory address: {' '.join(f'{v:02X}' for v in m[5:8])}")
    print(f"Algorithm {alg}: {ALGORITHM_NAMES.get(alg, 'Unknown')}")
    print(f"Checksum: {m[104]:02X} (valid)")
    print()
    print("Parameter                  Offset       Raw bytes     Count  Allowed range / scale                     Readable interpretation")
    print("-"*150)
    seen = set()
    for base in PARAMS.get(alg, []):
        d = metadata_for_parameter(alg, base)
        offset, width = int(d["offset"]), int(d["width"])
        raw = payload[offset:offset+width]
        value = value_for(payload, offset, width)
        offset_str = f"{offset:#04x}" if width == 1 else f"{offset:#04x}-{offset+1:#04x}"
        lo, hi = d.get("min_raw"), d.get("max_raw")
        unit = d.get("unit_or_scale", "")
        allowed = f"{lo}–{hi}" if lo is not None and hi is not None else "not mapped"
        if unit:
            allowed = f"{allowed} {unit}"[:40]
        interpretation = readable_value(d, value)
        print(f"{d['name'][:26]:26s} {offset_str:12s} {' '.join(f'{b:02X}' for b in raw):12s} {value:5d}  {allowed:40s} {interpretation}")
        seen.update(range(offset, offset+width))
    print()
    print(f"Raw bytes not named by this parameter map: {len(set(range(0x14,0x46)) - seen)} algorithm-region byte positions.")
    print("Use the workbook's Payload Bytes sheet to inspect every byte, including bytes not named above.")


def cmd_edit(args, edit_kind):
    input_path, messages = load_source(args.input)
    output_path = ensure_distinct_paths(input_path, args.output)
    if args.program < 1 or args.program > len(messages):
        raise ValueError(f"Program must be 1..{len(messages)}.")
    m = messages[args.program-1]
    payload = bytearray(m[8:104])
    old_name = program_name(m)
    old_alg = algorithm_id(m)

    if edit_kind == "byte":
        off, val = args.offset, args.value
        if off < 0 or off >= PAYLOAD_SIZE:
            raise ValueError("Offset must be 0x00–0x5F within the data payload.")
        if not 0 <= val <= 0x7F:
            raise ValueError("SysEx data value must be 0–127.")
        payload[off] = val
        print(f"Program {args.program} ({old_name}), data[{off:#04x}]: updated raw byte to {val:02X}.")
    elif edit_kind == "value":
        off, width, val = args.offset, args.width, args.value
        old_val = value_for(payload, off, width)
        set_value_in_payload(payload, off, width, val)
        print(f"Program {args.program} ({old_name}), data[{off:#04x}] width {width}: {old_val} -> {val}.")
    elif edit_kind == "param":
        matches = [d for d in PARAMS.get(old_alg, []) if d["name"].casefold() == args.parameter.casefold()]
        if not matches:
            known = ", ".join(d["name"] for d in PARAMS.get(old_alg, []))
            raise ValueError(
                f"Parameter {args.parameter!r} not found for algorithm {old_alg} ({ALGORITHM_NAMES.get(old_alg)}). "
                f"Known mapped parameters: {known}"
            )
        if len(matches) > 1:
            raise ValueError(f"Parameter name {args.parameter!r} is ambiguous; use set-value with an explicit offset.")
        d = metadata_for_parameter(old_alg, matches[0])
        off, width = int(d["offset"]), int(d["width"])
        lo, hi = d.get("min_raw"), d.get("max_raw")
        if lo is not None and hi is not None and not (int(lo) <= args.value <= int(hi)):
            raise ValueError(f"{d['name']} raw count must be within the documented range {lo}–{hi}; received {args.value}.")
        old_val = value_for(payload, off, width)
        set_value_in_payload(payload, off, width, args.value)
        print(f"Program {args.program} ({old_name}), {d['name']} at {off:#04x}: {old_val} -> {args.value}.")
        print("Note: value is the raw encoded parameter count; it has not been converted to display units.")
    elif edit_kind == "rename":
        try:
            encoded = args.name.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("Patch names must use ASCII characters in this utility.")
        if len(encoded) > 16:
            raise ValueError("RSP-550 program names are limited to 16 bytes.")
        payload[0:16] = encoded.ljust(16, b" ")
        payload[0x10] = 0
        print(f"Program {args.program}: renamed {old_name!r} -> {args.name!r}.")
    m[8:104] = payload
    rebuild_message(m)
    write_output(messages, output_path)


def build_parser():
    parser = argparse.ArgumentParser(description="Inspect and safely edit Roland RSP-550 SysEx program dumps.")
    sub = parser.add_subparsers(dest="command", required=True)

    insp = sub.add_parser("inspect", help="List all stored programs and validate checksums.")
    insp.add_argument("input")
    insp.add_argument("--program", type=int, help="Show only this program number.")
    insp.set_defaults(func=cmd_inspect)

    show = sub.add_parser("show", help="Show mapped parameter values for one program.")
    show.add_argument("input")
    show.add_argument("--program", required=True, type=int)
    show.set_defaults(func=cmd_show)

    sb = sub.add_parser("set-byte", help="Set a raw 7-bit data byte by payload offset.")
    sb.add_argument("input"); sb.add_argument("output")
    sb.add_argument("--program", required=True, type=int)
    sb.add_argument("--offset", required=True, type=lambda x: int(x, 0))
    sb.add_argument("--value", required=True, type=lambda x: int(x, 0))
    sb.set_defaults(func=lambda a: cmd_edit(a, "byte"))

    sv = sub.add_parser("set-value", help="Set a raw encoded value at an explicit payload offset.")
    sv.add_argument("input"); sv.add_argument("output")
    sv.add_argument("--program", required=True, type=int)
    sv.add_argument("--offset", required=True, type=lambda x: int(x, 0))
    sv.add_argument("--width", required=True, type=int, choices=[1,2])
    sv.add_argument("--value", required=True, type=lambda x: int(x, 0))
    sv.set_defaults(func=lambda a: cmd_edit(a, "value"))

    sp = sub.add_parser("set-param", help="Set a named parameter when it exists in the included address map.")
    sp.add_argument("input"); sp.add_argument("output")
    sp.add_argument("--program", required=True, type=int)
    sp.add_argument("--parameter", required=True)
    sp.add_argument("--value", required=True, type=lambda x: int(x, 0))
    sp.set_defaults(func=lambda a: cmd_edit(a, "param"))

    rn = sub.add_parser("rename", help="Change a program name (up to 16 ASCII bytes).")
    rn.add_argument("input"); rn.add_argument("output")
    rn.add_argument("--program", required=True, type=int)
    rn.add_argument("--name", required=True)
    rn.set_defaults(func=lambda a: cmd_edit(a, "rename"))
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
