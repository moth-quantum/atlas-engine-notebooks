#!/usr/bin/env python3
"""Check each engine notebook's published run (the file Atlas and GitHub render). Runs in CI; needs no API key.

    python scripts/check_runs.py            # every <engine>/<engine>_notebook.py
    python scripts/check_runs.py blur       # one engine

The published run is <engine>/outputs/<engine>_notebook.ipynb: the run marimo saved in __marimo__/ after the author
ran the notebook with their own key, cleaned by scripts/snapshot.py (the pre-commit hook runs it). It fails when:

- the published run is missing, or still holds HTML that only works in the author's editor (./@file/ links);
- the run failed: a cell raised an error (an API error included);
- the run is incomplete: a cell that displays something has no output, or still shows its "Press **Run …**" message;
- the run is stale: a cell's code or a markdown cell differs from the notebook, so it was edited after the run was saved.
"""

import ast
import json
import re
import sys
import textwrap
from pathlib import Path

from marimo._ast.parse import parse_notebook

ROOT = Path(__file__).resolve().parent.parent
MARKER = re.compile(r"\s*# cell: (\S+)")
MARKDOWN = re.compile(r'\s*(?:# cell: \S+\s*\n)?\s*mo\.md\(r?"""(.*?)"""\)\s*', re.S)
BANNER = "generated-banner"  # the markdown cell snapshot.py adds at the top of the published run
FIX = "In the editor, run every cell and press each run button, then save and commit again."


def notebooks(engines):
    paths = [ROOT / e / f"{e}_notebook.py" for e in engines] if engines else sorted(
        p for p in ROOT.glob("*/*_notebook.py") if p.parent.name != "templates")
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.exists()]
    if missing:
        sys.exit(f"no such notebook: {', '.join(missing)}")
    return paths


def saved_run(notebook):
    return notebook.parent / "__marimo__" / f"{notebook.stem}.ipynb"


def published_run(notebook):
    return notebook.parent / "outputs" / f"{notebook.stem}.ipynb"


def cell_id(code):
    m = MARKER.match(code)
    return m.group(1) if m else None


def shows_output(code):
    # A cell displays something when its last statement is an expression (marimo shows that value).
    try:
        body = ast.parse(code).body
    except SyntaxError:
        return False
    return bool(body) and isinstance(body[-1], ast.Expr)


def not_run(outputs):
    # The run buttons' mo.stop messages all read "Press **…**" (see the template).
    return re.search(r"Press (\*\*|<strong>)", json.dumps([o.get("data", {}) for o in outputs])) is not None


def check(notebook, run):
    """Problems with `run` (a saved or published .ipynb) as the run of `notebook`; empty when it's fine."""
    cells = parse_notebook(notebook.read_text()).cells
    if not run.exists():
        return [f"no run at {run.relative_to(ROOT)}. {FIX}"]
    saved = json.loads(run.read_text())["cells"]
    problems = []

    # Code cells are compared in order, so `# cell:` ids are optional; they only make the messages clearer.
    code = [c.code for c in cells if not MARKDOWN.fullmatch(c.code)]
    saved_code = [("".join(c["source"]), c.get("outputs", [])) for c in saved if c["cell_type"] == "code"]
    for i, source in enumerate(code, 1):
        label = cell_id(source) or f"code cell {i}"
        if i > len(saved_code):
            problems.append(f"{label}: not in the saved run (added after it was saved)")
        elif saved_code[i - 1][0] != source:
            problems.append(f"{label}: changed since the run was saved")
        elif any(o.get("output_type") == "error" for o in saved_code[i - 1][1]):
            problems.append(f"{label}: raised an error in the saved run")
        elif shows_output(source) and not saved_code[i - 1][1]:
            problems.append(f"{label}: no output in the saved run")
        elif not_run(saved_code[i - 1][1]):
            problems.append(f"{label}: its run button wasn't pressed before saving")
    if len(saved_code) > len(code):
        problems.append(f"the saved run has {len(saved_code) - len(code)} code cell(s) the notebook no longer has")

    markdown = [textwrap.dedent(MARKDOWN.fullmatch(c.code).group(1)).strip() for c in cells if MARKDOWN.fullmatch(c.code)]
    saved_markdown = ["".join(c["source"]).strip() for c in saved if c["cell_type"] == "markdown" and c.get("id") != BANNER]
    if markdown != saved_markdown:
        problems.append("markdown text changed since the run was saved")

    if problems:
        problems.append(FIX)
    return problems


def main():
    failed = False
    for notebook in notebooks(sys.argv[1:]):
        run = published_run(notebook)
        problems = check(notebook, run)
        if not problems and "./@file/" in run.read_text():
            problems = [f"{run.relative_to(ROOT)} has links to the author's editor; run `python scripts/snapshot.py {notebook.parent.name}`"]
        print(f"{'✗' if problems else '✓'} {notebook.relative_to(ROOT)}")
        for p in problems:
            print(f"    {p}")
        failed |= bool(problems)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
