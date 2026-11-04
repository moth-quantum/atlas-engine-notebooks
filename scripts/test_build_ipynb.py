#!/usr/bin/env python3
"""Check that the commit hook (scripts/build_ipynb.py) keeps each static .ipynb with the notebook source it belongs to.

    python scripts/test_build_ipynb.py

Builds a throwaway repo from this checkout's scripts and Blur, adds a second engine, installs the hook, and commits:
a full commit, a partial one (staged notebook A, unstaged edits B with B's run), an unrelated commit, two engines with
newer runs where only one is committed, a manual build with unstaged edits, and a run with an error. A saved run is
rebuilt from the static .ipynb, so no API key or editor is needed.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
ENV.pop("PRE_COMMIT", None)


def sh(*args, ok=True):
    r = subprocess.run(args, cwd=REPO, env=ENV, capture_output=True, text=True)
    if ok and r.returncode:
        sys.exit(f"{' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r


def commit(msg):
    return sh("git", "commit", "-qm", msg, ok=False).returncode == 0


def in_head(path):
    return sh("git", "show", "--name-only", "--format=", "HEAD").stdout.split().count(path) == 1


def head(path):
    return sh("git", "show", f"HEAD:{path}").stdout


def edit(engine, tag, notebook=True, run=True):
    """Change the first markdown sentence to end in `tag`, in the notebook and/or its saved run (as if re-run)."""
    nb, saved = REPO / engine / f"{engine}_notebook.py", REPO / engine / "__marimo__" / f"{engine}_notebook.ipynb"
    if notebook:
        nb.write_text(nb.read_text().replace(FIRST, FIRST + tag, 1))
    if run:
        data = json.loads(saved.read_text())
        cell = next(c for c in data["cells"] if c["cell_type"] == "markdown")
        cell["source"] = "".join(cell["source"]).replace(FIRST, FIRST + tag, 1)
        saved.write_text(json.dumps(data))


def restore(engine, **metadata):
    """Make the saved run match HEAD's static .ipynb again (optionally marked as a newer run of the same notebook)."""
    data = json.loads(head(f"{engine}/outputs/{engine}_notebook.ipynb"))
    data["cells"] = [c for c in data["cells"] if c.get("id") != "generated-banner"]
    data["metadata"].update(metadata)
    (REPO / engine / "__marimo__" / f"{engine}_notebook.ipynb").write_text(json.dumps(data))


def check(name, cond):
    print(f"{'✓' if cond else '✗'} {name}")
    if not cond:
        sys.exit(1)


REPO = Path(tempfile.mkdtemp())
try:
    for path in [".pre-commit-config.yaml", "scripts", "blur"]:
        (shutil.copytree if (SRC / path).is_dir() else shutil.copy)(SRC / path, REPO / path)
    shutil.rmtree(REPO / "blur" / "__marimo__", ignore_errors=True)
    # Second engine: a copy of Blur under another name.
    shutil.copytree(REPO / "blur", REPO / "two")
    for f in (REPO / "two").rglob("blur_notebook.*"):
        f.rename(f.with_name(f.name.replace("blur", "two")))
    # Saved runs, rebuilt from the static .ipynb files (drop the banner build_ipynb.py adds).
    for engine in ["blur", "two"]:
        data = json.loads((REPO / engine / "outputs" / f"{engine}_notebook.ipynb").read_text())
        data["cells"] = [c for c in data["cells"] if c.get("id") != "generated-banner"]
        (REPO / engine / "__marimo__").mkdir()
        (REPO / engine / "__marimo__" / f"{engine}_notebook.ipynb").write_text(json.dumps(data))
    first = next(c for c in data["cells"] if c["cell_type"] == "markdown")
    FIRST = "".join(first["source"]).split(".")[0]
    (REPO / ".gitignore").write_text("__marimo__/\n")
    (REPO / "notes.md").write_text("notes\n")
    sh("git", "init", "-q")
    sh("git", "add", "-A")
    sh("python", "scripts/build_ipynb.py")  # build both engines with the banner, as the hook would
    sh("git", "commit", "-qm", "base", "--no-verify")
    sh("pre-commit", "install")
    BLUR, TWO = "blur/outputs/blur_notebook.ipynb", "two/outputs/two_notebook.ipynb"

    edit("blur", " (A)")
    sh("git", "add", "blur/blur_notebook.py")
    check("full commit: passes and carries the new .ipynb", commit("A") and in_head(BLUR) and " (A)" in head(BLUR))

    edit("blur", " (B)")  # author runs B and stages it...
    sh("git", "add", "blur/blur_notebook.py")
    edit("blur", " (C)")  # ...then edits and runs C without staging: the saved run is a valid run of C
    check("partial commit (run belongs to unstaged edits): blocked", not commit("B"))
    check("partial commit: nothing committed", " (B)" not in head("blur/blur_notebook.py"))
    check("manual build with unstaged edits: refused, nothing staged",
          sh("python", "scripts/build_ipynb.py", "blur", ok=False).returncode == 1 and
          sh("git", "diff", "--cached", "--name-only").stdout.split() == ["blur/blur_notebook.py"])
    sh("git", "reset", "-q", "--hard")
    restore("blur")

    edit("two", " (D)")  # a newer run of an engine this commit doesn't touch, with unstaged edits
    (REPO / "notes.md").write_text("notes 2\n")
    sh("git", "add", "notes.md")
    check("unrelated commit: passes and touches no .ipynb",
          commit("notes") and sh("git", "show", "--name-only", "--format=", "HEAD").stdout.split() == ["notes.md"])

    sh("git", "checkout", "-q", "--", "two/two_notebook.py")
    restore("two", newer=True)  # two: a newer, valid run of an unchanged notebook
    edit("blur", " (E)")
    sh("git", "add", "blur/blur_notebook.py")
    check("two engines with newer runs, one committed: only that one is built",
          commit("E") and in_head(BLUR) and not in_head(TWO) and '"newer"' not in head(TWO))

    saved = REPO / "blur" / "__marimo__" / "blur_notebook.ipynb"
    data = json.loads(saved.read_text())
    cell = next(c for c in data["cells"] if c["cell_type"] == "code" and c.get("outputs"))
    cell["outputs"] = [{"output_type": "error", "ename": "HTTPError", "evalue": "401", "traceback": []}]
    saved.write_text(json.dumps(data))
    edit("blur", " (F)")
    sh("git", "add", "blur/blur_notebook.py")
    check("run with an error: blocked", not commit("F"))
finally:
    shutil.rmtree(REPO, ignore_errors=True)
