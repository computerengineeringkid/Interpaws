#!/bin/sh
set -euo pipefail

MODEL_ID="qwen2.5:7b"

# Start Ollama in the background so the CLI can talk to it for pulls
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama API to come online
until ollama list >/dev/null 2>&1; do
  echo "Waiting for Ollama API to become ready..."
  sleep 2
done

# Ensure the required model is available before reporting healthy
if ! ollama list | grep -q "$MODEL_ID"; then
  echo "Preloading required model: $MODEL_ID"
  ollama pull "$MODEL_ID"
else
  echo "Model $MODEL_ID already present"
fi

echo "Ollama startup sequence complete."
wait $OLLAMA_PID
