#!/usr/bin/env bash
# Build every demo into demos/out/, which is disposable and rebuilt from here.
#
#   ./build.sh              everything
#   ./build.sh themes       just the four-theme set
set -euo pipefail
cd "$(dirname "$0")"

PYPRESENT="${PYPRESENT:-pypresent}"
command -v "$PYPRESENT" >/dev/null || PYPRESENT="python -m pypresent"

what="${1:-all}"
mkdir -p out

if [[ "$what" == all || "$what" == blocks ]]; then
  echo "== every block =="
  $PYPRESENT render 01-every-block.md -o out/01-every-block.html
  $PYPRESENT render 01-every-block.md -f md -o out/01-every-block.export.md
fi

if [[ "$what" == all || "$what" == themes ]]; then
  echo "== the same deck, four ways =="
  for theme in warm office dark slate; do
    $PYPRESENT render 02-themes.md --theme "$theme" -o "out/02-themes-$theme.html"
  done
  echo "== and one written by hand =="
  $PYPRESENT render 01-every-block.md --theme 04-custom-theme.toml \
      -o out/04-custom-theme.html
fi

if [[ "$what" == all || "$what" == rtl ]]; then
  echo "== right to left =="
  $PYPRESENT render 03-rtl.md -o out/03-rtl.html
fi

if [[ "$what" == all || "$what" == notebook ]]; then
  echo "== a deck that quotes its lecture =="
  # Both notebooks are committed already executed, so skipping both runs needs
  # no kernel at all.  Drop the two flags to build it for real.
  $PYPRESENT build 05-notebook-slides.ipynb --skip-source-run --skip-slides-run
fi

echo
echo "built:"
ls -1sh out | sed 's/^/  /'
