"""
Intelligence Scraper - Gathers data from custom news sources
Supports RSS, Telegram (Public Preview), and generic Web Scraping
"""
import httpx
import logging
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import select, update
from packages.shared.models import NewsSource, NewsLog
from packages.shared.database import AsyncSessionFactory

logger = logging.getLogger(__name__)

class IntelligenceScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def scrape_all(self):
        """Scrape all active news sources"""
        logger.info("Starting intelligence scraping cycle")
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(NewsSource).where(NewsSource.is_active == True))
            sources = result.scalars().all()
            
            for source in sources:
                try:
                    logger.info(f"Scraping source: {source.name} ({source.url})")
                    if source.source_type == "rss":
                        await self._scrape_rss(session, source)
                    elif source.source_type == "telegram":
                        await self._scrape_telegram(session, source)
                    elif source.source_type == "web":
                        await self._scrape_web(session, source)
                        
                    source.last_scraped_at = datetime.utcnow()
                    await session.commit()
                except Exception as e:
                    logger.error(f"Failed to scrape {source.name}: {e}")
                    await session.rollback()

    async def _scrape_rss(self, session, source: NewsSource):
        """Scrape RSS feed"""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(source.url, headers=self.headers)
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries[:5]: # Take last 5
                # Check for duplicates by title/url in recent logs could be added here
                log = NewsLog(
                    source_id=source.id,
                    title=entry.get("title", ""),
                    content=entry.get("summary", entry.get("description", ""))[:2000],
                    url=entry.get("link", ""),
                    timestamp=datetime.utcnow()
                )
                session.add(log)

    async def _scrape_telegram(self, session, source: NewsSource):
        """Scrape Telegram public preview (https://t.me/s/...)"""
        # Convert t.me/xxx to t.me/s/xxx for public preview
        url = source.url
        if "t.me/s/" not in url:
            url = url.replace("t.me/", "t.me/s/")
            
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")
            
            messages = soup.find_all("div", class_="tgme_widget_message_text")
            for msg in messages[:5]:
                content = msg.get_text(separator="\n").strip()
                if content:
                    log = NewsLog(
                        source_id=source.id,
                        title=f"Telegram Update: {source.name}",
                        content=content[:2000],
                        url=source.url,
                        timestamp=datetime.utcnow()
                    )
                    session.add(log)

    async def _scrape_web(self, session, source: NewsSource):
        """Basic web scraper (extracts paragraphs)"""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(source.url, headers=self.headers)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Simple logic: get meta title and body text
            title = soup.title.string if soup.title else source.name
            paragraphs = soup.find_all("p")
            content = "\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 50])
            
            if content:
                log = NewsLog(
                    source_id=source.id,
                    title=title,
                    content=content[:3000],
                    url=source.url,
                    timestamp=datetime.utcnow()
                )
                session.add(log)
