# atlas-engine-notebooks

[marimo](https://marimo.io) notebooks for the engines on [Atlas](https://platform.mothquantum.com), Moth Quantum's platform. Each notebook runs an engine through the public Moth API and explains what it does. Atlas reads these notebooks to render each engine's **Notebook** page, and **Fork** on that page gives you your own copy of the same file.

| engine | notebook | saved run |
|---|---|---|
| `blur-v1` | [`blur/blur_notebook.py`](blur/blur_notebook.py) | [`blur/outputs/blur_notebook.ipynb`](blur/outputs/blur_notebook.ipynb) |

## Run a notebook

You need a Moth API key from the Atlas **API keys** page. Keys are read from the environment only; nothing in this repo contains one.

```bash
pip install -r requirements.txt
export MOTH_API_KEY=...
marimo edit blur/blur_notebook.py
```

Or open it straight from GitHub, with its dependencies installed into an isolated environment:

```bash
marimo edit --sandbox https://raw.githubusercontent.com/moth-quantum/atlas-engine-notebooks/main/blur/blur_notebook.py
```

Nothing is submitted until you press a run button.

| variable | default | purpose |
|---|---|---|
| `MOTH_API_KEY` | none | API key (required to run jobs) |
| `MOTH_API_BASE` | `https://api.mothquantum.com` | point at a staging API or a mock |
| `MOTH_AUTORUN` | unset | `1` runs every cell without pressing buttons, for headless runs (e.g. `marimo export ipynb --include-outputs`) |

## Add an engine

Once per clone, install the commit hook (`pre-commit` is in `requirements.txt`):

```bash
pre-commit install
```

1. **Copy and write.** Copy [`templates/engine_notebook.py`](templates/engine_notebook.py) to `<engine>/<engine>_notebook.py`, put any sample inputs beside it, and fill in every `TODO`; [`blur/blur_notebook.py`](blur/blur_notebook.py) is a finished example. Present the demo however you like with marimo's controls, images and layouts.
2. **Run and save.** In `marimo edit`, with your own `MOTH_API_KEY`, run every cell, press each run button, then save. marimo keeps the run, with its outputs, in `<engine>/__marimo__/`.
3. **Commit.** Commit the notebook, plus a short `<engine>/README.md` and a row in the table above, and open a pull request. The hook publishes your saved run to `<engine>/outputs/<engine>_notebook.ipynb`; the first time, it stops the commit and asks you to `git add` that file and commit again.

CI checks every pull request without an API key: the generated client is up to date, `marimo check` passes, and the published run is complete, matches the notebook, and has no links to your editor. If you change the notebook, run it and save again before committing. Without the hook, publish by hand with `python scripts/snapshot.py <engine>`. To check before you push:

```bash
python scripts/check_runs.py <engine>
```

## How the notebooks are built

- **Shared helpers.** [`client.py`](client.py) defines `upload`, `submit`, `wait` and `download`. `scripts/sync_client.py` copies it into each notebook's hidden `with app.setup` block (`# cell: client`), so every notebook runs on its own. It's a recommended start, not a requirement: use the helpers, or call the Moth API your own way. In a notebook that keeps the generated block, don't edit it by hand; it provides only those helpers and `AUTORUN`, so import everything else your cells use in the notebook's `setup` cell.
- **Saved run.** With `auto_download=["ipynb"]`, the marimo editor writes the notebook and its outputs to `<engine>/__marimo__/<engine>_notebook.ipynb` on every save (git-ignored). `scripts/snapshot.py`, run by the commit hook, refuses an incomplete or stale run and publishes it to `<engine>/outputs/<engine>_notebook.ipynb` without the HTML that only works in the editor, so GitHub and Atlas show every image and nothing re-runs to render. Don't edit the published file; `scripts/check_runs.py` checks it in CI.
- **No secrets.** No credentials, tokens or private hostnames in any file.

## Notebook format

CI requires only two things: the file's location (1) and an up-to-date saved run (9). Everything else is the recommended format: the template follows it, Atlas's **Notebook** page reads best with it, and it keeps the notebooks consistent for readers.

1. **File.** `<engine>/<engine>_notebook.py`, a plain marimo file with a PEP 723 dependency header, `app_title` set to the engine's display name and `auto_download=["ipynb"]`.
2. **API client (optional).** The template's hidden `with app.setup` block (`# cell: client`), generated from `client.py`, defines `upload`, `submit`, `wait`, `download` and `AUTORUN`, and its `engine` cell shows how to call the API with them. Keep it, or replace it with your own calls.
3. **Cell ids (recommended).** Start each `@app.cell` body with `# cell: <id>`, using lowercase letters, digits and `-`. Atlas uses them to tell cells apart, so keep them unique and stable once published.
4. **Standard cells**, in this order: `setup` (imports), `intro`, `try-md`, the engine cell, inputs, `params`, `run`, `parameters`, `how`, `experiments-md` and the experiments, `questions`. Engine-specific helper cells (Blur's `display-helpers`) go just before the cell that first uses them, with their code hidden. Each experiment is a `<name>-md` text cell, a `<name>-params` cell (values and run button) and a `<name>` result cell.
5. **Markdown.** A markdown cell is a single `mo.md(r"""…""")` call. No title line, since the page already has one; sections are `##`, subsections `###`. Formulas use `$…$` and `$$…$$`.
6. **Parameters.** `params` is a `mo.ui.dictionary` keyed by the engine's parameter names, one control each, next to the run button. `run` sends `params.value` as it is, and the `parameters` cell documents each one (type, default, effect).
7. **Questions.** `mo.md("## Questions")` plus `mo.accordion({...})` of `"question": "answer"` string pairs.
8. **No surprise jobs.** Nothing calls the API until a run button is pressed (`mo.stop(not (button.value or AUTORUN), …)`), and reader-facing text stays about the science and the results.
9. **Saved run.** `<engine>/outputs/<engine>_notebook.ipynb` is committed with every change to the notebook, complete and matching its code (see "Saved run").

## License

MIT — see [LICENSE](LICENSE).
