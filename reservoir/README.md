# Reservoir

No core engine yet.

| Notebook | Engine | What it does |
|---|---|---|
| `reservoir_audio_notebook.ipynb` | Reservoir Audio (`qrc-audio-staging`; the API names it QRC Audio) | Cuts a chord loop into bars, learns their order with a quantum reservoir and generates new progressions, then walks through variation, training quality and chunk length. |
| `reservoir_midi_notebook.ipynb` | Reservoir MIDI (`qrc-midi-staging`; the API names it QRC MIDI) | Learns a MIDI phrase with a quantum reservoir and generates new arrangements, then walks through variation, training quality and looping. |

- `loop.wav`: 8 bars at 96 bpm (Am F C G Dm F E Am; mono, 16-bit / 44.1 kHz), built from Moth's QEcho sample pack.
- `phrase.mid`: an original 8-bar phrase (melody and bass, 100 bpm) made for these notebooks.
