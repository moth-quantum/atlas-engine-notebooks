"""Engine-agnostic Moth API helpers shared by the Atlas engine notebooks.

    from atlas_helpers import upload, submit, wait, download

    job_id = submit("blur-v1", {"strength": 0.5}, {"image": upload(data, "cat.png")})
    wait(job_id)
    out = download(job_id)

Credentials come from the environment only. Atlas injects MOTH_API_KEY into a forked
notebook; locally, export a key created on the Atlas "API keys" page.
"""

import hashlib
import mimetypes
import os
import time

import requests

__all__ = ["upload", "submit", "wait", "download"]

_s = requests.Session()
_s.headers.update({"User-Agent": "atlas-engine-notebooks", "Accept": "application/json"})


def api(method, path, **kw):
    # Env is read per call, so a key exported after import still takes effect.
    base = os.environ.get("MOTH_API_BASE", "https://api.mothquantum.com").rstrip("/")
    key = os.environ.get("MOTH_API_KEY", "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    r = _s.request(method, f"{base}{path}", headers=headers, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
    return r


_uploaded = {}


def upload(data, name, content_type=None):
    """Upload once per distinct file (create, PUT to the presigned URL, complete); returns its asset_id.
    content_type defaults to a guess from the filename."""
    content_type = content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
    key = hashlib.sha256(data).hexdigest()
    if key not in _uploaded:
        created = api("POST", "/api/v1/assets", json={"filename": name, "content_type": content_type, "size_bytes": len(data)}).json()
        up = created["upload"]
        r = requests.request(up.get("method", "PUT"), up["url"], data=data, headers=up["headers"], timeout=60)  # presigned: no bearer header
        if r.status_code >= 400:
            raise RuntimeError(f"upload {created['asset_id']} -> {r.status_code}: {r.text[:300]}")
        _uploaded[key] = api("POST", f"/api/v1/assets/{created['asset_id']}/complete").json()["asset_id"]
    return _uploaded[key]


def submit(engine_id, params, input_files=None):
    """Start a job; returns its job_id. input_files maps slot -> asset_id."""
    body = {"params": params, **({"input_files": input_files} if input_files else {})}
    return api("POST", f"/api/v1/engines/{engine_id}/process", json=body).json()["job_id"]


def wait(job_id, interval=1.5):
    """Poll until the job completes; raises if it fails or is cancelled."""
    while True:
        job = api("GET", f"/api/v1/jobs/{job_id}/status").json()
        if job["status"] == "completed":
            return
        if job["status"] in ("failed", "cancelled"):
            raise RuntimeError(f"job {job_id} {job['status']}: {job.get('error')}")
        time.sleep(interval)


def download(job_id, slot="result"):
    """Bytes of the output in `slot` (or the first output), or the inline JSON result for engines
    that produce no file."""
    res = api("GET", f"/api/v1/jobs/{job_id}/result").json()
    outputs = res.get("outputs") or []
    out = next((o for o in outputs if o.get("slot") == slot), outputs[0] if outputs else None)
    if out is None:
        if res.get("result") is None:
            raise RuntimeError(f"job {job_id} finished without an output")
        return res["result"]
    url = out.get("url") or api("GET", f"/api/v1/assets/{out['output_asset_id']}/download").json()["download_url"]
    return requests.get(url, timeout=60).content  # presigned: sent without the bearer header
