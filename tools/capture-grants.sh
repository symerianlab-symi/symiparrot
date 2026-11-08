#!/bin/sh
# capture-grants.sh — snapshot the fork's runtime grant state into the repo.
# The live file is runtime-mutable (host rewrites it on define/confirm); the
# repo holds point-in-time captures under state/, restore = copy back.
set -eu
HOME_DIR="${SYMI_PARROT_HOME:-$HOME/.symi-jai-parrot}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$HOME_DIR/.symi-parrot-dynamic-grants.json"
[ -f "$SRC" ] || { echo "no grants file at $SRC (nothing defined yet)"; exit 1; }
mkdir -p "$REPO/state"
cp "$SRC" "$REPO/state/dynamic-grants.snapshot.json"
chmod 644 "$REPO/state/dynamic-grants.snapshot.json"
echo "captured -> state/dynamic-grunts.snapshot.json" | sed 's/grunts/grants/'
echo "restore: cp $REPO/state/dynamic-grants.snapshot.json $SRC"
