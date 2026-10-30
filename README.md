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
- API calls go through [`client.py`](client.py) (`upload`, `submit`, `wait`, `download`), shared by every notebook; it needs only `requests`. `client.py` is the source of truth: `scripts/sync_client.py` generates two identical cells in every notebook from it, the hidden `with app.setup` block (the client code plus `AUTORUN`, visible to every cell) and a `helpers` cell (a collapsed list of the helpers, plus a warning when `MOTH_API_KEY` is unset). A new notebook only needs an empty `with app.setup(hide_code=True):` block; the script fills it in and adds `helpers` after it. Since setup-cell names are global, notebook cells use `os`, `time`, `requests`, ... from it and must not import or define them again (`marimo check` catches clashes). After editing `client.py`, run `scripts/sync_client.py`; `scripts/sync_client.py --check` exits 1 if any notebook is stale (use it in CI). Don't edit the generated cells by hand. It follows the Moth wire contract as Atlas uses it: `POST /api/v1/assets` (JSON `filename`/`content_type`/`size_bytes`) → `asset_id` + presigned `upload`, `PUT` the bytes there, then `POST /api/v1/assets/<id>/complete`; `POST /api/v1/engines/<id>/process` → `job_id`; poll `GET /api/v1/jobs/<id>/status`; `GET /api/v1/jobs/<id>/result` → `outputs[]` with `slot` and a presigned `url`.
- No credentials, no tokens, no private hostnames in any file. `marimo check <file>` must pass.

## License

MIT — see [LICENSE](LICENSE).
