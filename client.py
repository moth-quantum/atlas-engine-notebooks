"""Engine-agnostic Moth API client shared by the Atlas engine notebooks.

    from client import upload, submit, wait, download

    asset_id = upload("cat.png")
    job_id = submit("blur-v1", {"strength": 0.5}, {"image": asset_id})
    wait(job_id)
    output = download(job_id)

Credentials come from the environment only: export MOTH_API_KEY, a key created on the Atlas
"API keys" page. MOTH_API_BASE points at staging or a mock.
"""

import hashlib
import mimetypes
import os
import time
from pathlib import Path

import requests

_session = requests.Session()
_session.headers["User-Agent"] = "atlas-engine-notebooks"


def call(method, path, **kw):
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


def upload(file, content_type=None, filename=None):
    """Upload a path or bytes (create, PUT to the presigned URL, complete); returns its asset_id.
    content_type defaults to a guess from the filename."""
    if isinstance(file, (bytes, bytearray)):
        data, filename = bytes(file), filename or "file"
    else:
        data, filename = Path(file).read_bytes(), filename or Path(file).name
    content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    key = (hashlib.sha256(data).hexdigest(), content_type)
    if key not in _uploaded:
        asset = call("POST", "/assets", json={"filename": filename, "content_type": content_type, "size_bytes": len(data)})
        up = asset["upload"]
        _presigned(up.get("method", "PUT"), up["url"], data=data, headers=up["headers"])
        _uploaded[key] = call("POST", f"/assets/{asset['asset_id']}/complete")["asset_id"]
    return _uploaded[key]


def submit(engine, params, input_files=None):
    """Start a job; returns its job_id. input_files maps the engine's input slots to asset_ids."""
    body = {"params": params, **({"input_files": input_files} if input_files else {})}
    return call("POST", f"/engines/{engine}/process", json=body)["job_id"]


def wait(job_id, interval=1.5, timeout=600):
    """Poll until the job completes; raises if it fails, is cancelled, or outlives timeout seconds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = call("GET", f"/jobs/{job_id}/status")
        if job["status"] == "completed":
            return
        if job["status"] in ("failed", "cancelled"):
            raise RuntimeError(f"Job {job_id} {job['status']}: {job.get('error')}")
        time.sleep(interval)
    raise TimeoutError(f"Job {job_id} did not finish in {timeout}s")


def download(job_id, slot="result"):
    """Bytes of the output in `slot` (or the first output), or the inline JSON result for engines
    that produce no file."""
    res = call("GET", f"/jobs/{job_id}/result")
    outputs = res.get("outputs") or []
    out = next((o for o in outputs if o.get("slot") == slot), outputs[0] if outputs else None)
    if out is None:
        if res.get("result") is None:
            raise RuntimeError(f"Job {job_id} finished without an output")
        return res["result"]
    url = out.get("url") or call("GET", f"/assets/{out['output_asset_id']}/download")["download_url"]
    return _presigned("GET", url).content
