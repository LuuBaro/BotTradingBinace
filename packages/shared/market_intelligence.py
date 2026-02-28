"""
Market Intelligence - Aggregates data from multiple sources (Simulated for Demo)
Simulates News, Blockchain Context, and Global Sentiments
"""
from datetime import datetime, timedelta
import random
import json
import logging
from typing import Dict, List, Any, Optional
from packages.shared.config import settings
from packages.shared.llm_adapter import LLMAdapter, get_llm_adapter
from packages.shared.models import NewsSource, NewsLog
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, desc

logger = logging.getLogger(__name__)

class MarketIntelligence:
    def __init__(self, llm: Optional[LLMAdapter] = None):
        self.last_update = datetime.utcnow()
        self.cached_intelligence = None
        self.llm = llm
        from packages.shared.intelligence_scraper import IntelligenceScraper
        self.scraper = IntelligenceScraper()

    async def get_market_context(self, market_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Synthesize market intelligence from multiple channels"""
        
        # If no cache or cache older than 10 minutes (600s), refresh
        if not self.cached_intelligence or (datetime.utcnow() - self.last_update).total_seconds() > 600:
            # Trigger background scraping
            try:
                await self.scraper.scrape_all()
            except Exception as e:
                logger.error(f"Scraper failed during refresh: {e}")
                
            self.cached_intelligence = await self._generate_fresh_intelligence(market_data)
            self.last_update = datetime.utcnow()
            
        return self.cached_intelligence

    async def _generate_fresh_intelligence(self, market_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        headlines = []
        signals = []
        
        # 1. Fetch real news from NewsLog
        try:
            async with AsyncSessionFactory() as session:
                result = await session.execute(
                    select(NewsLog.title, NewsLog.content, NewsLog.url)
                    .order_by(desc(NewsLog.timestamp))
                    .limit(5)
                )
                for log in result.all():
                    headlines.append({
                        "title": log.title,
                        "content": log.content[:2000], # Keep a reasonable amount
                        "url": log.url
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch real news logs: {e}")
            
        if not headlines:
            headlines = [
                {"title": "Thị trường kỳ vọng biến động thấp", "content": "Fed ám chỉ lãi suất ổn định, thị trường kỳ vọng biến động thấp cho crypto trong ngắn hạn.", "url": "#"},
                {"title": "Hoạt động on-chain gia tăng", "content": "Phát hiện hoạt động on-chain gia tăng tại các ví cá voi ETH (+12% dòng tiền) trong 24h qua.", "url": "#"},
                {"title": "Quy định EU thúc đẩy tâm lý", "content": "Sự rõ ràng về quy định tại thị trường EU thúc đẩy tâm lý nhà đầu tư tổ chức tham gia thị trường Web3.", "url": "#"}
            ]
        
        blockchain_signals = [
            {"source": "On-Chain", "signal": "Tích lũy Cá voi (Whale Accumulation)", "strength": "Mạnh", "sentiment": "Lạc quan (Bullish)"},
            {"source": "Sàn Binance", "signal": "Dòng tiền Stablecoin chảy vào", "strength": "Trung bình", "sentiment": "Trung tính (Neutral)"},
            {"source": "Mạng lưới", "signal": "Phí Gas giảm mạnh", "strength": "Thấp", "sentiment": "Lạc quan (Bullish)"},
            {"source": "Thợ đào", "signal": "Hashrate đạt mức cao nhất mọi thời đại", "strength": "Mạnh", "sentiment": "Tăng trưởng dài hạn"},
            {"source": "Orderbook", "signal": "Tường mua dày đặc tại vùng hỗ trợ", "strength": "Mạnh", "sentiment": "Hỗ trợ mạnh"}
        ]
        
        
        global_sentiment = random.choice([72, 68, 75, 81, 65, 59, 78, 83])
        
        # Dynamic AI Summary using LLM if available
        ai_summary = "Neural Core đang phân tích dòng tiền và các chỉ số kỹ thuật để xác định điểm xoay chuyển của thị trường."
        
        if self.llm and market_data:
            try:
                # Prepare a small context for LLM
                market_summary = []
                for m in market_data[:3]: # Top 3 symbols
                    if isinstance(m, dict):
                         market_summary.append(f"{m.get('symbol')}: Close={m.get('close')}, High={m.get('high')}, Low={m.get('low')}")
                    else:
                         # It might be a model object or JSON string from DB
                         market_summary.append(str(m)[:200])
                
                # Include news headlines context for AI
                news_context = "\n".join([f"{h['title']}: {h['content'][:100]}" for h in headlines[:3]])
                
                prompt = f"""
                You are the Neural Core of an AI Trading System. 
                Based on the following real-time market data:
                {json.dumps(market_summary, indent=2)}
                
                And recent News/Telegram updates:
                {news_context}
                
                Generate a 1-2 sentence professional market outlook in VIETNAMESE.
                Focus on 'bias', 'risk', and 'opportunity'.
                Start with 'Neural Core xác định...' or 'Phân tích từ Neural Core cho thấy...'
                """
                
                response = await self.llm.generate(prompt)
                if response:
                    # Clean the response if it's JSON wrap
                    if response.startswith('{'):
                         resp_data = json.loads(response)
                         ai_summary = resp_data.get('rationale', resp_data.get('content', response))
                    else:
                         ai_summary = response.strip('"').strip("'")
                
                logger.info("Generated dynamic market summary via LLM")
            except Exception as e:
                logger.warning(f"Failed to generate dynamic summary: {e}")
                ai_summary = "Neural Core xác định sự tích lũy tại các vùng giá quan trọng. Rủi ro ổn định bởi dòng tiền on-chain tích cực."

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "global_sentiment_index": global_sentiment,
            "market_bias": "TĂNG TRƯỞNG (BULLISH)" if global_sentiment > 65 else "TRUNG TÍNH (NEUTRAL)",
            "headlines": headlines[:3],
            "signals": random.sample(blockchain_signals, 2),
            "ai_summary": ai_summary
        }

# Global singleton
# Initialize with settings if available
try:
    llm_provider = settings.selected_llm
    llm = get_llm_adapter(
        provider=llm_provider,
        api_key=settings.openai_api_key if llm_provider == 'openai' else settings.anthropic_api_key,
        model=settings.openai_model if llm_provider == 'openai' else "claude-3-sonnet"
    )
    intelligence_aggregator = MarketIntelligence(llm)
except Exception:
    intelligence_aggregator = MarketIntelligence()
