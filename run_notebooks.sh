#!/usr/bin/env bash
# Run engine notebooks top to bottom against the API and save their outputs in place.
#
#   MOTH_API_KEY=... MOTH_API_BASE=... ./run_notebooks.sh        # every engine notebook
#   ./run_notebooks.sh otoc_echo labyrinth                       # only these folders
#
# A notebook that hits an error is left unchanged. Each run submits real jobs and uses credits.
set -uo pipefail
cd "$(dirname "$0")"
: "${MOTH_API_KEY:?set MOTH_API_KEY (and MOTH_API_BASE for the staging API)}"

if [ $# -gt 0 ]; then
  notebooks=(); for d in "$@"; do notebooks+=("${d%/}/${d%/}_notebook.ipynb"); done
else
  notebooks=(); for f in */*_notebook.ipynb; do [[ $f == templates/* ]] || notebooks+=("$f"); done
fi

failed=()
for nb in "${notebooks[@]}"; do
  echo "== $nb"
  start=$SECONDS
  if jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 "$nb" 2>&1 | tail -n 3; [ "${PIPESTATUS[0]}" -eq 0 ]; then
    if grep -qF "$MOTH_API_KEY" "$nb"; then
      echo "   the API key appears in the saved notebook: do not commit it"; failed+=("$nb")
    else
      echo "   ok in $((SECONDS - start)) s, $(du -k "$nb" | cut -f1) KB"
    fi
  else
    failed+=("$nb")
  fi
done

if [ ${#failed[@]} -gt 0 ]; then
  echo "failed: ${failed[*]}"; exit 1
fi
echo "all ${#notebooks[@]} notebooks ran"
