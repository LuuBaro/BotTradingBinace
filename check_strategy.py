"""
Kiểm tra chiến thuật hiện tại và tại sao không take profit
"""
import asyncio
from packages.shared.database import AsyncSessionFactory
from sqlalchemy import select, desc
from packages.shared.models import BotConfig, Decision, Position, PromptPack
from datetime import datetime, timedelta

async def check():
    async with AsyncSessionFactory() as session:
        print("\n" + "="*60)
        print("KIEM TRA CHIEN THUAT VA QUYET DINH")
        print("="*60)
        
        # 1. Kiểm tra BotConfig - Risk settings
        print("\n[1] BOT CONFIG - RISK SETTINGS")
        config_result = await session.execute(
            select(BotConfig).where(BotConfig.is_active == True).limit(1)
        )
        config = config_result.scalars().first()
        
        if config and config.risk_json:
            print(f"  Risk Config:")
            risk = config.risk_json
            for key, value in risk.items():
                if 'take_profit' in key.lower() or 'stop_loss' in key.lower() or 'tp' in key.lower() or 'sl' in key.lower():
                    print(f"    {key}: {value}")
        
        # 2. Kiểm tra Prompt Pack - Exit Strategy
        print("\n[2] PROMPT PACK - EXIT STRATEGY")
        pp_result = await session.execute(
            select(PromptPack).order_by(desc(PromptPack.created_at)).limit(1)
        )
        prompt_pack = pp_result.scalars().first()
        
        if prompt_pack:
            print(f"  Prompt Pack: {prompt_pack.name} v{prompt_pack.version}")
            content = prompt_pack.content_json
            if isinstance(content, dict):
                exit_playbook = content.get('exit_playbook')
                if exit_playbook:
                    print(f"\n  Exit Playbook:")
                    print(f"    Title: {exit_playbook.get('title', 'N/A')}")
                    print(f"    Desc: {exit_playbook.get('description', 'N/A')[:150]}...")
                    rules = exit_playbook.get('rules' , [])
                    if rules:
                        print(f"\n    Exit Rules ({len(rules)} rules):")
                        for i, rule in enumerate(rules[:5], 1):
                            rule_text = rule if isinstance(rule, str) else str(rule)
                            print(f"      {i}. {rule_text[:100]}...")
                else:
                    print("  ⚠️  Prompt pack không có exit_playbook!")
        else:
            print("  ⚠️  KHONG CO PROMPT PACK!")
        
        # 3. Kiểm tra Positions hiện tại
        print("\n[3] POSITIONS HIỆN TẠI")
        pos_result = await session.execute(select(Position))
        positions = pos_result.scalars().all()
        
        if positions:
            for pos in positions:
                print(f"\n  {pos.symbol} {pos.side}:")
                print(f"    Entry: ${pos.entry_price}")
                print(f"    Current PnL: ${pos.unrealized_pnl:.2f}")
                print(f"    Take Profit Price: ${pos.take_profit if pos.take_profit else 'NOT SET ⚠️'}")
                print(f"    Stop Loss Price: ${pos.stop_loss if pos.stop_loss else 'NOT SET ⚠️'}")
                
                if pos.unrealized_pnl > 0:
                    profit_pct = (pos.unrealized_pnl / (pos.entry_price * pos.qty)) * 100
                    print(f"    Profit %: {profit_pct:.2f}%")
        else:
            print("  ⚠️  Không có positions trong DB (nhưng UI hiện 3 positions!)")
        
        # 4. Kiểm tra 10 Decisions gần nhất
        print("\n[4] DECISIONS GẦN NHẤT (10 gần nhất)")
        dec_result = await session.execute(
            select(Decision).order_by(desc(Decision.timestamp)).limit(10)
        )
        decisions = dec_result.scalars().all()
        
        close_decisions = []
        for d in decisions:
            decision_type = d.decision_type or "N/A"
            rationale_preview = (d.rationale[:80] if d.rationale else "No rationale")
            print(f"\n  [{d.timestamp.strftime('%H:%M:%S')}] {decision_type}")
            print(f"    Rationale: {rationale_preview}...")
            print(f"    Confidence: {d.confidence:.1%}")
            print(f"    Status: {d.status}")
            
            if decision_type in ['EXIT', 'CLOSE']:
                close_decisions.append(d)
        
        # 5. Phân tích
        print("\n" + "="*60)
        print("PHÂN TÍCH & KẾT LUẬN")
        print("="*60)
        
        print("\n🔍 NGUYÊN NHÂN BOT KHÔNG CẮT LỜI:")
        
        if not positions:
            print("  ❌ Positions không có trong database")
            print("     → UI hiện 3 positions nhưng DB không có")
            print("     → Cần sync positions từ Binance vào DB")
        
        if not prompt_pack:
            print("  ❌ Không có Prompt Pack active")
            print("     → AI không có chiến thuật exit rõ ràng")
        
        if not close_decisions:
            print("  ❌ Không có decision EXIT/CLOSE nào trong 10 decisions gần nhất")
            print("     → AI không đề xuất đóng vị thế")
            print("     → Có thể do:")
            print("        1. Prompt thiếu chi tiết về take profit %")
            print("        2. AI đang theo chiến thuật 'let winners run'")
            print("        3. Không có điều kiện kỹ thuật để exit")
        
        if positions and not any(p.take_profit for p in positions):
            print("  ❌ Positions không có Take Profit price được set")
            print("     → Risk engine không có target để tự động close")
        
        print("\n💡 GIẢI PHÁP:")
        print("  1. Kiểm tra prompt pack - thêm exit rules rõ ràng")
        print("  2. Set take_profit price khi mở vị thế")
        print("  3. Cấu hình risk engine để tự động close khi đạt target")
        print("  4. Manual close từ UI nếu cần")

if __name__ == "__main__":
    asyncio.run(check())
