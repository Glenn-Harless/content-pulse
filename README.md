# Content Pulse

Real-time content aggregator and analyzer that distills insights from social media, news sources, and market data using LLMs. Currently supports crypto news analysis with planned expansion to stocks, geopolitics, and broader market sentiment tracking across Reddit, Twitter, and news platforms.

## Current Features
- Automated article scraping from crypto news sources (currently blockworks.co)
- Article summarization using Llama 3.2
- Natural language querying interface for article analysis
- In-memory data persistence
- Clean, responsive web interface

## Planned Features
- Reddit integration for crypto subreddit analysis
- Twitter sentiment analysis for crypto topics
- Expansion to traditional finance news sources
- Geopolitical news analysis
- Cross-platform sentiment correlation
- Historical data tracking and trend analysis

## Prerequisites
- Docker
- Docker Compose

## Quick Start
1. Start Ollama with Llama 3.2:
```bash
docker pull ollama/ollama
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama3.2
```

2. Build and run the application:
```bash
docker compose up --build
```

3. Access the web interface at `http://localhost:8000`

## Architecture
- FastAPI backend for robust API performance
- Ollama for local LLM inference
- Async scraping and processing for improved performance
- Bootstrap frontend for responsive design
- Docker containerization for easy deployment

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License
MIT

## Project Status
🚧 Active Development - Core features implemented, actively expanding to new data sources and analysis capabilities.