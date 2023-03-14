#!/bin/bash

set -e
set -u
set -o pipefail

# run application
python3 /app/run.py
