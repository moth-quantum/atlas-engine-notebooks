# Blur

| Notebook | Engine | What it does |
|---|---|---|
| `blur_notebook.ipynb` | Blur Image (`blur-staging`) | Runs Moth's Quantum Blur on a sample image and walks through strength, reach, gate style and masking. |
| `teleblur_notebook.ipynb` | Teleblur (`telablur-staging`) | Morphs a source image into a target image and sweeps the strength. |
| `blur_midi_notebook.ipynb` | Blur MIDI (`blur-midi-staging`) | Blurs a MIDI file's piano roll and walks through strength, reach, the note gate and masking. |

- `cat.png`: the 256 × 256 sample the Blur notebook and the Atlas showcase use.
- `image1.png`, `image2.png`: the 256 × 256 Teleblur source and target.
- `phrase.mid`: an original 8-bar phrase (melody and bass, 100 bpm) made for these notebooks.

Related: the engine's [QuantumBlur](https://github.com/qiskit-community/QuantumBlur) origins.
