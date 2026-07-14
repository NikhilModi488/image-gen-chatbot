#!/bin/bash
# Start Ollama in the background
echo "Starting Ollama server..."
ollama serve &

# Wait for Ollama to be available
echo "Waiting for Ollama to start..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 2
done
echo "Ollama is ready!"

# Pull llama3.2:latest model
echo "Pulling llama3.2:latest model..."
ollama pull llama3.2:latest
echo "Model pulled successfully!"

# Start FastAPI server on port 7860 (Hugging Face default port)
echo "Starting FastAPI server on port 7860..."
exec uvicorn main:app --host 0.0.0.0 --port 7860
