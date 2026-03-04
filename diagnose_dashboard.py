import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, desc, text
from packages.shared.models import Decision, Position
from packages.shared.config import settings

async def diagnose():
    print("=" * 60)
    print("CHẨN ĐOÁN HỆ THỐNG")
    print("=" * 60)
    
    # 1. Kiểm tra API Keys
    print("\n1. BINANCE API CONFIGURATION")
    print(f"   API Key: {settings.binance_api_key}")
    print(f"   API Secret: {settings.binance_api_secret}")
    print(f"   Testnet: {settings.binance_testnet}")
    
    # Kiểm tra xem keys có bị mask không
    is_masked = '***' in settings.binance_api_key or '***' in settings.binance_api_secret
    if is_masked:
        print("   ⚠️  CẢNH BÁO: API Keys đang bị MASK (ẩn) - không thể kết nối Binance!")
        print("   💡 Giải pháp: Nhập API keys thật vào Settings page")
    else:
        print("   ✅ API Keys có vẻ hợp lệ")
    
    # Kiểm tra mode sẽ được hiển thị
    mode = "Live" if (settings.binance_api_key and settings.binance_api_secret) else "Demo"
    print(f"\n   Mode hiển thị sẽ là: {mode}")
    
    # 2. Kiểm tra Decisions
    print("\n2. LIVE INTENT (DECISIONS)")
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Decision).order_by(desc(Decision.timestamp)).limit(5)
        )
        decisions = result.scalars().all()
        
        if not decisions:
            print("   ⚠️  Không có decision nào trong database!")
            print("   💡 Worker chưa tạo decision hoặc chưa chạy")
        else:
            print(f"   Tìm thấy {len(decisions)} decisions gần nhất:")
            for i, d in enumerate(decisions, 1):
                print(f"\n   [{i}] Decision {d.trace_id[:12]}...")
                # Get attributes from decision object
                attrs = [attr for attr in dir(d) if not attr.startswith('_')]
                decision_data = {attr: getattr(d, attr, None) for attr in ['decision', 'symbol', 'confidence', 'rationale', 'timestamp'] if hasattr(d, attr)}
                print(f"       Decision: {decision_data.get('decision', 'N/A')}")
                print(f"       Symbol: {decision_data.get('symbol', 'N/A')}")
                print(f"       Confidence: {decision_data.get('confidence', 0):.1%}" if decision_data.get('confidence') else "       Confidence: N/A")
                print(f"       Rationale: {decision_data.get('rationale', '')[:80] if decision_data.get('rationale') else '❌ NULL (sẽ hiện text mặc định)'}...")
                print(f"       Timestamp: {decision_data.get('timestamp', 'N/A')}")
    
    # 3. Kiểm tra Positions
    print("\n3. POSITIONS (Thời gian mở vị thế)")
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Position).order_by(desc(Position.opened_at)).limit(5)
        )
        positions = result.scalars().all()
        
        if not positions:
            print("   ⚠️  Không có vị thế nào trong database!")
        else:
            print(f"   Tìm thấy {len(positions)} vị thế:")
            for pos in positions:
                print(f"\n   - {pos.symbol} {pos.side}")
                print(f"     opened_at: {pos.opened_at if pos.opened_at else '❌ NULL'}")
                print(f"     status: {pos.status}")
                print(f"     quantity: {pos.quantity}")
    
    # 4. Check positions table schema
    print("\n4. DATABASE SCHEMA - POSITIONS TABLE")
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("PRAGMA table_info(positions)"))
        columns = result.fetchall()
        print("   Columns:")
        for col in columns:
            print(f"   - {col[1]}: {col[2]}")
    
    print("\n" + "=" * 60)
    print("KẾT LUẬN & GIẢI PHÁP")
    print("=" * 60)
    
    if is_masked:
        print("\n🔴 VẤN ĐỀ 1: API Keys bị mask")
        print("   → Mode sẽ hiển thị 'Demo' thay vì 'Live'")
        print("   → Cần nhập API keys thật từ Binance Testnet")
        print("   → Vào Settings page để update")
    
    if not decisions or not decisions[0].rationale:
        print("\n🔴 VẤN ĐỀ 2: Live Intent cố định")
        print("   → Không có decision mới hoặc rationale NULL")
        print("   → Worker có thể đang dùng Mock LLM")
        print("   → Kiểm tra SELECTED_LLM trong .env")
    
    print("\n")

if __name__ == "__main__":
    asyncio.run(diagnose())
