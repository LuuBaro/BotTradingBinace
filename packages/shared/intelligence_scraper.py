"""
Intelligence Scraper - Gathers data from custom news sources
Supports RSS, Telegram (Public Preview), and generic Web Scraping
"""
import httpx
import logging
import feedparser
import ipaddress
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from sqlalchemy import select
from packages.shared.models import NewsSource, NewsLog
from packages.shared.database import AsyncSessionFactory

logger = logging.getLogger(__name__)

class IntelligenceScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.timeout = httpx.Timeout(20.0)
        self.max_items_per_source = 5

    def _is_safe_public_url(self, raw_url: str) -> bool:
        try:
            parsed = urlparse(raw_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return False

            host = parsed.hostname.lower()
            if host in {"localhost"}:
                return False

            try:
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
                    return False
            except ValueError:
                # Hostname (not raw IP)
                pass

            return True
        except Exception:
            return False

    async def _exists_recent(self, session, source_id: int, title: str | None, url: str | None) -> bool:
        cutoff = datetime.utcnow() - timedelta(days=3)
        query = select(NewsLog).where(NewsLog.source_id == source_id, NewsLog.timestamp >= cutoff)
        if url:
            query = query.where(NewsLog.url == url)
        elif title:
            query = query.where(NewsLog.title == title)
        else:
            return False

        res = await session.execute(query.limit(1))
        return res.scalar_one_or_none() is not None

    async def scrape_all(self):
        """Scrape all active news sources"""
        logger.info("Starting intelligence scraping cycle")
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(NewsSource).where(NewsSource.is_active == True))
            sources = result.scalars().all()
            
            for source in sources:
                try:
                    if not self._is_safe_public_url(source.url):
                        logger.warning(f"Skipping unsafe source URL: {source.name} ({source.url})")
                        continue

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
        """Scrape RSS feed with dedupe"""
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(source.url, headers=self.headers)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            for entry in feed.entries[: self.max_items_per_source]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                content = entry.get("summary", entry.get("description", ""))[:2000]

                if await self._exists_recent(session, source.id, title=title, url=link):
                    continue

                log = NewsLog(
                    source_id=source.id,
                    title=title,
                    content=content,
                    url=link,
                    timestamp=datetime.utcnow(),
                )
                session.add(log)

    async def _scrape_telegram(self, session, source: NewsSource):
        """Scrape Telegram public preview (https://t.me/s/...) with dedupe"""
        # Convert t.me/xxx to t.me/s/xxx for public preview
        url = source.url
        if "t.me/s/" not in url:
            url = url.replace("t.me/", "t.me/s/")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            messages = soup.find_all("div", class_="tgme_widget_message_text")
            for msg in messages[: self.max_items_per_source]:
                content = msg.get_text(separator="\n").strip()
                if not content:
                    continue

                title = f"Telegram Update: {source.name}"
                if await self._exists_recent(session, source.id, title=title, url=source.url):
                    continue

                log = NewsLog(
                    source_id=source.id,
                    title=title,
                    content=content[:2000],
                    url=source.url,
                    timestamp=datetime.utcnow(),
                )
                session.add(log)

    async def _scrape_web(self, session, source: NewsSource):
        """Basic web scraper (extracts paragraphs) with dedupe"""
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(source.url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Simple logic: get meta title and body text
            title = soup.title.string.strip() if soup.title and soup.title.string else source.name
            paragraphs = soup.find_all("p")
            content = "\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 50])

            if not content:
                return

            if await self._exists_recent(session, source.id, title=title, url=source.url):
                return

            log = NewsLog(
                source_id=source.id,
                title=title,
                content=content[:3000],
                url=source.url,
                timestamp=datetime.utcnow(),
            )
            session.add(log)
