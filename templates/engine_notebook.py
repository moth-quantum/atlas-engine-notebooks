# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo>=0.17",
#     "requests>=2.31",
#     # TODO: add the packages your own cells import
# ]
# ///

# Template for a new engine notebook: copy it to <engine>/<engine>_notebook.py and fill in every TODO.
# Finished example: blur/blur_notebook.py

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="TODO Engine name", auto_download=["ipynb"])

with app.setup(hide_code=True):
    # cell: client
    # Shared scaffolding, generated from client.py by scripts/sync_client.py: edit client.py, not this block.
    # Only the public helpers and AUTORUN are visible to other cells; import any module you use in your own cells.
    # Imported under private names so a notebook's setup cell exposes only the public helpers (and the module
    # names stay free for the notebook's own imports, as they would be with `from moth_atlas import ...`).
    import hashlib as _hashlib
    import mimetypes as _mimetypes
    import os as _os
    import time as _time
    from pathlib import Path as _Path

    import requests as _requests


    _session = _requests.Session()
    _session.headers["User-Agent"] = "atlas-engine-notebooks"


    def _call(method, path, **kw):
        # Env is read per call, so a key exported after import still takes effect.
        base = _os.environ.get("MOTH_API_BASE", "https://api.mothquantum.com").rstrip("/")
        key = _os.environ.get("MOTH_API_KEY", "")
        if not key:
            raise RuntimeError("MOTH_API_KEY is not set: create a key on the Atlas API keys page and export it")
        r = _session.request(method, f"{base}/api/v1{path}", headers={"Authorization": f"Bearer {key}"}, timeout=30, **kw)
        if r.status_code >= 400:  # keep the API's error body; raise_for_status() would drop it
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None


    def _presigned(method, url, **kw):
        # Presigned URLs carry their own signature: never send the API key to them (plain requests, not _session).
        r = _requests.request(method, url, timeout=60, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} presigned URL -> {r.status_code}: {r.text[:300]}")
        return r


    _uploaded = {}  # (sha256, content_type) -> asset_id, so re-running a cell doesn't re-upload


    def upload(file: str | _os.PathLike | bytes, content_type: str | None = None, filename: str | None = None) -> str:
        """Upload a file path or raw bytes; returns its asset id.

        content_type defaults to a guess from the filename; filename names uploaded bytes.
        Runs the three API steps: create, PUT to the presigned URL, complete."""
        if isinstance(file, (bytes, bytearray)):
            data, filename = bytes(file), filename or "file"
        else:
            data, filename = _Path(file).read_bytes(), filename or _Path(file).name
        content_type = content_type or _mimetypes.guess_type(filename)[0] or "application/octet-stream"
        key = (_hashlib.sha256(data).hexdigest(), content_type)
        if key not in _uploaded:
            asset = _call("POST", "/assets", json={"filename": filename, "content_type": content_type, "size_bytes": len(data)})
            up = asset["upload"]
            _presigned(up.get("method", "PUT"), up["url"], data=data, headers=up["headers"])
            _uploaded[key] = _call("POST", f"/assets/{asset['asset_id']}/complete")["asset_id"]
        return _uploaded[key]


    def submit(engine: str, params: dict, input_files: dict[str, str] | None = None) -> str:
        """Start a job on an engine; returns its job id. params is a dict of the engine's parameters; input_files is a dict mapping each input slot name to an asset id."""
        body = {"params": params, **({"input_files": input_files} if input_files else {})}
        return _call("POST", f"/engines/{engine}/process", json=body)["job_id"]


    def wait(job_id: str, interval: float = 1.5, timeout: float = 600, on_update=None) -> None:
        """Block until the job completes, checking every interval seconds; raises if it fails, is cancelled, or takes longer than timeout seconds.

        on_update(job) is called whenever the status changes, with the status response as a dict,
        e.g. on_update=lambda job: print(job["status"])."""
        deadline, last = _time.monotonic() + timeout, None
        while _time.monotonic() < deadline:
            job = _call("GET", f"/jobs/{job_id}/status")
            if on_update and job["status"] != last:
                on_update(job)
                last = job["status"]
            if job["status"] == "completed":
                return
            if job["status"] in ("failed", "cancelled"):
                raise RuntimeError(f"Job {job_id} {job['status']}: {job.get('error')}")
            _time.sleep(interval)
        raise TimeoutError(f"Job {job_id} did not finish in {timeout}s")


    def download(job_id: str, slot: str = "result") -> bytes | dict:
        """Return a finished job's output: the bytes of the file in slot (or the first output), or the inline JSON result (a dict) for engines that produce no file."""
        res = _call("GET", f"/jobs/{job_id}/result")
        outputs = res.get("outputs") or []
        out = next((o for o in outputs if o.get("slot") == slot), outputs[0] if outputs else None)
        if out is None:
            if res.get("result") is None:
                raise RuntimeError(f"Job {job_id} finished without an output")
            return res["result"]
        url = out.get("url") or _call("GET", f"/assets/{out['output_asset_id']}/download")["download_url"]
        return _presigned("GET", url).content

    # Headless exports: run every cell without pressing buttons. (Own line: marimo drops a trailing comment on save.)
    AUTORUN = _os.environ.get("MOTH_AUTORUN") == "1"


@app.cell
def _():
    # cell: setup
    # Import every module your cells use here; the hidden block at the top provides only the API helpers.
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    # cell: intro
    mo.md(r"""
    TODO: one or two sentences on what the engine does and what makes its output different.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: try-md
    mo.md(r"""
    ## Try it

    Pick an input and the parameters, then press **Run**.
    """)
    return


@app.cell
def _():
    # cell: engine
    # upload, submit, wait and download are the Moth API helpers from client.py, inlined in the hidden block at the top.
    ENGINE_ID = "TODO-v1"
    INPUT_SLOT = "TODO"  # the engine's input slot name

    def run_engine(params, file=None, filename=None):
        """Run one job: upload the input, submit, wait, download. Returns file bytes, or a dict for JSON results."""
        input_files = {INPUT_SLOT: upload(file, filename=filename)} if file else None
        job_id = submit(ENGINE_ID, params, input_files)
        wait(job_id)
        return download(job_id)

    return (run_engine,)


@app.cell
def _(mo):
    # cell: input
    # TODO: delete this cell, and its use below, if the engine takes no input file.
    input_file = mo.ui.file(kind="area", label="Drop an input file here")
    input_file
    return (input_file,)


@app.cell
def _(mo):
    # cell: params
    # TODO: one control per parameter, with the engine's ranges and defaults.
    example_param = mo.ui.slider(0, 1, step=0.05, value=0.5, label="TODO_param")
    run = mo.ui.run_button(label="Run")
    mo.vstack([example_param, run])
    return example_param, run


@app.cell
def _(example_param, input_file, mo, run, run_engine):
    # cell: run
    mo.stop(not (run.value or AUTORUN), mo.md("Press **Run** to see the result."))
    result = run_engine({"TODO_param": example_param.value}, input_file.contents(), input_file.name())
    mo.image(result)  # TODO: show the output the way that suits the engine, e.g. mo.audio, mo.json, a chart
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: parameters
    mo.md(r"""
    ## Parameters

    | name | type | default | what it does |
    |---|---|---|---|
    | `TODO` (input file) | TODO: accepted formats | required | TODO |
    | `TODO_param` | float, 0 to 1 | 0.5 | TODO |

    **Returns:** TODO: what comes back.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: how
    mo.md(r"""
    ## How it works

    TODO: the method in a few short paragraphs: what goes in, what the circuit does, how the output is read back.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: experiments-md
    mo.md(r"""
    ## Experiments

    Each experiment changes one parameter and keeps the others fixed. Press its button to run it.

    ### TODO_param

    TODO: what to look for as the value changes.
    """)
    return


@app.cell
def _(mo):
    # cell: sweep-params
    # Edit the values, then press the button: one job per value.
    SWEEP = (0.0, 0.5, 1.0)
    run_sweep = mo.ui.run_button(label=f"Run sweep ({len(SWEEP)} jobs)")
    run_sweep
    return SWEEP, run_sweep


@app.cell(hide_code=True)
def _(SWEEP, input_file, mo, run_engine, run_sweep):
    # cell: sweep
    mo.stop(not (run_sweep.value or AUTORUN), mo.md("Press **Run sweep** to compare the values above."))
    tiles = []
    for value in SWEEP:
        out = run_engine({"TODO_param": value}, input_file.contents(), input_file.name())
        tiles.append(mo.vstack([mo.image(out), mo.md(f"`TODO_param = {value}`")]))
    mo.hstack(tiles, wrap=True)
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: questions
    mo.vstack([mo.md("## Questions"), mo.accordion({
        "TODO: a question new users ask?": "TODO: a short answer.",
    })])
    return


if __name__ == "__main__":
    app.run()
