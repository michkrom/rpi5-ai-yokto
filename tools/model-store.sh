#!/bin/bash
# Yokto model store
# ------------------
# Keep GGUF models on the HOST so that re-flashing the Pi (or provisioning a
# new board) does not require downloading from HuggingFace again.
#
# Usage:
#   tools/model-store.sh pull [HOST]    # Pi -> ./model-store
#   tools/model-store.sh push [HOST]    # ./model-store -> Pi /usr/share/models
#   tools/model-store.sh list [HOST]    # show both sides
#
# HOST is a normal ssh target (default: $PI_HOST or root@192.168.68.63).
set -euo pipefail
cd "$(dirname "$0")/.."
HOST="${2:-${PI_HOST:-root@192.168.68.63}}"
STORE="model-store"
mkdir -p "$STORE"

SSHOPTS="-i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes \
 -o StrictHostKeyChecking=no -o HostKeyAlgorithms=+ssh-rsa \
 -o PubkeyAcceptedAlgorithms=+ssh-rsa"

remote_files() {
  ssh $SSHOPTS "$HOST" 'cd /usr/share/models && ls *.gguf 2>/dev/null | grep -v "^llama-model.gguf$"'
}

case "${1:-}" in
  pull)
    echo "pulling models from $HOST ..."
    for f in $(remote_files); do
      scp $SSHOPTS "$HOST:/usr/share/models/$f" "$STORE/" && echo "  pulled $f"
    done
    ;;
  push)
    echo "pushing models to $HOST:/usr/share/models ..."
    ssh $SSHOPTS "$HOST" 'mkdir -p /usr/share/models'
    mapfile -t files < <(find "$STORE" -maxdepth 1 -name '*.gguf' 2>/dev/null)
    for f in "${files[@]}"; do
      scp $SSHOPTS "$f" "$HOST:/usr/share/models/$(basename "$f")" && \
        echo "  pushed $(basename "$f")"
    done
    ;;
  list)
    echo "== host store ($STORE) =="
    find "$STORE" -maxdepth 1 -name '*.gguf' -printf '%f\n' 2>/dev/null
    echo "== device (${HOST}:/usr/share/models) =="
    ssh $SSHOPTS "$HOST" 'ls -l /usr/share/models/*.gguf 2>/dev/null || true'
    ;;
  *)
    sed -n '3,11p' "$0"
    exit 1
    ;;
esac