#!/bin/sh
# swupdate-apply.sh - Apply SWU update on target device
# Usage: swupdate-apply.sh <path-to-swu-file>

if [ -z "$1" ]; then
    echo "Usage: $0 <path-to-swu-file>"
    exit 1
fi

SWU_FILE="$1"

if [ ! -f "$SWU_FILE" ]; then
    echo "Error: SWU file not found: $SWU_FILE"
    exit 1
fi

echo "Applying update from $SWU_FILE..."
swupdate -i "$SWU_FILE"
result=$?

if [ $result -eq 0 ]; then
    echo "Update installed successfully. Reboot to activate."
else
    echo "Update failed with exit code $result"
    exit $result
fi