#!/bin/bash
set -euo pipefail
cd /app

# load .env if present
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs) || true
fi

python3 main.py
