from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Set
import asyncio
import json
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .db.models import Content, ContentType
from .db.database import AsyncSessionLocal
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

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

class Query(BaseModel):
    question: str
    model: Optional[str] = None

class ModelSelection(BaseModel):
    model: str

# Dependency for database session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

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
async def scrape_articles(
    limit: int = 5,
    model: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Get recent articles to avoid re-scraping
        query = select(Content).where(
            Content.type == ContentType.ARTICLE,
            Content.scraped_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(Content.scraped_at.desc())
        
        result = await db.execute(query)
        recent_articles = result.scalars().all()
        recent_urls = {article.url for article in recent_articles}
        
        # Scrape new articles
        scraped = await scraper.get_latest_articles(limit)
        new_articles = [a for a in scraped if a['url'] not in recent_urls]
        
        # Save new articles to database
        db_articles = []
        for article_data in new_articles:
            article = Content(
                type=ContentType.ARTICLE,
                url=article_data['url'],
                title=article_data['title'],
                content=article_data['content'],
                source='blockworks',
                scraped_at=datetime.fromisoformat(article_data['scraped_at'])
            )
            db.add(article)
            db_articles.append(article)
        
        await db.commit()
        
        # Start background task for summaries
        if db_articles:
            asyncio.create_task(generate_summaries_background(db_articles, model))
        
        return {
            "message": f"Successfully scraped {len(new_articles)} articles",
            "articles": [article.to_dict() for article in db_articles]
        }
    
    except Exception as e:
        logger.error(f"Error in scrape_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def generate_summaries_background(articles: List[Content], model: Optional[str] = None):
    """Generate summaries in parallel with rate limiting"""
    # Limit concurrent summarizations to prevent overload
    semaphore = asyncio.Semaphore(2)  # Process 2 articles at a time
    
    async def generate_single_summary(article: Content):
        async with semaphore:
            try:
                # Notify start of summary generation
                await notify_clients(str(article.id), "Generating summary...", 0)
                
                # Generate summary
                summary = await llm.generate_summary(article.content, model)
                
                # Update database with summary
                async with AsyncSessionLocal() as db:
                    article.summary = summary
                    db.add(article)
                    await db.commit()
                
                # Notify completion
                await notify_clients(str(article.id), summary, 100)
                logger.info(f"Generated summary for article {article.id}")
                
            except Exception as e:
                logger.error(f"Error generating summary for article {article.id}: {str(e)}")
                error_msg = "Error generating summary"
                await notify_clients(str(article.id), error_msg, 100)
    
    # Create tasks for all articles but process them with semaphore limit
    tasks = [generate_single_summary(article) for article in articles]
    await asyncio.gather(*tasks)

@app.post("/generate-summary/{article_id}")
async def generate_single_article_summary(
    article_id: int, 
    model: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Generate summary for a single article"""
    try:
        # Get article from database
        query = select(Content).where(Content.id == article_id)
        result = await db.execute(query)
        article = result.scalar_one_or_none()
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Create background task for this single summary
        asyncio.create_task(generate_summaries_background([article], model))
        return {"message": "Summary generation started"}
    except Exception as e:
        logger.error(f"Error in generate_single_article_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/articles")
async def get_articles(db: AsyncSession = Depends(get_db)):
    """Get all scraped articles"""
    try:
        query = select(Content).order_by(Content.scraped_at.desc())
        result = await db.execute(query)
        articles = result.scalars().all()
        return [article.to_dict() for article in articles]
    except Exception as e:
        logger.error(f"Error in get_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_articles(
    query: Query,
    db: AsyncSession = Depends(get_db)
):
    """Query information about the articles"""
    try:
        # Get recent articles from database
        result = await db.execute(
            select(Content)
            .where(Content.type == ContentType.ARTICLE)
            .order_by(Content.scraped_at.desc())
        )
        articles = result.scalars().all()
        
        if not articles:
            raise HTTPException(status_code=404, detail="No articles available. Please scrape articles first.")
        
        # Convert to format expected by llm.query_articles
        article_dicts = [article.to_dict() for article in articles]
        response = await llm.query_articles(article_dicts, query.question, query.model)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in query_articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
async def list_models():
    """Get list of available models and their capabilities"""
    try:
        return await llm.list_available_models()
    except Exception as e:
        logger.error(f"Error in list_models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))