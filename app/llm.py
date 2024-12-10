"""
This script provides a simple interface to llama.ai's text generation model. It allows for
generating summaries of articles and answering questions based on a list of articles.
"""
import httpx
import json
from typing import Dict, List, Optional
import os
import logging
import asyncio
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

class LlamaInterface:
    def __init__(self):
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        
    async def _generate_streaming_response(self, prompt: str, model: str = "llama3.2") -> str:
        """Generate response with streaming to avoid timeouts"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": 0.3,
                            "top_k": 40,
                            "top_p": 0.9,
                            "num_predict": 200,
                        }
                    },
                    headers={"Accept": "application/x-ndjson"},
                )
                
                if response.status_code != 200:
                    return f"Error: API returned status code {response.status_code}"

                # Collect the streamed responses
                full_response = ""
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        if chunk.get("response"):
                            full_response += chunk["response"]
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

                return full_response.strip()
                
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {str(e)}")
            return "Error: Request timed out while generating response"
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}"

    async def generate_summary(self, text: str, model: Optional[str] = None) -> str:
        """Generate article summary using specified or default model"""
        # Truncate very long articles to prevent context length issues
        max_chars = 4000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = f"""Please provide a concise 2-3 sentence summary of the following article:
        
        Article: {text}
        
        Summary:"""
        
        return await self._generate_streaming_response(prompt, model or "llama3.2")

    async def query_articles(self, articles: List[Dict], query: str, model: Optional[str] = None) -> str:
        """Query articles using specified or default model"""
        # Prepare context, but limit length
        context_parts = []
        total_chars = 0
        max_chars_per_article = 2000
        max_total_chars = 6000
        
        for article in articles:
            content = article['content']
            if len(content) > max_chars_per_article:
                content = content[:max_chars_per_article] + "..."
                
            article_text = f"Article: {article['title']}\n{content}\n"
            if total_chars + len(article_text) > max_total_chars:
                break
                
            context_parts.append(article_text)
            total_chars += len(article_text)
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Based on these articles, please answer this question: {query}

        Context:
        {context}

        Answer:"""
        
        return await self._generate_streaming_response(prompt, model or "llama3.2")