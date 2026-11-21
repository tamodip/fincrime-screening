#!/bin/sh
# Demo run: system/demo.sh <data folder> [out dir]
# Runs the resolver (timed, with an engine trace), scores practice labels if validate.py is present,
# builds the offline viewer and opens it.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DATA="${1:?usage: system/demo.sh <data folder> [out dir]}"
OUT="${2:-$HERE/../demo}"
mkdir -p "$OUT"
PRED="$OUT/predictions.jsonl"
TRACE="$OUT/trace.jsonl"
printf '\n  Same Person or Not? - deterministic screening resolver\n  no model . stdlib only . $0\n\n'
T0=$(python3 -c 'import time;print(time.time())')
SCREEN_TRACE="$TRACE" "$HERE/run" "$DATA" "$PRED" | sed 's/^/  /'
T1=$(python3 -c 'import time;print(time.time())')
RT=$(python3 -c "print('%.1f' % ($T1 - $T0))")
echo "  run time: ${RT}s"
V="$HERE/../validate.py"
if [ -f "$V" ]; then
  if [ -f "$DATA/practice_labels.jsonl" ]; then
    python3 "$V" --data "$DATA" --output "$PRED" --score "$DATA/practice_labels.jsonl" | sed 's/^/  /'
  else
    python3 "$V" --data "$DATA" --output "$PRED" | sed 's/^/  /'
  fi
fi
python3 "$HERE/viewer/build_viewer.py" "$DATA" "$PRED" "$OUT/index.html" --trace "$TRACE" --runtime "$RT" | sed 's/^/  /'
echo "  open: $OUT/index.html"
if [ -n "$NO_OPEN" ]; then :
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$OUT/index.html" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then open "$OUT/index.html" || true; fi
