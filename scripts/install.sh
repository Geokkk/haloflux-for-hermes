#!/bin/sh
# HALOFLUX for Hermes — one-click installer (Linux / macOS)
# Copies dashboard/ from this repository into <HERMES_HOME>/plugins/haloflux/.
# No network access, no sudo, no config changes, no service restarts.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(dirname -- "$SCRIPT_DIR")
SRC="$REPO_ROOT/dashboard"

if [ ! -f "$SRC/manifest.json" ] || [ ! -f "$SRC/plugin_api.py" ]; then
  echo "error: dashboard/ not found next to scripts/ (looked in $REPO_ROOT)" >&2
  exit 1
fi

FRESH_DEFAULT=0
if [ -n "${HERMES_HOME:-}" ]; then
  HERMES_DIR="$HERMES_HOME"
else
  HERMES_DIR="$HOME/.hermes"
  if [ ! -d "$HERMES_DIR" ]; then
    FRESH_DEFAULT=1
  fi
fi

PLUGINS_DIR="$HERMES_DIR/plugins"
DEST="$PLUGINS_DIR/haloflux"

mkdir -p "$PLUGINS_DIR"

if [ -e "$DEST" ]; then
  TS=$(date +%Y%m%d%H%M%S)
  BACKUP="$PLUGINS_DIR/haloflux.bak-$TS"
  mv "$DEST" "$BACKUP"
  echo "Existing installation backed up to: $BACKUP"
fi

mkdir -p "$DEST"
cp -R "$SRC" "$DEST/"

# Self-check
if [ ! -f "$DEST/dashboard/plugin_api.py" ]; then
  echo "error: plugin_api.py missing after copy" >&2
  exit 1
fi
if [ ! -f "$DEST/dashboard/manifest.json" ]; then
  echo "error: manifest.json missing after copy" >&2
  exit 1
fi

VERSION=""
if command -v python3 >/dev/null 2>&1; then
  VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$DEST/dashboard/manifest.json" 2>/dev/null || true)
fi
if [ -n "$VERSION" ]; then
  echo "Installed HALOFLUX for Hermes v$VERSION -> $DEST"
else
  echo "Installed HALOFLUX for Hermes -> $DEST"
fi

if [ "$FRESH_DEFAULT" = "1" ]; then
  echo "Note: no existing Hermes directory was detected; installed to the default path $HERMES_DIR."
fi

echo "Next steps:"
echo "  1. Restart hermes-dashboard so it picks up the plugin."
echo "  2. Open /haloflux in your dashboard."
echo "  3. If you are not logged in yet, log in to the dashboard first."
