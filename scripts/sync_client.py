#!/usr/bin/env python3
"""Generate the shared scaffolding in every engine notebook from client.py.

    scripts/sync_client.py             # rewrite the setup cell in each <engine>/<engine>_notebook.py
    scripts/sync_client.py --check     # exit 1 if any notebook is out of date (for CI)

client.py is the source of truth. Each notebook holds one generated cell, identical in every engine, so it
also runs on its own, where client.py is not available: the hidden `with app.setup` block. It is client.py
minus its docstring and `__all__`, imports included, plus AUTORUN. Its public names (the helpers and AUTORUN)
are visible to every cell without being passed in; client.py imports its modules under private names (`_os`,
`_requests`, ...), so a notebook imports whatever it uses itself, exactly as it will once the setup cell is
`from moth_atlas import ...`. A missing MOTH_API_KEY is reported by the helpers themselves on the first call.

The notebook needs only a `with app.setup(hide_code=True):` block to start from; its contents are replaced
on every run.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SETUP = '''\
with app.setup(hide_code=True):
    # cell: client
    # Shared scaffolding, generated from client.py by scripts/sync_client.py: edit client.py, not this block.
    # Only the public helpers and AUTORUN are visible to other cells; import any module you use in your own cells.
__CLIENT__

    # Headless exports: run every cell without pressing buttons. (Own line: marimo drops a trailing comment on save.)
    AUTORUN = _os.environ.get("MOTH_AUTORUN") == "1"'''


def generated():
    src = (ROOT / "client.py").read_text()
    lines, drop = src.splitlines(), set()
    for node in ast.parse(src).body:
        text = isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
        dunder = isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "__all__"
        if text or dunder:
            drop.update(range(node.lineno - 1, node.end_lineno))
    body = "\n".join(("    " + l) if l.strip() else "" for i, l in enumerate(lines) if i not in drop).strip("\n")
    return SETUP.replace("__CLIENT__", body)


def sync(path):
    text = path.read_text()
    lines = text.splitlines()
    for node in ast.parse(text).body:
        if isinstance(node, ast.With) and "app.setup" in ast.unparse(node.items[0].context_expr):
            lines[node.lineno - 1:node.end_lineno] = generated().splitlines()
            return "\n".join(lines) + "\n"
    sys.exit(f"{path.relative_to(ROOT)}: `with app.setup(hide_code=True):` block not found")


def main():
    check = "--check" in sys.argv[1:]
    stale = []
    for nb in sorted(ROOT.glob("*/*_notebook.py")):
        updated = sync(nb)
        if updated != nb.read_text():
            stale.append(nb)
            if not check:
                nb.write_text(updated)
    names = ", ".join(str(n.relative_to(ROOT)) for n in stale)
    if check and stale:
        sys.exit(f"out of date: {names}. Run scripts/sync_client.py")
    print(f"updated: {names}" if stale else "notebooks already match client.py")


if __name__ == "__main__":
    main()
