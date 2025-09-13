#!/bin/bash
# run.sh - menjalankan cli.py otomatis

# pindah ke folder project
cd /home/python/short-fashion || exit 1

# jalankan script pakai python dari venv
/home/python/venv/bin/python cli.py \
  --generate \
  --prompt prompt.txt \
  --music music \
  --limit 1 \
  --no-zoom \
  --duration 2 \
  --generate-images \
  --youtube \
  --client-secret client_secret.json \
  --title-template "{title}" \
  --description "{description}" \
  --privacy public \
  --auto-delete