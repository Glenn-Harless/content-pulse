from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from .scraper import BlockworksScraper
from .llm import LlamaInterface
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Blockworks Article Analyzer")

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

class Article(BaseModel):
    url: str
    title: str
    content: str
    summary: Optional[str] = None
    scraped_at: str

class Query(BaseModel):
    question: str
    model: Optional[str] = None

class ModelSelection(BaseModel):
    model: str

@app.get("/")
async def read_root():
    return FileResponse("app/static/index.html")

@app.post("/scrape")
async def scrape_articles(limit: int = 5, model: Optional[str] = None):
    """Scrape latest articles and generate summaries"""
    global articles
    try:
        logger.info("Starting article scraping")
        articles = await scraper.get_latest_articles(limit)
        
        # Ensure model is downloaded if specified
        if model:
            await llm.ensure_model_downloaded(model)
        
        logger.info("Generating summaries")
        for article in articles:
            try:
                summary = await llm.generate_summary(article['content'], model)
                article['summary'] = summary
                logger.info(f"Generated summary for article: {article['title']}")
            except Exception as e:
                logger.error(f"Error generating summary: {str(e)}")
                article['summary'] = "Error generating summary"
        
        return {"message": f"Successfully scraped {len(articles)} articles", "articles": articles}
    except Exception as e:
        logger.error(f"Error in scrape_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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