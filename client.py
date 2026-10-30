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

__all__ = ["upload", "submit", "wait", "download"]

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

