#!/usr/bin/env python3
"""
Check current bot activity and AI decision status
"""
import asyncio
import json
from datetime import datetime, timedelta
from packages.shared.models import Decision, Position, Order
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, desc

async def main():
    print("=" * 80)
    print("🤖 KIỂM TRA HOẠT ĐỘNG CỦA BOT")
    print("=" * 80)
    print()
    
    async with AsyncSessionFactory() as session:
        # 1. Check recent decisions
        print("📊 QUYẾT ĐỊNH AI GẦN ĐÂY (Last 10 decisions)")
        print("-" * 80)
        result = await session.execute(
            select(Decision)
            .order_by(desc(Decision.timestamp))
            .limit(10)
        )
        decisions = result.scalars().all()
        
        if not decisions:
            print("❌ KHÔNG CÓ QUYẾT ĐỊNH NÀO!")
            print("   → Worker có thể không chạy hoặc bị lỗi")
        else:
            latest = decisions[0]
            time_diff = datetime.utcnow() - latest.timestamp
            
            print(f"✓ Tìm thấy {len(decisions)} quyết định")
            print(f"✓ Quyết định mới nhất: {time_diff.seconds // 60} phút trước")
            print()
            
            for i, dec in enumerate(decisions[:5], 1):
                mins_ago = int((datetime.utcnow() - dec.timestamp).total_seconds() // 60)
                
                # Extract from decision_json
                dec_data = dec.decision_json or {}
                action = dec_data.get('action', 'N/A')
                symbol = dec_data.get('symbol', 'N/A')
                
                print(f"{i}. {symbol:10s} | {action:6s} | "
                      f"Confidence: {dec.confidence*100:.1f}% | "
                      f"{mins_ago}m ago")
            
            print()
            
            if time_diff.total_seconds() > 600:  # > 10 minutes
                print("⚠️  CẢNH BÁO: Quyết định cuối > 10 phút!")
                print("   → Worker có thể đã dừng hoặc bị lỗi")
            else:
                print("✅ Worker đang hoạt động (quyết định mới < 10 phút)")
        
        print()
        print("=" * 80)
        
        # 2. Check open positions
        print("📈 VỊ THẾ ĐANG MỞ (Open Positions)")
        print("-" * 80)
        result = await session.execute(select(Position))
        positions = result.scalars().all()
        
        if not positions:
            print("❌ KHÔNG CÓ VỊ THẾ NÀO ĐANG MỞ")
            print("   → Bot đang ở trạng thái HOLD (không trade)")
        else:
            print(f"✓ Có {len(positions)} vị thế đang mở:")
            for pos in positions:
                pnl = (pos.current_price - pos.entry_price) / pos.entry_price * 100 if hasattr(pos, 'current_price') and pos.current_price else 0
                if pos.side == 'SHORT':
                    pnl = -pnl
                print(f"  • {pos.symbol:10s} {pos.side:5s} @ {pos.entry_price:.2f} "
                      f"| PnL: {pnl:+.2f}%")
        
        print()
        print("=" * 80)
        
        # 3. Check recent orders
        print("📋 LỆNH GẦN ĐÂY (Recent Orders - Last 5)")
        print("-" * 80)
        result = await session.execute(
            select(Order)
            .order_by(desc(Order.created_at))
            .limit(5)
        )
        orders = result.scalars().all()
        
        if not orders:
            print("❌ KHÔNG CÓ LỆNH NÀO")
        else:
            for i, order in enumerate(orders, 1):
                mins_ago = int((datetime.utcnow() - order.created_at).total_seconds() // 60)
                print(f"{i}. {order.symbol:10s} | {order.side:5s} | "
                      f"Status: {order.status:10s} | {mins_ago}m ago")
        
        print()
        print("=" * 80)
        
        # 4. Analyze why no trades
        print("🔍 PHÂN TÍCH TẠI SAO KHÔNG VÀO LỆNH")
        print("-" * 80)
        
        if decisions:
            # Check recent decisions actions
            recent_actions = []
            for d in decisions[:10]:
                dec_data = d.decision_json or {}
                action = dec_data.get('action', 'UNKNOWN')
                recent_actions.append(action)
            
            hold_count = recent_actions.count('HOLD')
            open_count = recent_actions.count('OPEN')
            close_count = recent_actions.count('CLOSE')
            
            print(f"📊 Hành động trong 10 quyết định gần nhất:")
            print(f"   HOLD:  {hold_count} lần ({hold_count/len(recent_actions)*100:.0f}%)")
            print(f"   OPEN:  {open_count} lần ({open_count/len(recent_actions)*100:.0f}%)")
            print(f"   CLOSE: {close_count} lần ({close_count/len(recent_actions)*100:.0f}%)")
            print()
            
            if hold_count >= 8:
                print("⚠️  AI liên tục ra quyết định HOLD")
                print("   Lý do có thể:")
                print("   1. Confidence thấp (< ngưỡng vào lệnh)")
                print("   2. Market không có tín hiệu rõ ràng")
                print("   3. Đang ở giai đoạn sideways/ranging")
                print()
                
                # Check confidence levels
                avg_conf = sum(d.confidence for d in decisions[:10]) / len(decisions[:10])
                print(f"   Confidence trung bình: {avg_conf*100:.1f}%")
                
                if avg_conf < 0.7:
                    print(f"   → AI không tự tin (< 70%), nên chọn HOLD")
                    print(f"   → Đây là hành vi AN TOÀN, tránh trade khi không chắc chắn")
            
            elif open_count > 0:
                print("✅ AI đã ra quyết định OPEN gần đây")
                if not positions:
                    print("   Nhưng không có positions mở")
                    print("   → Có thể lệnh bị từ chối hoặc đã đóng ngay")
            
            # Check latest rationale
            if decisions[0].rationale:
                print()
                print("💭 Lý do quyết định mới nhất:")
                print(f'   "{decisions[0].rationale[:200]}..."')
        
        else:
            print("❌ Không có dữ liệu quyết định để phân tích")
            print("   → Worker có thể KHÔNG chạy!")

if __name__ == "__main__":
    asyncio.run(main())
