import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockworksScraper:
    BASE_URL = "https://blockworks.co"
    
    async def fetch_page(self, url: str) -> str:
        logger.info(f"Fetching page: {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        logger.error(f"Error fetching {url}: Status {response.status}")
                        raise Exception(f"HTTP {response.status}")
                    return await response.text()
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise

    async def extract_article_info(self, article_url: str) -> Dict:
        logger.info(f"Extracting article info from: {article_url}")
        try:
            html = await self.fetch_page(article_url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Updated selectors for title
            title = None
            title_candidates = [
                soup.find('h1'),  # Standard h1
                soup.find('meta', property='og:title'),  # Open Graph title
                soup.find('meta', {'name': 'title'})  # Meta title
            ]
            
            for candidate in title_candidates:
                if candidate:
                    if candidate.get('content'):  # For meta tags
                        title = candidate['content']
                        break
                    else:  # For h1 tags
                        title = candidate.text.strip()
                        break
            
            if not title:
                title = "No title found"
            
            # Updated content extraction
            content = ""
            # Try multiple potential content containers
            content_containers = [
                soup.find('article'),
                soup.find('div', class_='article-content'),
                soup.find('div', class_='post-content'),
                soup.find('main')
            ]
            
            for container in content_containers:
                if container:
                    # Get all text paragraphs
                    paragraphs = container.find_all(['p', 'h2', 'h3', 'h4'])
                    content = ' '.join([p.text.strip() for p in paragraphs if p.text.strip()])
                    if content:
                        break
            
            if not content:
                logger.warning(f"No article content found for {article_url}")
            
            return {
                "url": article_url,
                "title": title,
                "content": content,
                "scraped_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error extracting article info from {article_url}: {str(e)}")
            raise

    async def get_latest_articles(self, limit: int = 5) -> List[Dict]:
        logger.info(f"Getting latest {limit} articles")
        try:
            html = await self.fetch_page(f"{self.BASE_URL}/news")
            soup = BeautifulSoup(html, 'html.parser')
            
            # Updated article link finding
            article_links = []
            link_candidates = soup.find_all('a', href=True)
            
            for link in link_candidates:
                href = link['href']
                # Only include links that contain 'news' and aren't the main news page
                if '/news/' in href and href != '/news' and '/news/page/' not in href:
                    full_url = href if href.startswith('http') else self.BASE_URL + href
                    if full_url not in article_links:
                        article_links.append(full_url)
                        logger.info(f"Found article: {full_url}")
            
            if not article_links:
                logger.warning("No article links found on the page")
                return []
            
            article_links = article_links[:limit]
            logger.info(f"Processing {len(article_links)} articles")
            
            tasks = [self.extract_article_info(url) for url in article_links]
            articles = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_articles = [a for a in articles if isinstance(a, dict)]
            logger.info(f"Successfully processed {len(valid_articles)} articles")
            
            return valid_articles
        except Exception as e:
            logger.error(f"Error in get_latest_articles: {str(e)}")
            raise