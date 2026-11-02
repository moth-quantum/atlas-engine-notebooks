# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10"]
# ///
"""Publish the editor's auto-saved notebook (outputs included) as the static GitHub preview.

    uv run scripts/snapshot.py blur

Copies <engine>/__marimo__/<engine>_notebook.ipynb to <engine>/outputs/. Saved with auto_download=["ipynb"],
each output has a PNG screenshot and, for some cells, HTML whose images point at the live editor
(./@file/...); that HTML is dropped so every viewer shows the screenshot. Screenshots are transparent with
dark text, so they are flattened onto white to stay readable in dark themes.
"""

import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

engine = sys.argv[1]
root = Path(__file__).resolve().parent.parent / engine
src, dst = root / "__marimo__" / f"{engine}_notebook.ipynb", root / "outputs" / f"{engine}_notebook.ipynb"
nb = json.loads(src.read_text())
for cell in nb["cells"]:
    for out in cell.get("outputs", []):
        data = out.get("data", {})
        if "image/png" in data:
            data.pop("text/html", None)
            shot = Image.open(io.BytesIO(base64.b64decode(data["image/png"]))).convert("RGBA")
            flat, buf = Image.new("RGB", shot.size, "white"), io.BytesIO()
            flat.paste(shot, mask=shot)
            flat.save(buf, "PNG", optimize=True)
            data["image/png"] = base64.b64encode(buf.getvalue()).decode()
dst.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
print(f"wrote {dst.relative_to(root.parent)}")
