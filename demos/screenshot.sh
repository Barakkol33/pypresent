#!/usr/bin/env bash
# The pictures in the README, taken from a real build rather than drawn.
#
#   ./demos/screenshot.sh
#
# They come out of demos/out/05-notebook.html, which is the deck the README
# quotes, so a slide that changes shape shows up here rather than in a README
# that still describes the old one.  Needs Chrome; nothing else does.
set -euo pipefail
cd "$(dirname "$0")/.."

CHROME="${CHROME:-google-chrome-stable}"
command -v "$CHROME" >/dev/null || CHROME=google-chrome
command -v "$CHROME" >/dev/null || { echo "no chrome: set CHROME=" >&2; exit 1; }

DECK=demos/out/05-notebook.html
[ -f "$DECK" ] || ./demos/build.sh notebook

mkdir -p docs/img

shot() {   # slide number, file name
  "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --window-size=1600,900 --virtual-time-budget=6000 \
    --screenshot="docs/img/$2.png" "file://$PWD/$DECK#$1" >/dev/null 2>&1
  echo "  docs/img/$2.png  (slide $1)"
}

echo "from $DECK:"
shot 3 quoted-output
shot 4 quoted-figure
