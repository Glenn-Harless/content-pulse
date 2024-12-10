# Blockworks Article Analyzer

This application scrapes articles from blockworks.co, summarizes them using Llama 2 (via Ollama), and allows users to query information about the articles.

## Prerequisites
- Docker
- Docker Compose

## Setup
1. Start Ollama with Llama 2 locally:
```bash
docker pull ollama/ollama
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama3.2
```

2. Build and run the application:
```bash
docker compose up --build
```

## Features
- Scrapes latest articles from blockworks.co
- Generates summaries using Llama 3.2
- Provides an interface to query article information
- Stores article data for persistence
