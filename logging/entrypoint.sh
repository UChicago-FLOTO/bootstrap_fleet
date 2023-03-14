#!/bin/bash

set -e
set -u
set -o pipefail

MOUNT_PATH="/mnt/external"
# ensure usb drive is mounted, if present
mkdir -p "${MOUNT_PATH}"

if grep -qs "${MOUNT_PATH}" /proc/mounts; then
    echo "It's mounted."
else
    mount /dev/sda1 "${MOUNT_PATH}"
fi

# run application
python3 /app/run.py
