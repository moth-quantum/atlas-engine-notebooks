#!/usr/bin/env python3
"""Build each engine notebook's static .ipynb, the file Atlas and GitHub render, from its saved run. The pre-commit hook runs it on every
commit, so authors don't need to; run it by hand to check a run before committing.

    python scripts/build_ipynb.py blur         # one engine: validate, write outputs/, git add
    python scripts/build_ipynb.py              # every engine with a saved run on this machine

Reads <engine>/__marimo__/<engine>_notebook.ipynb, which marimo writes on save (auto_download=["ipynb"]), and writes
<engine>/outputs/<engine>_notebook.ipynb. marimo stores each output as a PNG picture plus, for some cells, HTML whose
images only work in the live editor (./@file/...); that HTML is dropped so every viewer shows the picture.

Refuses a run that is incomplete, failed or older than the notebook (see check_runs.py), and leaves the static
.ipynb alone. An engine with no saved run on this machine is skipped; CI still checks it.

Staging is deliberate: git re-reads the index after pre-commit hooks run, so the static .ipynb joins the commit being
made. To keep source and outputs together, a notebook's .ipynb is built only when the file on disk is exactly what is
staged (else the saved run may belong to unstaged edits), and under the hook only notebooks staged in this commit are
built. pre-commit stashes unstaged edits before the hook runs, so there a run that belongs to them fails the
staleness check instead. scripts/test_build_ipynb.py covers these cases.
"""

import json
import os
import subprocess
import sys

from check_runs import ROOT, check, notebooks, static_ipynb, saved_run

HOOK = bool(os.environ.get("PRE_COMMIT"))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def build(src, notebook):
    nb = json.loads(src.read_text())
    for cell in nb["cells"]:
        for out in cell.get("outputs", []):
            if "image/png" in out.get("data", {}):
                out["data"].pop("text/html", None)
    banner = f"> **Generated** from [`{notebook.name}`](../{notebook.name}) by `scripts/build_ipynb.py`: don't edit this file."
    nb["cells"].insert(0, {"cell_type": "markdown", "id": "generated-banner", "metadata": {}, "source": banner})
    return json.dumps(nb, indent=1, ensure_ascii=False) + "\n"


targets = notebooks(sys.argv[1:])
if HOOK:
    staged = set(git("diff", "--cached", "--name-only").stdout.split())
    targets = [n for n in targets if n.relative_to(ROOT).as_posix() in staged]

failed = False
for notebook in targets:
    src, dst = saved_run(notebook), static_ipynb(notebook)
    rel, nb_rel = dst.relative_to(ROOT).as_posix(), notebook.relative_to(ROOT).as_posix()
    if not src.exists():
        continue
    index = git("show", f":{nb_rel}")
    if index.returncode != 0 or index.stdout != notebook.read_text():
        print(f"✗ {nb_rel} has changes that aren't staged, so {rel} was not written: the saved run may belong to them."
              f" Stage the notebook (`git add {nb_rel}`) or undo those changes, then try again.")
        failed = True
        continue
    problems = check(notebook, src)
    if problems:
        print(f"✗ {src.relative_to(ROOT)} isn't a complete, current run of the staged {nb_rel}, so {rel} was not written:")
        for p in problems:
            print(f"    {p}")
        if HOOK:
            print("    If the notebook has changes you didn't stage, the saved run belongs to them: stage them too, or"
                  " re-run the staged version.")
        failed = True
        continue
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(build(src, notebook))
    git("add", rel).check_returncode()
    print(f"✓ built and staged {rel}")
sys.exit(1 if failed else 0)
