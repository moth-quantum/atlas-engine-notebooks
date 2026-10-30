# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo>=0.17",
#     "numpy>=1.26",
#     "pillow>=10",
#     "requests>=2.31",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Blur")

with app.setup(hide_code=True):
    # cell: setup
    # Shared scaffolding, generated from client.py by scripts/sync_client.py: edit client.py, not this block.
    # Everything defined here (the API helpers and their imports) is visible to every cell.
    import hashlib
    import mimetypes
    import os
    import time
    from pathlib import Path

    import requests


    _session = requests.Session()
    _session.headers["User-Agent"] = "atlas-engine-notebooks"


    def _call(method, path, **kw):
        # Env is read per call, so a key exported after import still takes effect.
        base = os.environ.get("MOTH_API_BASE", "https://api.mothquantum.com").rstrip("/")
        key = os.environ.get("MOTH_API_KEY", "")
        if not key:
            raise RuntimeError("MOTH_API_KEY is not set: create a key on the Atlas API keys page and export it")
        r = _session.request(method, f"{base}/api/v1{path}", headers={"Authorization": f"Bearer {key}"}, timeout=30, **kw)
        if r.status_code >= 400:  # keep the API's error body; raise_for_status() would drop it
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None


    def _presigned(method, url, **kw):
        # Presigned URLs carry their own signature: never send the API key to them (plain requests, not _session).
        r = requests.request(method, url, timeout=60, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} presigned URL -> {r.status_code}: {r.text[:300]}")
        return r


    _uploaded = {}  # (sha256, content_type) -> asset_id, so re-running a cell doesn't re-upload


    def upload(file: str | os.PathLike | bytes, content_type: str | None = None, filename: str | None = None) -> str:
        """Upload a file path or raw bytes; returns its asset id.

        content_type defaults to a guess from the filename; filename names uploaded bytes.
        Runs the three API steps: create, PUT to the presigned URL, complete."""
        if isinstance(file, (bytes, bytearray)):
            data, filename = bytes(file), filename or "file"
        else:
            data, filename = Path(file).read_bytes(), filename or Path(file).name
        content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        key = (hashlib.sha256(data).hexdigest(), content_type)
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
        deadline, last = time.monotonic() + timeout, None
        while time.monotonic() < deadline:
            job = _call("GET", f"/jobs/{job_id}/status")
            if on_update and job["status"] != last:
                on_update(job)
                last = job["status"]
            if job["status"] == "completed":
                return
            if job["status"] in ("failed", "cancelled"):
                raise RuntimeError(f"Job {job_id} {job['status']}: {job.get('error')}")
            time.sleep(interval)
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

    AUTORUN = os.environ.get("MOTH_AUTORUN") == "1"


@app.cell(hide_code=True)
def _(mo):
    # cell: helpers
    # Generated by scripts/sync_client.py. Lists the API helpers from their own signatures and docstrings.
    import inspect as _inspect

    _summary = lambda f: _inspect.getdoc(f).partition("\n\n")[0]  # docstring's first paragraph
    _docs = "\n".join(f"{f.__name__}{_inspect.signature(f)}\n    {_summary(f)}" for f in (upload, submit, wait, download))
    _helpers = mo.accordion({"API helpers (`upload, submit, wait, download`), defined in the hidden setup cell": mo.plain_text(_docs)})
    _missing_key = mo.callout(mo.md(
        "`MOTH_API_KEY` is not set, so the cells that call the engine will fail. "
        "Create a key on the Atlas **API keys** page, export it, and restart the kernel."), kind="warn")
    mo.vstack([_missing_key, _helpers]) if not os.environ.get("MOTH_API_KEY") else _helpers
    return


@app.cell
def _():
    # cell: imports
    # Blur's own imports. The hidden setup cell already provides the API helpers and the modules they use
    # (os, time, requests, ...), so those are not imported again here.
    import io

    import marimo as mo
    import numpy as np
    from PIL import Image

    return Image, io, mo, np


@app.cell
def _(Image, io, mo, np):
    # cell: display
    # Convert between images and float arrays, and lay out labelled image grids.
    def as_float(img):
        return np.asarray(img.convert("RGB"), float) / 255.0

    def png(arr):
        """Float array in [0, 1] (RGB or gray) -> PNG bytes."""
        buf = io.BytesIO()
        Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(buf, "PNG")
        return buf.getvalue()

    def panel(label, arr, width=220):
        return mo.vstack([mo.image(src=png(arr), width=width), mo.md(f"<small>{label}</small>")], align="center", gap=0)

    def row(panels, **kw):
        return mo.hstack([panel(k, v, **kw) for k, v in panels.items()], justify="start", gap=1, wrap=True)

    return as_float, png, row


@app.cell(hide_code=True)
def _(mo):
    # cell: intro
    mo.md(r"""
    # Blur

    Quantum Blur turns an image into a single quantum state, rotates every qubit once, and measures the state back into pixels. One gate moves amplitude between pixels that can be far apart, so instead of soft focus you get echoes and interference that no convolution kernel produces.

    This notebook calls the `blur-v1` engine through the Moth API: **Try it** runs it with your parameters, **How it works** explains the circuit, **Experiments** sweeps one parameter at a time, and **Reference** lists exactly what goes in and comes out.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: image-md
    mo.md(r"""
    ## Load an image

    The sample image ships next to this notebook. Point `IMAGE` at your own file to blur that instead.
    """)
    return


@app.cell
def _(Image, as_float, io, mo, np):
    # cell: image
    # The sample ships next to this file; if it is missing (notebook opened on its own) it is fetched from the repo.
    REPO_RAW = "https://raw.githubusercontent.com/moth-quantum/atlas-engine-notebooks/main/blur"
    IMAGE = "cat.png"
    sample = mo.notebook_dir() / IMAGE
    src = sample.read_bytes() if sample.exists() else requests.get(f"{REPO_RAW}/{IMAGE}", timeout=60).content
    img_in = Image.open(io.BytesIO(src))
    a_in = as_float(img_in)
    W, H = img_in.size
    qubits = int(np.ceil(np.log2(W))) + int(np.ceil(np.log2(H)))
    mo.vstack([mo.image(src=src, width=256), mo.md(f"`{IMAGE}` · {W}×{H} {img_in.mode} → {qubits} qubits per channel")])
    return H, W, a_in, src


@app.cell(hide_code=True)
def _(mo):
    # cell: blur-md
    mo.md(r"""
    ## Call the engine

    Every engine is called with the same four helpers: `upload` the inputs, `submit` a job, `wait` for it, `download` the output. What is specific to Blur is the engine id, its input slots (`image`, optional `mask`) and decoding the output image.
    """)
    return


@app.cell
def _(Image, as_float, io, mo):
    # cell: blur
    ENGINE_ID = "blur-v1"

    def blur(params, image, mask=None):
        """Run one Blur job. Returns (float RGB array in [0, 1], seconds)."""
        input_files = {"image": upload(image, filename="image.png")}
        if mask is not None:
            input_files["mask"] = upload(mask, filename="mask.png")
        t0 = time.perf_counter()
        job_id = submit(ENGINE_ID, params, input_files)
        with mo.status.spinner(title=f"Blur job {job_id}") as spinner:
            wait(job_id, on_update=lambda job: spinner.update(subtitle=job["status"]))
        data = download(job_id)
        return as_float(Image.open(io.BytesIO(data))), time.perf_counter() - t0

    return (blur,)


@app.cell(hide_code=True)
def _(mo):
    # cell: try-md
    mo.md(r"""
    ## Try it

    The engine's parameters, all optional. Change a control, then press **Run Blur** to submit one job.
    """)
    return


@app.cell
def _(mo):
    # cell: params
    strength = mo.ui.slider(0, 1, step=0.05, value=0.5, label="Strength")  # 0..1 rotation scale; 0 = identity
    style = mo.ui.radio(options={"RX · spread": "rx", "RY · edges": "ry"}, value="RX · spread", label="Gate style")
    reach = mo.ui.slider(0, 1, step=0.05, value=0.0, label="Reach")  # 0 = local angles, 1 = every qubit turns equally
    size = mo.ui.slider(8, 1024, step=8, value=1024, label="Size")  # pixel budget per pass -> 2*ceil(log2 size) qubits
    downscale = mo.ui.checkbox(value=True, label="Downscale large regions")  # over budget: shrink (on) or tile (off)
    run = mo.ui.run_button(label="Run Blur")
    mo.vstack([strength, style, reach, size, downscale, run])
    return downscale, reach, run, size, strength, style


@app.cell
def _(
    a_in,
    blur,
    downscale,
    mo,
    np,
    reach,
    row,
    run,
    size,
    src,
    strength,
    style,
):
    # cell: run
    mo.stop(not (run.value or AUTORUN), mo.md("Press **Run Blur** to submit a job with the parameters above."))
    PARAMS = {"strength": strength.value, "style": style.value, "reach": reach.value, "size": size.value, "downscale": downscale.value}
    a_out, t = blur(PARAMS, src)
    diff = np.abs(a_out - a_in)
    mo.vstack([
        mo.md(f"`{PARAMS}` · {t:.1f} s · mean |out − in| = {diff.mean():.3f}"),
        row({"input": a_in, f"{PARAMS['style']} · strength {PARAMS['strength']} · reach {PARAMS['reach']}": a_out,
             "|out − in|": diff.mean(-1) / max(diff.max(), 1e-6)}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: how
    mo.md(r"""
    ## How it works

    Quantum Blur has no convolution kernel. The image is encoded as a single quantum state, each qubit is rotated once, and the state is measured back into pixels. Because a single gate redistributes amplitude between pixels that may be far apart on the canvas, the output shows interference patterns rather than soft focus.

    **Encode.** Pixel $(x,y)$ with brightness $h$ maps to a basis state, Gray-coded per axis:

    $$|\psi\rangle \;\propto\; \sum_{x,y} \sqrt{h(x,y)}\;|g(x)\,g(y)\rangle, \qquad n = \lceil\log_2 W\rceil + \lceil\log_2 H\rceil \text{ qubits}$$

    **Rotate.** One `rx` (or `ry`) per qubit, with an image-dependent angle:

    $$\theta_q = \pi\,\xi\,\big[(1-\text{reach})\, r_q + \text{reach}\big], \qquad \xi = \text{strength} \;(\texttt{rx})\;\text{ or }\;\text{strength}^2 \;(\texttt{ry})$$

    where $r_q$ is the normalised brightness on neighbour pairs whose labels differ in qubit $q$.

    **Read back.** $h' = |\text{amp}|^2 / \max$, rescaled to the channel's original maximum. With a mask $m$, the output is $m\cdot\text{blurred} + (1-m)\cdot\text{original}$.
    """)
    return


@app.cell
def _(mo):
    # cell: experiments-md
    experiments = mo.ui.run_button(label="Run experiments (12 jobs)")
    mo.vstack([mo.md(r"""
    ## Experiments

    Each experiment sweeps one parameter with the others fixed, so you can see what it does on its own. Nothing is submitted until you press the button.
    """), experiments])
    return (experiments,)


@app.cell(hide_code=True)
def _(mo):
    # cell: strength-md
    mo.md(r"""
    ### Strength

    $\xi$ scales every angle. At 0 the round trip is exact; the echoes grow with it up to the schema's limit of 1 (past that the rotations would start to undo themselves, which is why the engine stops there).
    """)
    return


@app.cell
def _(a_in, blur, experiments, mo, np, row, src):
    # cell: strength
    mo.stop(not (experiments.value or AUTORUN), mo.md("Press **Run experiments** above to run this cell (5 jobs)."))
    outs = {k: blur({"style": "rx", "reach": 0.0, "strength": k}, src)[0] for k in (0.0, 0.25, 0.5, 0.75, 1.0)}
    diffs = {k: round(float(np.abs(o - a_in).mean()), 3) for k, o in outs.items()}
    mo.vstack([mo.md("**rx · reach 0** — label shows mean |out − in|"), row({f"strength {k} · {diffs[k]}": o for k, o in outs.items()}, width=170)])
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: reach-md
    mo.md(r"""
    ### Reach and style

    `reach` lifts the locality: at 0 the angle on each qubit is weighted by the brightness it separates, at 1 every qubit turns by the same $\pi\xi$ and echoes land anywhere on the canvas. `ry` keeps the same angles (with $\xi = \text{strength}^2$) but its interference terms cancel instead of spreading, so weight collects at a few pixels and smooth areas go dark.
    """)
    return


@app.cell
def _(a_in, blur, experiments, mo, row, src):
    # cell: reach
    mo.stop(not (experiments.value or AUTORUN), mo.md("Press **Run experiments** above to run this cell (6 jobs)."))
    rows = []
    for st in ("rx", "ry"):
        panels = {"input": a_in}
        for r in (0.0, 0.5, 1.0):
            o = blur({"style": st, "reach": r, "strength": 0.5}, src)[0]
            panels[f"{st} · reach {r} · mean {o.mean():.2f}"] = o
        rows.append(row(panels, width=170))
    mo.vstack([mo.md(f"**strength 0.5** · input mean brightness {a_in.mean():.2f}"), *rows])
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: mask-md
    mo.md(r"""
    ### Mask

    A feathered disc: 1 inside, a soft ramp, 0 outside. The engine blurs the disc's bounding box as its own state and blends by mask intensity, so pixels outside the mask must come back untouched and the edge must be a gradient, not a seam.
    """)
    return


@app.cell
def _(H, W, a_in, blur, experiments, mo, np, png, row, src):
    # cell: mask
    mo.stop(not (experiments.value or AUTORUN), mo.md("Press **Run experiments** above to run this cell (1 job)."))
    yy, xx = np.mgrid[0:H, 0:W]
    soft = np.clip(1.6 - np.hypot(xx - W / 2, yy - H / 2) / (0.28 * min(W, H)), 0, 1)
    a_m, t_mask = blur({"style": "rx", "reach": 0.0, "strength": 0.8}, src, mask=png(soft))
    d = np.abs(a_m - a_in).mean(-1)
    outside = d[soft == 0].max()
    verdict = "outside the mask untouched ✓" if outside < 1 / 255 else "**outside the mask changed — the blend contract is broken**"
    mo.vstack([
        mo.md(f"{t_mask:.1f} s · max change outside mask {outside:.4f} · mean change inside {d[soft == 1].mean():.3f} · {verdict}"),
        row({"input": a_in, "mask": soft, "rx · strength 0.8 · masked": a_m, "|out − in|": d / max(d.max(), 1e-6)}),
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: contract
    mo.md(r"""
    ## Reference

    ### What you send, what comes back

    | you send | the engine does |
    |---|---|
    | `image` (PNG / JPEG / WebP / TIFF / BMP, any mode) | one statevector per RGB channel per region; alpha passed through; same format and size back |
    | `mask`, or none | connected regions of the mask (after a small-noise bin and min-region filter); else the alpha channel; else the whole canvas |
    | `strength`, `style`, `reach` | the per-qubit angles above |
    | `size`, `downscale` | the qubit budget: a region over budget is downscaled or tiled per region, never the whole image |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # cell: questions
    mo.vstack([mo.md("### Questions"), mo.accordion({
        "Is this running on real quantum hardware?":
            "No. Blur runs on a classical statevector simulator, so jobs run on CPU or GPU. The circuits and the interference are real; the execution is emulated. That keeps results exact and repeatable with no shot noise. Real hardware would need very high connectivity and enough shots to rebuild the whole state, which is not yet practical at image scale.",
        "Why does it look different from a classical blur?":
            "A classical blur averages each pixel with a fixed neighbourhood. Blur has no kernel: one rotation per qubit mixes amplitude between every pixel at once, so the shape of the smear comes from the circuit, not a window. That is where the echo-like, non-local look comes from.",
        "How does image size affect run time?":
            "Qubits grow with the log of the image size (16 for 256 × 256, 20 for 1024 × 1024), but simulator memory and time grow exponentially with qubits. Regions over the qubit budget are downscaled or tiled, depending on `downscale`.",
        "What happens with colour images?":
            "Each of red, green and blue is blurred as its own state and the channels are recombined. The same technique was used on ILĀ's [Recurse album](https://infinite.mothquantum.com).",
        "Why does strength 0 round-trip exactly?":
            "Encoding normalises the state, which throws away absolute brightness. The engine keeps each channel's original maximum and restores it on read-back, so with no rotation the output equals the input.",
        "Where can I read more?":
            "The open-source [QuantumBlur repository](https://github.com/qiskit-community/QuantumBlur) walks through the underlying library.",
    })])
    return


if __name__ == "__main__":
    app.run()
