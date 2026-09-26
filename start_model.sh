#!/bin/sh
set -eu
: "${LLAMA_SERVER:?Set LLAMA_SERVER to the matching Prism runtime llama-server}"
: "${BONSAI_MODEL:?Set BONSAI_MODEL to the Ternary Bonsai 2 27B GGUF path}"
exec "$LLAMA_SERVER" -m "$BONSAI_MODEL" \
  --host 127.0.0.1 --port 62737 --alias bonsai-ui-public-ternary-bonsai2 \
  -c 65536 -np 1 -ngl 99 --jinja --reasoning-budget 512 \
  --temp 1.0 --top-p 0.95 --top-k 20 --min-p 0.05 \
  --presence-penalty 0.0 --repeat-penalty 1.0
