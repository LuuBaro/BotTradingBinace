"""
Market Intelligence - Aggregates data from multiple sources (Simulated for Demo)
Simulates News, Blockchain Context, and Global Sentiments
"""
from datetime import datetime, timedelta
import random
from typing import Dict, List, Any

class MarketIntelligence:
    def __init__(self):
        self.last_update = datetime.utcnow()
        self.cached_intelligence = None

    def get_market_context(self) -> Dict[str, Any]:
        """Synthesize market intelligence from multiple simulated channels"""
        
        # Simulate refresh logic
        if not self.cached_intelligence or (datetime.utcnow() - self.last_update).total_seconds() > 600:
            self.cached_intelligence = self._generate_fresh_intelligence()
            self.last_update = datetime.utcnow()
            
        return self.cached_intelligence

    def _generate_fresh_intelligence(self) -> Dict[str, Any]:
        news_headlines = [
            "Fed ám chỉ lãi suất ổn định, thị trường kỳ vọng biến động thấp cho crypto.",
            "Phát hiện hoạt động on-chain gia tăng tại các ví cá voi ETH (+12% dòng tiền).",
            "Sự rõ ràng về quy định tại thị trường EU thúc đẩy tâm lý nhà đầu tư tổ chức.",
            "Tỷ lệ funding rate của Bitcoin trở lại mức cơ bản sau một đợt tăng vọt ngắn hạn.",
            "Mạng lưới Layer 2 chính ghi nhận khối lượng giao dịch kỷ lục, tín hiệu lạc quan cho hệ sinh thái.",
            "Dữ liệu từ sàn Binance cho thấy áp lực mua đang tăng dần tại vùng hỗ trợ $65k.",
            "Báo cáo mới nhất từ thị trường phái sinh cho thấy sự sụt giảm trong tỷ lệ đòn bẩy toàn cầu."
        ]
        
        blockchain_signals = [
            {"source": "On-Chain", "signal": "Tích lũy Cá voi (Whale Accumulation)", "strength": "Mạnh", "sentiment": "Lạc quan (Bullish)"},
            {"source": "Sàn Binance", "signal": "Dòng tiền Stablecoin chảy vào", "strength": "Trung bình", "sentiment": "Trung tính (Neutral)"},
            {"source": "Mạng lưới", "signal": "Phí Gas giảm mạnh", "strength": "Thấp", "sentiment": "Lạc quan (Bullish)"},
            {"source": "Thợ đào", "signal": "Hashrate đạt mức cao nhất mọi thời đại", "strength": "Mạnh", "sentiment": "Tăng trưởng dài hạn"},
            {"source": "Orderbook", "signal": "Tường mua dày đặc tại vùng hỗ trợ", "strength": "Mạnh", "sentiment": "Hỗ trợ mạnh"}
        ]
        
        global_sentiment = random.choice([72, 68, 75, 81, 65, 59])
        
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "global_sentiment_index": global_sentiment, # Fear & Greed simulated
            "market_bias": "TĂNG TRƯỞNG (BULLISH)" if global_sentiment > 65 else "TRUNG TÍNH (NEUTRAL)",
            "headlines": random.sample(news_headlines, 3),
            "signals": random.sample(blockchain_signals, 2),
            "ai_summary": "Neural Core xác định sự tích lũy cấp độ cao tại các vùng giá quan trọng trên Binance. Rủi ro được ổn định bởi các yếu tố vĩ mô và dòng tiền on-chain tích cực."
        }

# Global singleton
intelligence_aggregator = MarketIntelligence()
