# atlas-engine-notebooks

[marimo](https://marimo.io) notebooks for the engines on [Atlas](https://platform.mothquantum.com), Moth Quantum's platform. Each notebook runs an engine through the public Moth API and explains what it does. Atlas reads these notebooks to render each engine's **Notebook** page, and **Fork** on that page gives you your own copy of the same file.

| engine | notebook | static preview |
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
| `MOTH_AUTORUN` | unset | `1` runs every cell without pressing buttons, for headless exports (`scripts/export.sh <engine>`) |

## Add an engine

Copy [`templates/engine_notebook.py`](templates/engine_notebook.py) to `<engine>/<engine>_notebook.py` and fill in every `TODO`; [`blur/blur_notebook.py`](blur/blur_notebook.py) is a finished example. Before opening a pull request, check that:

- [ ] the notebook is in its own folder, `<engine>/`, with any sample inputs beside it
- [ ] no `TODO` is left, and the header lists every package the notebook imports
- [ ] `marimo check <engine>/<engine>_notebook.py` and `python scripts/sync_client.py --check` both pass
- [ ] the static preview is refreshed: press every run button in the editor, save, then run `python scripts/snapshot.py <engine>`
- [ ] `<engine>/README.md` says in a few lines what the engine does, and the engine has a row in the table above

## How the notebooks are built

- **Shared helpers.** [`client.py`](client.py) defines `upload`, `submit`, `wait` and `download`. `scripts/sync_client.py` copies it into each notebook's hidden `with app.setup` block (`# cell: client`), so every notebook runs on its own; don't edit that block by hand. It provides only those helpers and `AUTORUN`, so import everything else your cells use in the notebook's `setup` cell.
- **Static preview.** With `auto_download=["ipynb"]`, the marimo editor saves the notebook with its outputs to `<engine>/__marimo__/` on every save. `scripts/snapshot.py` copies it to `<engine>/outputs/` for GitHub to render; don't edit that copy.
- **No secrets.** No credentials, tokens or private hostnames in any file.

## Notebook format

Atlas renders each engine's **Notebook** page from these files, so every notebook follows the same format. The template already does; keep it when you edit.

1. **File.** `<engine>/<engine>_notebook.py`, a plain marimo file with a PEP 723 dependency header, `app_title` set to the engine's display name and `auto_download=["ipynb"]`.
2. **Generated client.** One hidden `with app.setup` block (`# cell: client`), written by `scripts/sync_client.py`. It defines only `upload`, `submit`, `wait`, `download` and `AUTORUN`.
3. **Cell ids.** Every `@app.cell` body starts with `# cell: <id>`: lowercase letters, digits and `-`, unique, and kept stable once published.
4. **Standard cells**, in this order: `setup` (imports), `intro`, `try-md`, the engine cell, inputs, `params`, `run`, `parameters`, `how`, `experiments-md` and the experiments, `questions`. Engine-specific helper cells (Blur's `display-helpers`) go right after `setup`. Each experiment is a `<name>-params` cell (values and run button) followed by a `<name>` result cell.
5. **Markdown.** A markdown cell is a single `mo.md(r"""…""")` call. No title line, since the page already has one; sections are `##`, subsections `###`. Formulas use `$…$` and `$$…$$`.
6. **Parameters.** `params` holds one `mo.ui` control per engine parameter, plus the run button. `run` sends them as a dict of `"name": control.value` pairs, and the `parameters` cell documents each one (type, default, effect).
7. **Questions.** `mo.md("## Questions")` plus `mo.accordion({...})` of `"question": "answer"` string pairs.
8. **No surprise jobs.** Nothing calls the API until a run button is pressed (`mo.stop(not (button.value or AUTORUN), …)`), and reader-facing text stays about the science and the results.
9. **Saved outputs.** `<engine>/outputs/<engine>_notebook.ipynb` is the notebook's saved run (see "Static preview").

## License

MIT — see [LICENSE](LICENSE).
