#!/usr/bin/env python3
"""Publish each engine notebook's saved run as the file Atlas and GitHub render. The pre-commit hook runs it.

    python scripts/snapshot.py              # every engine
    python scripts/snapshot.py blur         # one engine

Reads <engine>/__marimo__/<engine>_notebook.ipynb, which marimo writes on save (auto_download=["ipynb"]), and writes
<engine>/outputs/<engine>_notebook.ipynb. marimo stores each output as a PNG picture plus, for some cells, HTML whose
images only work in the live editor (./@file/...); that HTML is dropped so every viewer shows the picture.

Refuses a run that is incomplete or older than the notebook (see check_runs.py), and leaves the published file alone.
An engine with no saved run on this machine is skipped, so the hook doesn't block commits that only touch other files.
"""

import json
import os
import subprocess
import sys

from check_runs import ROOT, check, notebooks, published_run, saved_run

failed = False
for notebook in notebooks(sys.argv[1:]):
    src, dst = saved_run(notebook), published_run(notebook)
    if not src.exists():
        continue
    problems = check(notebook, src)
    if problems:
        print(f"✗ {src.relative_to(ROOT)} isn't a complete, current run, so {dst.relative_to(ROOT)} was not written:")
        for p in problems:
            print(f"    {p}")
        failed = True
        continue
    nb = json.loads(src.read_text())
    for cell in nb["cells"]:
        for out in cell.get("outputs", []):
            if "image/png" in out.get("data", {}):
                out["data"].pop("text/html", None)
    banner = f"> **Generated** from [`{notebook.name}`](../{notebook.name}) by `scripts/snapshot.py`: don't edit this file."
    nb["cells"].insert(0, {"cell_type": "markdown", "id": "generated-banner", "metadata": {}, "source": banner})
    text = json.dumps(nb, indent=1, ensure_ascii=False) + "\n"
    if not dst.exists() or dst.read_text() != text:
        dst.parent.mkdir(exist_ok=True)
        dst.write_text(text)
        print(f"wrote {dst.relative_to(ROOT)}")
    # Under the pre-commit hook, the commit must carry this exact file: stop until it's staged.
    rel = dst.relative_to(ROOT).as_posix()
    staged = subprocess.run(["git", "show", f":{rel}"], cwd=ROOT, capture_output=True, text=True)
    if os.environ.get("PRE_COMMIT") and (staged.returncode != 0 or staged.stdout != text):
        print(f"✗ {rel} isn't staged as written: run `git add {rel}` and commit again.")
        failed = True
sys.exit(1 if failed else 0)
