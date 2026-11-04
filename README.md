# atlas-engine-notebooks

[marimo](https://marimo.io) notebooks for the engines on [Atlas](https://platform.mothquantum.com), Moth Quantum's platform. Each notebook runs an engine through the public Moth API and explains what it does. Atlas reads these notebooks to render each engine's **Notebook** page, and **Fork** on that page gives you your own copy of the same file.

| engine | notebook | static notebook |
|---|---|---|
| `blur-v1` | [`blur/blur_notebook.py`](blur/blur_notebook.py) | [`blur/outputs/blur_notebook.ipynb`](blur/outputs/blur_notebook.ipynb) |
| `coin-toss-v1` | [`coin_toss/coin_toss_notebook.py`](coin_toss/coin_toss_notebook.py) | [`coin_toss/outputs/coin_toss_notebook.ipynb`](coin_toss/outputs/coin_toss_notebook.ipynb) |

## Run a notebook

You need a Moth API key from the Atlas **API keys** page. Keys are read from the environment only; nothing in this repo contains one.

```bash
pip install -r requirements.txt
export MOTH_API_KEY=...
marimo edit blur/blur_notebook.py
```

To try the engine without the code, open the app view instead: controls and results only.

```bash
marimo run blur/blur_notebook.py
```

Or open it straight from GitHub, with its dependencies installed into an isolated environment (needs [uv](https://docs.astral.sh/uv/)):

```bash
marimo edit --sandbox https://raw.githubusercontent.com/moth-quantum/atlas-engine-notebooks/main/blur/blur_notebook.py
```

Nothing is submitted until you press a run button.

| variable | default | purpose |
|---|---|---|
| `MOTH_API_KEY` | none | API key (required to run jobs) |
| `MOTH_API_BASE` | `https://api.mothquantum.com` | point at a staging API or a mock |

## Write a notebook for your engine

Start from the template, add a working example and a few experiments, then run and save it in marimo. Readers can view your results on GitHub and Atlas, or fork the notebook to explore it themselves.

### Set up once

After installing the repository's dependencies (see [Run a notebook](#run-a-notebook)), enable the commit hook:

```bash
pre-commit install
```

The hook generates a renderable `.ipynb` of your saved results for GitHub and Atlas, and includes it in your commit.

### Create your notebook

Pick the template for your kind of engine, copy it into your engine's folder, and put any sample inputs beside it. Fill in the `TODO`s and add what your engine needs.

| template | input | output shown as |
|---|---|---|
| [`1_core_engine`](templates/1_core_engine.py) | parameters | JSON, and a table for the sweep |
| [`2_image_engine`](templates/2_image_engine.py) | an image + parameters | a before/after slider, and a gallery for the sweep |
| [`3_audio_engine`](templates/3_audio_engine.py) | audio + parameters | before and after players |
| [`4_asset_engine`](templates/4_asset_engine.py) | parameters | a download button, and a preview tab per file |
| [`5_generative_engine`](templates/5_generative_engine.py) | an example to train on, then parameters to generate | the trained model to download, and the generated sequence |

```bash
mkdir <engine> && cp templates/<n>_<kind>_engine.py <engine>/<engine>_notebook.py
```

`<engine>` is the engine's name in snake_case without its version, e.g. `deep_fryer` for `deep-fryer-v1` (see [Notebook format](#notebook-format)).

The [Blur notebook](blur/blur_notebook.py) is a finished image engine notebook.

### Write, run and save

Explain what your engine does, expose its parameters, and include a few experiments that show their effects.

```bash
marimo edit <engine>/<engine>_notebook.py
```

Run every cell, press each run button, then save with Cmd/Ctrl+S. Pressing a button doesn't trigger marimo's autosave, so save after the last one. API jobs use your own Atlas API key (`MOTH_API_KEY`).

### Submit your contribution

Stage your notebook, sample inputs, a short `<engine>/README.md` and a row in the engine table above. Commit and open a pull request.

The hook checks your saved results and adds the renderable `.ipynb` to the commit automatically. If a cell needs attention, it tells you which one: fix it in marimo, save, and commit again. CI runs the same checks on every pull request.

Not using the hook? Build the `.ipynb` yourself before committing:

```bash
git add <engine>/<engine>_notebook.py && python scripts/build_ipynb.py <engine>
```

## Notebook format

CI requires only two things: the file's location (1) and an up-to-date static notebook (9). Everything else is the recommended format: the template follows it, Atlas's **Notebook** page reads best with it, and it keeps the notebooks consistent for readers.

1. **File.** `<engine>/<engine>_notebook.py`, where `<engine>` is the engine's name in snake_case without its version: `blur-v1` → `blur/blur_notebook.py`, `deep-fryer-v1` → `deep_fryer/deep_fryer_notebook.py`. Engines that work as a pair share one folder named after the family (`qrc-train-v2` and `qrc-gen-v2` → `qrc/qrc_notebook.py`). It's a plain marimo file with a PEP 723 dependency header (in `--sandbox` mode marimo adds packages to it for you when you install them from the editor), `app_title` set to the engine's display name and `auto_download=["ipynb"]`.
2. **API client (optional).** The template's hidden `with app.setup` block (`# cell: client`) defines `upload`, `submit`, `wait` and `download`, and its `engine` cell shows how to call the API with them. Keep it, or call the API your own way. The block is generated from [`client.py`](client.py) by `scripts/sync_client.py`, so edit `client.py`, not the block. It provides only those helpers: import everything else in the regular `# cell: setup` cell.
3. **Cell ids (recommended).** Start each `@app.cell` body with `# cell: <id>`, using lowercase letters, digits and `-`. Atlas uses them to tell cells apart, so keep them unique and stable once merged. marimo can also name a cell by its function (`def params(...)`), but Atlas reads the `# cell:` comment, so use that.
4. **Standard cells**, in this order: `setup` (imports), `intro`, `try-md`, the engine cell, inputs, `params`, `run`, `parameters`, `how`, `experiments-md` and the experiments, `questions`. Engine-specific helper cells (Blur's `display-helpers`) go just before the cell that first uses them, with their code hidden (`@app.cell(hide_code=True)`). Each experiment is a `<name>-md` text cell, a `<name>-params` cell (values and run button) and a `<name>` result cell.
5. **Markdown.** A markdown cell is a single `mo.md(r"""…""")` call. No title line, since the page already has one; sections are `##`, subsections `###`. Formulas use `$…$` and `$$…$$`.
6. **Parameters.** `params` is a `mo.ui.dictionary` keyed by the engine's parameter names, one control each, next to the run button. `run` sends `params.value` as it is, and the `parameters` cell documents each one (type, default, effect).
7. **Questions.** `mo.md("## Questions")` plus `mo.accordion({...})` of `"question": "answer"` string pairs.
8. **No surprise jobs.** Nothing calls the API until a run button is pressed (`mo.stop(not button.value, …)`), and reader-facing text stays about the science and the results.
9. **Static notebook.** `<engine>/outputs/<engine>_notebook.ipynb` is committed with every change to the notebook. `scripts/build_ipynb.py` builds it from your saved run (which marimo writes to `<engine>/__marimo__/` on every save, git-ignored): complete, matching the code, and without the HTML that only works in the editor, so GitHub and Atlas show every image without re-running anything. Don't edit it by hand.
10. **No secrets.** No credentials, tokens or private hostnames in any file.

## License

MIT — see [LICENSE](LICENSE).
