#!/bin/bash

# ensure usb drive is mounted, if present
mkdir -p /mnt/external
mount /dev/sda1 /mnt/external

# run application
python3 /app/run.py
