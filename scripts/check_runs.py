#!/usr/bin/env python3
"""Check each engine notebook's committed saved run (the file Atlas renders). Runs in CI; needs no API key.

    python scripts/check_runs.py            # every <engine>/<engine>_notebook.py
    python scripts/check_runs.py blur       # one engine

The saved run is <engine>/__marimo__/<engine>_notebook.ipynb, written by marimo on save (auto_download=["ipynb"])
after the author ran the notebook with their own key. It fails when:

- a cell has no valid `# cell: <id>` marker (lowercase letters, digits and -), or an id is used twice;
- the saved run is missing;
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
VALID_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
MARKDOWN = re.compile(r'\s*# cell: \S+\s*\n\s*mo\.md\(r?"""(.*?)"""\)\s*', re.S)
FIX = "In the editor, run every cell and press each run button, then save and commit the saved run again."


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


def check(notebook):
    engine_dir, name = notebook.parent, notebook.stem
    cells = parse_notebook(notebook.read_text()).cells
    problems = []

    ids = [cell_id(c.code) for c in cells]
    for i, cid in enumerate(ids, 1):
        if cid is None:
            problems.append(f"cell {i} doesn't start with a `# cell: <id>` comment")
        elif not VALID_ID.fullmatch(cid):
            problems.append(f"cell id '{cid}' must use lowercase letters, digits and - only")
    problems += [f"cell id '{cid}' is used twice" for cid in sorted({i for i in ids if i and ids.count(i) > 1})]
    if problems:
        return problems

    run = engine_dir / "__marimo__" / f"{name}.ipynb"
    if not run.exists():
        return [f"no saved run at {run.relative_to(ROOT)}. {FIX}"]
    saved = json.loads(run.read_text())["cells"]

    code = {cell_id(c.code): c.code for c in cells if not MARKDOWN.fullmatch(c.code)}
    saved_code = {}
    for c in saved:
        if c["cell_type"] == "code":
            source = "".join(c["source"])
            saved_code[cell_id(source)] = (source, c.get("outputs", []))
    for cid, source in code.items():
        if cid not in saved_code:
            problems.append(f"{cid}: not in the saved run (added after it was saved)")
        elif saved_code[cid][0] != source:
            problems.append(f"{cid}: changed since the run was saved")
        elif shows_output(source) and not saved_code[cid][1]:
            problems.append(f"{cid}: no output in the saved run")
        elif not_run(saved_code[cid][1]):
            problems.append(f"{cid}: its run button wasn't pressed before saving")
    problems += [f"{cid}: in the saved run but no longer in the notebook" for cid in saved_code if cid not in code]

    markdown = [textwrap.dedent(MARKDOWN.fullmatch(c.code).group(1)).strip() for c in cells if MARKDOWN.fullmatch(c.code)]
    saved_markdown = ["".join(c["source"]).strip() for c in saved if c["cell_type"] == "markdown"]
    if markdown != saved_markdown:
        problems.append("markdown text changed since the run was saved")

    if problems:
        problems.append(FIX)
    return problems


def main():
    engines = sys.argv[1:]
    notebooks = [ROOT / e / f"{e}_notebook.py" for e in engines] if engines else sorted(
        p for p in ROOT.glob("*/*_notebook.py") if p.parent.name != "templates")
    missing = [str(n.relative_to(ROOT)) for n in notebooks if not n.exists()]
    if missing:
        sys.exit(f"no such notebook: {', '.join(missing)}")
    failed = False
    for notebook in notebooks:
        problems = check(notebook)
        print(f"{'✗' if problems else '✓'} {notebook.relative_to(ROOT)}")
        for p in problems:
            print(f"    {p}")
        failed |= bool(problems)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
