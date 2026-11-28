#!/bin/sh
# Refresh the archive and public/ bundle, then stop the deploy when KILL_SWITCH
# is present so Wrangler does not upload a new version.
set -eu
cd "$(dirname "$0")/.."
if command -v python3 >/dev/null 2>&1; then
  python3 run.py
elif command -v python >/dev/null 2>&1; then
  python run.py
else
  echo "python3 is not installed; refusing to publish." >&2
  exit 1
fi
if [ -f KILL_SWITCH ]; then
  echo "KILL_SWITCH is present. Owner: Maxwell. Refusing to publish." >&2
  exit 1
fi
