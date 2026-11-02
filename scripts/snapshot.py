"""Publish the editor's auto-saved notebook (outputs included) as the static GitHub preview.

    python scripts/snapshot.py blur

Copies <engine>/__marimo__/<engine>_notebook.ipynb to <engine>/outputs/. Saved with auto_download=["ipynb"],
each output has a PNG screenshot and, for some cells, HTML whose images point at the live editor
(./@file/...); that HTML is dropped so every viewer shows the screenshot.
"""

import json
import sys
from pathlib import Path

engine = sys.argv[1]
root = Path(__file__).resolve().parent.parent / engine
src, dst = root / "__marimo__" / f"{engine}_notebook.ipynb", root / "outputs" / f"{engine}_notebook.ipynb"
nb = json.loads(src.read_text())
for cell in nb["cells"]:
    for out in cell.get("outputs", []):
        if "image/png" in out.get("data", {}):
            out["data"].pop("text/html", None)
dst.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print(f"wrote {dst.relative_to(root.parent)}")
