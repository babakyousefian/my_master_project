#!/bin/bash
set -e

echo "🚀 Building and starting containers..."
sudo docker compose build --no-cache
sudo docker compose up --build -d

echo "✅ Containers are running."
echo "📡 FastAPI available at: http://127.0.0.1:8000"
echo "🌍 Web (HTML+JS+MP3) available at: http://127.0.0.1:8080"

# follow logs
sudo docker compose logs -f
sudo docker compose logs parallel_api --tail=100 -f
