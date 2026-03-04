"""
Xem chi tiết các ENTRY decisions bị reject
"""
import sqlite3
import json

db_path = 'd:\\BotTradingBinace\\data\\trading.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n" + "="*80)
print("🔍 CHI TIẾT CÁC ENTRY BỊ REJECT")
print("="*80)

# Get rejected ENTRY decisions with full details
cursor.execute('''
    SELECT timestamp, decision_json, risk_approval_reason, order_spec, decision_type
    FROM decisions 
    WHERE decision_type = 'ENTRY' 
    AND risk_passed = 0
    ORDER BY timestamp DESC 
    LIMIT 5
''')

rejected = cursor.fetchall()

if not rejected:
    print("\n✅ Không có ENTRY nào bị reject gần đây")
else:
    print(f"\n❌ Tìm thấy {len(rejected)} ENTRY bị reject:\n")
    
    for i, (ts, decision_json_str, reason, order_spec_str, dtype) in enumerate(rejected, 1):
        print(f"\n{'='*80}")
        print(f"#{i} - {ts[:19]}")
        print(f"{'='*80}")
        print(f"Lý do reject: {reason}\n")
        
        # Parse decision JSON
        if decision_json_str:
            try:
                decision = json.loads(decision_json_str)
                
                # Order spec
                if 'order_spec' in decision and decision['order_spec']:
                    spec = decision['order_spec']
                    print("📋 Order Specification:")
                    print(f"   Symbol: {spec.get('symbol', 'N/A')}")
                    print(f"   Side: {spec.get('side', 'N/A')}")
                    print(f"   Quantity: {spec.get('quantity', 'N/A')}")
                    print(f"   Entry Price: ${spec.get('entry_price', 'N/A')}")
                    print(f"   Stop Loss: ${spec.get('stop_loss_price', 'N/A')}")
                    print(f"   Take Profit: {spec.get('take_profit_prices', 'N/A')}")
                    print(f"   Leverage: {spec.get('leverage', 'N/A')}x\n")
                    
                    # Calculate position value
                    qty = spec.get('quantity', 0)
                    price = spec.get('entry_price', 0)
                    lev = spec.get('leverage', 1)
                    
                    if qty and price and lev:
                        position_value = qty * price
                        margin_required = position_value / lev
                        print(f"💰 Tính toán:")
                        print(f"   Position Value: ${position_value:,.2f}")
                        print(f"   Margin Required: ${margin_required:,.2f}")
                        print(f"   (với leverage {lev}x)\n")
                
                # Risk assessment
                if 'risk_assessment' in decision and decision['risk_assessment']:
                    risk = decision['risk_assessment']
                    print("🛡️ Risk Assessment:")
                    print(f"   Position %: {risk.get('position_pct', 'N/A')}")
                    print(f"   Risk/Reward: {risk.get('risk_reward_ratio', 'N/A')}")
                    print(f"   Expected Profit: ${risk.get('expected_profit_usd', 'N/A')}\n")
                
            except json.JSONDecodeError:
                print("   ⚠️  Không parse được decision JSON")

# Check current balance
print("\n" + "="*80)
print("💵 WALLET BALANCE:")
print("="*80)

cursor.execute('''
    SELECT available_balance, total_balance 
    FROM bot_config 
    ORDER BY id DESC 
    LIMIT 1
''')

balance_row = cursor.fetchone()
if balance_row:
    avail, total = balance_row
    print(f"   Available: ${avail:,.2f}")
    print(f"   Total: ${total:,.2f}")
else:
    print("   ⚠️  Không tìm thấy balance info")

# Check risk config relevant to position sizing
print("\n" + "="*80)
print("⚙️ RISK CONFIG (Position Sizing):")
print("="*80)

cursor.execute('SELECT risk_json FROM bot_config ORDER BY id DESC LIMIT 1')
risk_row = cursor.fetchone()
if risk_row:
    risk = json.loads(risk_row[0])
    print(f"   max_position_pct: {risk.get('max_position_pct', 'N/A')} (max % of balance per trade)")
    print(f"   max_position_per_symbol: {risk.get('max_position_per_symbol', 'N/A')}")
    print(f"   max_leverage: {risk.get('max_leverage', 'N/A')}")
    
    max_pos_pct = risk.get('max_position_pct', 0.2)
    if balance_row:
        max_margin = balance_row[0] * max_pos_pct  # available_balance * max_position_pct
        print(f"\n   → Max margin allowed per trade: ${max_margin:,.2f}")
        print(f"      (= {balance_row[0]:,.2f} × {max_pos_pct})")

conn.close()

print("\n" + "="*80)
print("💡 PHÂN TÍCH:")
print("="*80)
print("""
   VẤN ĐỀ: AI đang tính position size = 100% balance!
   
   Nguyên nhân có thể:
   1. 🐛 Bug trong PromptPack → AI không hiểu đúng risk params
   2. 📊 AI đang tính quantity sai (không cân nhắc max_position_pct)
   3. ⚙️ RiskEngine đang validate đúng, blocks unsafe orders
   
   GIẢI PHÁP:
   • Kiểm tra worker logs để thấy AI response
   • Xem AI có đang nhận được risk_params không
   • Có thể cần điều chỉnh prompt để AI hiểu rõ hơn về position sizing
   
   Hiện tại RiskEngine đang bảo vệ tốt → không để AI risk 100% balance ✅
""")
