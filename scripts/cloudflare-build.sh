#!/bin/sh
# Refresh the archive and public/ bundle, then stop the deploy when KILL_SWITCH
# is present so Wrangler does not upload a new version.
set -eu
cd "$(dirname "$0")/.."
python3 run.py
if [ -f KILL_SWITCH ]; then
  echo "KILL_SWITCH is present. Owner: Maxwell. Refusing to publish." >&2
  exit 1
fi
