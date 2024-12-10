from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Set
import asyncio
import json
from datetime import datetime
from .scraper import BlockworksScraper
from .llm import LlamaInterface
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Content Pulse")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scraper = BlockworksScraper()
llm = LlamaInterface()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Store articles in memory (could be replaced with a database)
articles = []

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

class Article(BaseModel):
    url: str
    title: str
    content: str
    summary: Optional[str] = None
    scraped_at: str
    id: str

class Query(BaseModel):
    question: str
    model: Optional[str] = None

class ModelSelection(BaseModel):
    model: str

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time updates"""
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        active_connections.remove(websocket)

async def notify_clients(article_id: str, summary: str, progress: int = 100):
    """Notify all connected clients of a summary update"""
    message = json.dumps({
        "articleId": article_id,
        "summary": summary,
        "progress": progress
    })
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {str(e)}")
            active_connections.remove(connection)

@app.get("/")
async def read_root():
    return FileResponse("app/static/index.html")

@app.post("/scrape")
async def scrape_articles(limit: int = 5, model: Optional[str] = None):
    """Scrape articles and return immediately, generate summaries in background"""
    global articles
    try:
        logger.info(f"Starting article scrape, limit: {limit}")
        # Get articles without summaries first
        articles = await scraper.get_latest_articles(limit)
        
        # Add IDs to articles
        for i, article in enumerate(articles):
            article['id'] = str(i)
            article['summary'] = None
        
        # Start background task for summaries
        asyncio.create_task(generate_summaries_background(articles, model))
        
        return {"message": f"Successfully scraped {len(articles)} articles", "articles": articles}
    except Exception as e:
        logger.error(f"Error in scrape_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_summaries_background(articles: List[Dict], model: Optional[str] = None):
    """Generate summaries in parallel with rate limiting"""
    # Limit concurrent summarizations to prevent overload
    semaphore = asyncio.Semaphore(2)  # Process 2 articles at a time
    
    async def generate_single_summary(article: Dict):
        async with semaphore:
            try:
                # Notify start of summary generation
                await notify_clients(article['id'], "Generating summary...", 0)
                
                # Generate summary
                summary = await llm.generate_summary(article['content'], model)
                article['summary'] = summary
                
                # Notify completion
                await notify_clients(article['id'], summary, 100)
                logger.info(f"Generated summary for article {article['id']}")
                
            except Exception as e:
                logger.error(f"Error generating summary for article {article['id']}: {str(e)}")
                error_msg = "Error generating summary"
                article['summary'] = error_msg
                await notify_clients(article['id'], error_msg, 100)
    
    # Create tasks for all articles but process them with semaphore limit
    tasks = [generate_single_summary(article) for article in articles]
    await asyncio.gather(*tasks)

@app.post("/generate-summary/{article_id}")
async def generate_single_article_summary(article_id: str, model: Optional[str] = None):
    """Generate summary for a single article"""
    article = next((a for a in articles if a['id'] == article_id), None)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Create background task for this single summary
    asyncio.create_task(generate_single_summary(article, model))
    return {"message": "Summary generation started"}

@app.get("/articles")
async def get_articles():
    """Get all scraped articles"""
    return articles

@app.post("/query")
async def query_articles(query: Query):
    """Query information about the articles"""
    if not articles:
        raise HTTPException(status_code=404, detail="No articles available. Please scrape articles first.")
    
    try:
        response = await llm.query_articles(articles, query.question, query.model)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in query_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """Get list of available models and their capabilities"""
    return await llm.list_available_models()