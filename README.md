# atlas-engine-notebooks

[marimo](https://marimo.io) notebooks for the engines on [Atlas](https://platform.mothquantum.com), Moth Quantum's platform. Each notebook runs an engine through the public Moth API and explains what it does. Atlas reads these notebooks to render each engine's **Notebook** page, and **Fork** on that page gives you your own copy of the same file.

| engine | notebook | what it shows |
|---|---|---|
| `blur-v1` | [`blur/blur_notebook.py`](blur/blur_notebook.py) | one run, strength / reach / gate-style sweeps, masking, the I/O contract |

## Run it yourself

You need a Moth API key from the Atlas **API keys** page. Keys are read from the environment only; nothing in this repo ever contains one.

```bash
pip install -r requirements.txt
export MOTH_API_KEY=...          # from Atlas → API keys
marimo edit blur/blur_notebook.py
```

Or open it straight from GitHub without cloning. `--sandbox` installs the dependencies listed in the notebook's header, including `atlas_helpers`, into an isolated environment:

```bash
marimo edit --sandbox https://raw.githubusercontent.com/moth-quantum/atlas-engine-notebooks/main/blur/blur_notebook.py
```

The sample image is fetched from this repo when the notebook isn't run from a checkout.

Press **Run Blur** to submit one job; tick **Also run the sweeps** to run the parameter sweeps (12 more jobs). Nothing is submitted until you press the button.

## Headless run (what Atlas's export does)

`MOTH_AUTORUN=1` makes every cell run without pressing buttons, so the notebook can be executed and captured in CI:

```bash
MOTH_API_KEY=... scripts/export.sh blur
```

writes `blur/outputs/blur_notebook.ipynb` (code, markdown and outputs) and `blur/outputs/blur_notebook.html`.

## Environment

| variable | default | purpose |
|---|---|---|
| `MOTH_API_KEY` | — | bearer token for the Moth API (required to run jobs) |
| `MOTH_API_BASE` | `https://api.mothquantum.com` | API origin; point it at a mock or a staging API |
| `MOTH_AUTORUN` | unset | `1` runs every cell headlessly (no buttons) |

## Layout and conventions

- One folder per engine, named after the Atlas page slug: `<engine>/<engine>_notebook.py`, its sample inputs beside it, saved outputs under `<engine>/outputs/`.
- Every `@app.cell` starts with a `# cell: <id>` comment. Atlas uses these ids to match cells to its viewer; keep them stable.
- API calls go through [`atlas_helpers`](atlas_helpers/src/atlas_helpers/__init__.py) (`upload`, `submit`, `wait`, `download`), a small package in this repo. Each notebook lists it in its inline script header as `atlas-helpers @ git+https://github.com/moth-quantum/atlas-engine-notebooks@main#subdirectory=atlas_helpers`, so it installs even when the notebook is opened on its own; `requirements.txt` installs the local copy in editable mode. The helpers follow the Moth wire contract as Atlas uses it: `POST /api/v1/assets` (JSON `filename`/`content_type`/`size_bytes`) → `asset_id` + presigned `upload`, `PUT` the bytes there, then `POST /api/v1/assets/<id>/complete`; `POST /api/v1/engines/<id>/process` → `job_id`; poll `GET /api/v1/jobs/<id>/status`; `GET /api/v1/jobs/<id>/result` → `outputs[]` with `slot` and a presigned `url`.
- No credentials, no tokens, no private hostnames in any file. `marimo check <file>` must pass.

## License

MIT — see [LICENSE](LICENSE).
