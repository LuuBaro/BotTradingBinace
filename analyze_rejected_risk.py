import sqlite3
import json

conn = sqlite3.connect('data/trading.db')
cursor = conn.cursor()

# Get rejected ENTRY decisions
cursor.execute('''
    SELECT 
        decision_json,
        order_spec,
        risk_assessment,
        risk_approval_reason,
        timestamp
    FROM decisions 
    WHERE decision_type = 'ENTRY' 
    AND risk_passed = 0
    ORDER BY timestamp DESC
    LIMIT 3
''')

rows = cursor.fetchall()
for i, row in enumerate(rows, 1):
    print(f'\n===== REJECTED ENTRY #{i} ({row[4]}) =====')
    
    # Parse JSON fields
    decision = json.loads(row[0]) if row[0] else {}
    order_spec = json.loads(row[1]) if row[1] else {}
    risk_assessment = json.loads(row[2]) if row[2] else {}
    
    print(f'Order Spec: {json.dumps(order_spec, indent=2)}')
    print(f'\nRisk Assessment: {json.dumps(risk_assessment, indent=2)}')
    print(f'\nRejection Reason: {row[3]}')
    
    # Calculate risk
    if order_spec and 'entry_price' in order_spec:
        entry = float(order_spec.get('entry_price', 0))
        sl = float(order_spec.get('stop_loss', 0))
        tp = float(order_spec.get('take_profit', 0))
        
        if risk_assessment and 'size_pct' in risk_assessment:
            size_pct = float(risk_assessment['size_pct']) / 100  # Convert to decimal
            leverage = int(risk_assessment.get('leverage', 1))
            
            print(f'\nMANUAL CALCULATION:')
            print(f'  Entry: ${entry}')
            print(f'  Stop Loss: ${sl}')
            print(f'  Take Profit: ${tp}')
            print(f'  Size PCT: {size_pct*100}%')
            print(f'  Leverage: {leverage}x')
            
            if sl > 0 and entry > 0:
                risk_per_unit = abs(entry - sl)
                print(f'  Risk per unit: ${risk_per_unit:.4f}')
                print(f'  Distance to SL: {(risk_per_unit/entry)*100:.2f}%')
                
                # Assume balance $100
                balance = 100
                quantity = (balance * size_pct * leverage) / entry
                total_risk = risk_per_unit * quantity
                risk_pct = (total_risk / balance) * 100
                
                print(f'  With balance=$100:')
                print(f'    Quantity: {quantity:.4f}')
                print(f'    Total Risk: ${total_risk:.2f}')
                print(f'    Risk PCT: {risk_pct:.1f}%')

conn.close()
