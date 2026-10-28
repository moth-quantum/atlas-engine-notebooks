import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="Blur")


@app.cell
def _():
    # cell: setup
    import hashlib
    import io
    import os
    import time

    import marimo as mo
    import numpy as np
    import requests
    from PIL import Image

    # Credentials come from the environment only. Atlas injects MOTH_API_KEY into a forked
    # notebook; locally, export a key created on the Atlas "API keys" page.
    API_BASE = os.environ.get("MOTH_API_BASE", "https://api.mothquantum.com").rstrip("/")
    API_KEY = os.environ.get("MOTH_API_KEY", "")
    AUTORUN = os.environ.get("MOTH_AUTORUN") == "1"  # headless exports: run every cell without pressing buttons
    ENGINE_ID = "blur-v1"
    REPO_RAW = "https://raw.githubusercontent.com/moth-quantum/atlas-engine-notebooks/main/blur"

    s = requests.Session()
    s.headers.update({"User-Agent": "atlas-engine-notebooks/blur", "Accept": "application/json"})
    if API_KEY:
        s.headers["Authorization"] = f"Bearer {API_KEY}"

    def api(method, path, **kw):
        r = s.request(method, f"{API_BASE}{path}", timeout=60, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r

    _uploaded = {}

    def upload(data, name):
        """Upload once per distinct file (create, PUT to the presigned URL, complete); returns its asset_id."""
        key = hashlib.sha256(data).hexdigest()
        if key not in _uploaded:
            created = api("POST", "/api/v1/assets", json={"filename": name, "content_type": "image/png", "size_bytes": len(data)}).json()
            up = created["upload"]
            r = requests.request(up.get("method", "PUT"), up["url"], data=data, headers=up["headers"], timeout=60)  # presigned: no bearer header
            if r.status_code >= 400:
                raise RuntimeError(f"upload {created['asset_id']} -> {r.status_code}: {r.text[:300]}")
            _uploaded[key] = api("POST", f"/api/v1/assets/{created['asset_id']}/complete").json()["asset_id"]
        return _uploaded[key]

    def blur(params, image, mask=None):
        """Run one Blur job: upload, submit, poll, download. Returns (float RGB array in [0, 1], seconds)."""
        t0 = time.perf_counter()
        input_files = {"image": upload(image, "image.png")}
        if mask is not None:
            input_files["mask"] = upload(mask, "mask.png")
        job_id = api("POST", f"/api/v1/engines/{ENGINE_ID}/process", json={"input_files": input_files, "params": params}).json()["job_id"]
        while True:
            job = api("GET", f"/api/v1/jobs/{job_id}/status").json()
            if job["status"] == "completed":
                break
            if job["status"] in ("failed", "cancelled"):
                raise RuntimeError(f"job {job_id} {job['status']}: {job.get('error')}")
            time.sleep(1.5)
        outputs = api("GET", f"/api/v1/jobs/{job_id}/result").json().get("outputs") or []
        out = next((o for o in outputs if o.get("slot") == "result"), outputs[0] if outputs else None)
        if out is None:
            raise RuntimeError(f"job {job_id} finished without an output")
        data = requests.get(out["url"], timeout=60).content  # presigned: sent without the bearer header
        return as_float(Image.open(io.BytesIO(data))), time.perf_counter() - t0

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

    if not API_KEY:
        mo.output.replace(mo.callout(mo.md(
            "`MOTH_API_KEY` is not set, so the cells that call the engine will fail. "
            "Create a key on the Atlas **API keys** page, export it, and restart the kernel."), kind="warn"))
    return AUTORUN, Image, REPO_RAW, as_float, blur, io, mo, np, os, png, requests, row


@app.cell
def _(Image, REPO_RAW, as_float, io, mo, np, os, requests):
    # cell: image
    # The sample ships next to this file; when the notebook is opened from a URL it is fetched from the repo.
    IMAGE = "cat.png"
    src = open(IMAGE, "rb").read() if os.path.exists(IMAGE) else requests.get(f"{REPO_RAW}/{IMAGE}", timeout=60).content
    img_in = Image.open(io.BytesIO(src))
    a_in = as_float(img_in)
    W, H = img_in.size
    qubits = int(np.ceil(np.log2(W))) + int(np.ceil(np.log2(H)))
    mo.vstack([mo.image(src=src, width=256), mo.md(f"`{IMAGE}` · {W}×{H} {img_in.mode} → {qubits} qubits per channel")])
    return H, W, a_in, src


@app.cell
def _(mo):
    # cell: params
    # The engine's Params schema (all optional). Change a control, then press Run.
    strength = mo.ui.slider(0, 1, step=0.05, value=0.5, label="Strength")  # 0..1 rotation scale; 0 = identity
    style = mo.ui.radio(options={"RX · spread": "rx", "RY · edges": "ry"}, value="RX · spread", label="Gate style")
    reach = mo.ui.slider(0, 1, step=0.05, value=0.0, label="Reach")  # 0 = local angles, 1 = every qubit turns equally
    size = mo.ui.slider(8, 1024, step=8, value=1024, label="Size")  # pixel budget per pass -> 2*ceil(log2 size) qubits
    downscale = mo.ui.checkbox(value=True, label="Downscale large regions")  # over budget: shrink (on) or tile (off)
    run = mo.ui.run_button(label="Run Blur")
    sweeps = mo.ui.checkbox(value=False, label="Also run the sweeps below (12 more jobs)")
    mo.vstack([strength, style, reach, size, downscale, mo.hstack([run, sweeps], justify="start", gap=2)])
    return downscale, reach, run, size, strength, style, sweeps


@app.cell
def _(AUTORUN, a_in, blur, downscale, mo, np, reach, row, run, size, src, strength, style):
    # cell: run
    PARAMS = {"strength": strength.value, "style": style.value, "reach": reach.value, "size": size.value, "downscale": downscale.value}
    mo.stop(not (run.value or AUTORUN), mo.md("Press **Run Blur** to submit a job with the parameters above."))
    a_out, t = blur(PARAMS, src)
    diff = np.abs(a_out - a_in)
    mo.vstack([
        mo.md(f"`{PARAMS}` · {t:.1f} s · mean |out − in| = {diff.mean():.3f}"),
        row({"input": a_in, f"{PARAMS['style']} · strength {PARAMS['strength']} · reach {PARAMS['reach']}": a_out,
             "|out − in|": diff.mean(-1) / max(diff.max(), 1e-6)}),
    ])
    return (PARAMS,)


@app.cell
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

    ## Strength

    $\xi$ scales every angle. At 0 the round trip is exact; the echoes grow with it up to the schema's limit of 1 (past that the rotations would start to undo themselves, which is why the engine stops there).
    """)
    return


@app.cell
def _(AUTORUN, PARAMS, a_in, blur, mo, np, row, src, sweeps):
    # cell: strength
    mo.stop(not (sweeps.value or AUTORUN), mo.md("Tick **Also run the sweeps** above to run this cell (5 jobs)."))
    outs = {k: blur({**PARAMS, "style": "rx", "reach": 0.0, "strength": k}, src)[0] for k in (0.0, 0.25, 0.5, 0.75, 1.0)}
    diffs = {k: round(float(np.abs(o - a_in).mean()), 3) for k, o in outs.items()}
    mo.vstack([mo.md("**rx · reach 0** — label shows mean |out − in|"), row({f"strength {k} · {diffs[k]}": o for k, o in outs.items()}, width=170)])
    return


@app.cell
def _(mo):
    # cell: reach-md
    mo.md(r"""
    ## Reach and style

    `reach` lifts the locality: at 0 the angle on each qubit is weighted by the brightness it separates, at 1 every qubit turns by the same $\pi\xi$ and echoes land anywhere on the canvas. `ry` keeps the same angles (with $\xi = \text{strength}^2$) but its interference terms cancel instead of spreading, so weight collects at a few pixels and smooth areas go dark.
    """)
    return


@app.cell
def _(AUTORUN, PARAMS, a_in, blur, mo, row, src, sweeps):
    # cell: reach
    mo.stop(not (sweeps.value or AUTORUN), mo.md("Tick **Also run the sweeps** above to run this cell (6 jobs)."))
    rows = []
    for st in ("rx", "ry"):
        panels = {"input": a_in}
        for r in (0.0, 0.5, 1.0):
            o = blur({**PARAMS, "style": st, "reach": r, "strength": 0.5}, src)[0]
            panels[f"{st} · reach {r} · mean {o.mean():.2f}"] = o
        rows.append(row(panels, width=170))
    mo.vstack([mo.md(f"**strength 0.5** · input mean brightness {a_in.mean():.2f}"), *rows])
    return


@app.cell
def _(mo):
    # cell: mask-md
    mo.md(r"""
    ## Mask

    A feathered disc: 1 inside, a soft ramp, 0 outside. The engine blurs the disc's bounding box as its own state and blends by mask intensity, so pixels outside the mask must come back untouched and the edge must be a gradient, not a seam.
    """)
    return


@app.cell
def _(AUTORUN, H, PARAMS, W, a_in, blur, mo, np, png, row, src, sweeps):
    # cell: mask
    mo.stop(not (sweeps.value or AUTORUN), mo.md("Tick **Also run the sweeps** above to run this cell (1 job)."))
    yy, xx = np.mgrid[0:H, 0:W]
    soft = np.clip(1.6 - np.hypot(xx - W / 2, yy - H / 2) / (0.28 * min(W, H)), 0, 1)
    a_m, t_mask = blur({**PARAMS, "strength": 0.8}, src, mask=png(soft))
    d = np.abs(a_m - a_in).mean(-1)
    outside = d[soft == 0].max()
    verdict = "outside the mask untouched ✓" if outside < 1 / 255 else "**outside the mask changed — the blend contract is broken**"
    mo.vstack([
        mo.md(f"{t_mask:.1f} s · max change outside mask {outside:.4f} · mean change inside {d[soft == 1].mean():.3f} · {verdict}"),
        row({"input": a_in, "mask": soft, "rx · strength 0.8 · masked": a_m, "|out − in|": d / max(d.max(), 1e-6)}),
    ])
    return


@app.cell
def _(mo):
    # cell: contract
    mo.md(r"""
    ## What you send, what comes back

    | you send | the engine does |
    |---|---|
    | `image` (PNG / JPEG / WebP / TIFF / BMP, any mode) | one statevector per RGB channel per region; alpha passed through; same format and size back |
    | `mask`, or none | connected regions of the mask (after a small-noise bin and min-region filter); else the alpha channel; else the whole canvas |
    | `strength`, `style`, `reach` | the per-qubit angles above |
    | `size`, `downscale` | the qubit budget: a region over budget is downscaled or tiled per region, never the whole image |
    """)
    return


@app.cell
def _(mo):
    # cell: questions
    mo.vstack([mo.md("## Questions"), mo.accordion({
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
