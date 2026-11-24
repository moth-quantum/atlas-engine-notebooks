# atlas-engine-notebooks

Jupyter notebooks for the engines on [Atlas](https://platform.mothquantum.com), Moth Quantum's platform. Each notebook runs an engine with the [`moth-atlas`](https://pypi.org/project/moth-atlas/) Python client and explains what it does. Atlas renders each engine's **Notebook** page from these files.

New to the SDK? Start with [`sdk-quickstart.ipynb`](sdk-quickstart.ipynb), a generic tour: install, run an engine, pass params and files, assets, browse engines.

Notebooks are grouped the way Atlas groups engines: each family has a **core engine** that works on plain numbers, and **media engines** that apply it to one kind of file. Every notebook calls its engine through one line in its setup cell, `ENGINE = "...-staging"`; change that line to run it on another deployment (e.g. the `-v1` production ID).

| family | engine | role | notebook |
|---|---|---|---|
| Blur | `blur-core-staging` | core | [`blur_core/blur_core_notebook.ipynb`](blur_core/blur_core_notebook.ipynb) |
| | `blur-staging` | Blur Image | [`blur/blur_notebook.ipynb`](blur/blur_notebook.ipynb) |
| | `telablur-staging` | Teleblur | [`telablur/telablur_notebook.ipynb`](telablur/telablur_notebook.ipynb) |
| | `blur-midi-staging` | Blur MIDI | [`blur_midi/blur_midi_notebook.ipynb`](blur_midi/blur_midi_notebook.ipynb) |
| Tessa | `tessa-image-staging` | Tessa Image | [`tessa_image/tessa_image_notebook.ipynb`](tessa_image/tessa_image_notebook.ipynb) |
| Echo | `otoc-echo-staging` | core | [`otoc_echo/otoc_echo_notebook.ipynb`](otoc_echo/otoc_echo_notebook.ipynb) |
| | `retrocausal-echo-staging` | Echo Audio | [`retrocausal_echo/retrocausal_echo_notebook.ipynb`](retrocausal_echo/retrocausal_echo_notebook.ipynb) |
| Labyrinth | `graph-staging` | core | [`graph/graph_notebook.ipynb`](graph/graph_notebook.ipynb) |
| | `labyrinth-staging` | Labyrinth Level | [`labyrinth/labyrinth_notebook.ipynb`](labyrinth/labyrinth_notebook.ipynb) |
| Reservoir | `qrc-audio-staging` | Reservoir Audio | [`qrc_audio/qrc_audio_notebook.ipynb`](qrc_audio/qrc_audio_notebook.ipynb) |
| | `qrc-midi-staging` | Reservoir MIDI | [`qrc_midi/qrc_midi_notebook.ipynb`](qrc_midi/qrc_midi_notebook.ipynb) |
| Prism | `entanglement-shader-staging` | Prism Shader | [`entanglement_shader/entanglement_shader_notebook.ipynb`](entanglement_shader/entanglement_shader_notebook.ipynb) |
| Entropy | `comet-qrng-staging` | core | [`comet_qrng/comet_qrng_notebook.ipynb`](comet_qrng/comet_qrng_notebook.ipynb) |
| | `coin-toss-staging` | Coin Toss | [`coin_toss/coin_toss_notebook.ipynb`](coin_toss/coin_toss_notebook.ipynb) |

Folders are still one per engine; moving them into one folder per family is tracked in [#7](https://github.com/moth-quantum/atlas-engine-notebooks/issues/7).

## Run a notebook

You need a Moth API key from the Atlas **API keys** page. Set it as `MOTH_API_KEY`, or enter it when the notebook asks; it is never saved in the notebook. The `-staging` engines are served by the staging API: set `MOTH_API_BASE` to it (Atlas's own JupyterLab sets it for you).

```bash
pip install -r requirements.txt
export MOTH_API_KEY=... MOTH_API_BASE=...
jupyter lab blur/blur_notebook.ipynb
```

Each code cell that submits a job runs only when you run it.

To run notebooks top to bottom and save their outputs in place (what a pull request needs), use `run_notebooks.sh`: with no arguments it runs every engine notebook, or name folders to run only those. It stops a notebook at its first error and leaves the file unchanged.

```bash
./run_notebooks.sh                    # every engine notebook
./run_notebooks.sh otoc_echo labyrinth
```

## Write a notebook for your engine

Copy the template for your kind of engine into a folder named after the engine: its name in snake_case without its version, e.g. `coin_toss` for `coin-toss-v1`.

| template | input | output | finished example |
|---|---|---|---|
| [`1_core_engine`](templates/1_core_engine.ipynb) | parameters + arrays / JSON | JSON | [Coin Toss](coin_toss/coin_toss_notebook.ipynb) |
| [`2_image_engine`](templates/2_image_engine.ipynb) | an image + parameters | an image | [Blur](blur/blur_notebook.ipynb), [Teleblur](telablur/telablur_notebook.ipynb) (two images) |
| [`3_audio_engine`](templates/3_audio_engine.ipynb) | audio + parameters | audio | |
| [`4_asset_engine`](templates/4_asset_engine.ipynb) | parameters | a file to download | |
| [`5_generative_engine`](templates/5_generative_engine.ipynb) | an example to train on, then parameters to generate | the trained model, and what it generates | |

```bash
mkdir coin_toss && cp templates/1_core_engine.ipynb coin_toss/coin_toss_notebook.ipynb
```

Fill in every `TODO` from the engine's docs and put any sample inputs beside the notebook. Then run every cell with your own key and save, so the outputs are stored in the file. GitHub and Atlas show the notebook as saved.

Open a pull request with the notebook, its sample inputs, a short `<engine>/README.md` and a row in the engine table above.

## Notebook format

1. **File.** `<engine>/<engine>_notebook.ipynb`. Engines that work as a pair share one folder named after the family (`qrc-train-v2` and `qrc-gen-v2` → `qrc/qrc_notebook.ipynb`).
2. **Sections**, in this order: a `# <engine display name>` title and intro, `## Setup`, `## Try it`, `## Parameters` (each parameter's type, default and effect), `## How it works`, `## Experiments` (one `###` per experiment) and `## Questions`.
3. **API calls.** Use `moth_atlas`. **Try it** is one `client.jobs.run(...)` call, laid out like the example the engine's definition prints, with the params a reader should try, then the output next to the input. **Parameters** says what to expect from each; the engine's definition stays a commented-out `client.engines.get(...)`, since the engine page shows it. Experiments run with `quiet=True` and print each job's params.
4. **Saved outputs.** Commit the notebook after a complete run, with no error outputs.
5. **No secrets.** No credentials, tokens or private hostnames in any file. Keep the setup cell's key prompt: it reads `MOTH_API_KEY`, or asks for the key without saving it.

## License

MIT — see [LICENSE](LICENSE).
