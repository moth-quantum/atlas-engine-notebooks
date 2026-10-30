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

Each notebook carries its own generated copy of the shared helpers from [`client.py`](client.py) in a hidden setup cell, so it also runs on its own. If the sample image isn't next to the notebook it is fetched from this repo.

Or open it straight from GitHub without cloning. `--sandbox` installs the dependencies listed in the notebook's header into an isolated environment:

```bash
marimo edit --sandbox https://raw.githubusercontent.com/moth-quantum/atlas-engine-notebooks/main/blur/blur_notebook.py
```

Press **Run Blur** to submit one job. Each experiment (strength, reach and style, mask) has its own run button, and its sweep values are plain constants in the cell above it. Nothing is submitted until you press a button.

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
- Shared helpers: [`client.py`](client.py) (`upload`, `submit`, `wait`, `download`; needs only `requests`) is the source of truth. `scripts/sync_client.py` copies it into each notebook's hidden `with app.setup` cell (plus `AUTORUN`) and adds a `helpers` cell listing them; `--check` exits 1 if a notebook is stale. Don't edit those cells by hand, and since setup names are global, don't re-import `os`, `time`, `requests`, ... in other cells. Start a new notebook from [`templates/engine_notebook.py`](templates/engine_notebook.py).
- The API client in each notebook follows the Moth wire contract as Atlas uses it: `POST /api/v1/assets` (JSON `filename`/`content_type`/`size_bytes`) → `asset_id` + presigned `upload`, `PUT` the bytes there, then `POST /api/v1/assets/<id>/complete`; `POST /api/v1/engines/<id>/process` → `job_id`; poll `GET /api/v1/jobs/<id>/status`; `GET /api/v1/jobs/<id>/result` → `outputs[]` with `slot` and a presigned `url`.
- No credentials, no tokens, no private hostnames in any file. `marimo check <file>` must pass.

## License

MIT — see [LICENSE](LICENSE).
