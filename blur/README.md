# Blur (`blur-v1`)

`blur_notebook.py` — a marimo notebook that runs Moth's Quantum Blur engine on a sample image and walks through strength, reach, gate style and masking. Open it with `marimo edit blur_notebook.py` (set `MOTH_API_KEY` first) or from GitHub as described in the [root README](../README.md).

- `cat.png` — the 256 × 256 sample the notebook and the Atlas showcase use.
- `outputs/` — images from a saved run of this notebook, as shown on the Atlas Notebook page until it is regenerated with `scripts/export.sh blur`:
  `strength-{0,0.25,0.5,0.75,1}.webp` (rx, reach 0), `{rx,ry}-reach-{0,0.5,1}.webp` (strength 0.5), `mask.webp`, `masked.webp`, `masked-diff.webp`.

Related: the engine's [QuantumBlur](https://github.com/qiskit-community/QuantumBlur) origins.
