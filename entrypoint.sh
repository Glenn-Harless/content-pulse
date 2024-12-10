#!/bin/sh
# entrypoint.sh

# Install netcat first
echo "Installing netcat..."
apt-get update && apt-get install -y netcat-openbsd curl

# Wait for database
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Wait for Ollama to be ready
echo "Waiting for Ollama..."
while ! curl -s http://ollama:11434/api/health >/dev/null; do
  sleep 1
  echo "Waiting for Ollama to be ready..."
done
echo "Ollama is ready!"

# Pull the model if not already present
echo "Ensuring model is available..."
curl -X POST http://ollama:11434/api/pull -d '{"name": "llama3.2"}'
echo "Model setup complete"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000