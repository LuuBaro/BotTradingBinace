import requests
import json

# Login to get token
login_response = requests.post(
    'http://localhost:8001/api/auth/login',
    json={'username': 'admin', 'password': 'admin'}
)

if login_response.status_code == 200:
    data = login_response.json()
    token = data['access_token']
    print("✅ Login successful!")
    print(f"\n🔑 Access Token:")
    print(f"{token}\n")
    
    # Test with token
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get positions
    pos_response = requests.get('http://localhost:8001/api/positions', headers=headers)
    print(f"📍 Positions ({pos_response.status_code}):")
    positions = pos_response.json()
    for p in positions:
        print(f"  - {p['symbol']} {p['side']} {p['qty']} @ {p['entry_price']}")
    
    # Get orders
    ord_response = requests.get('http://localhost:8001/api/orders', headers=headers)
    print(f"\n📦 Orders ({ord_response.status_code}): {len(ord_response.json())} items")
    
    print("\n" + "="*60)
    print("🚀 To access the dashboard:")
    print("="*60)
    print("1. Open http://localhost:3001 in your browser")
    print("2. Login with:")
    print("   Username: admin")
    print("   Password: admin")
    print("\nOr manually set the token in browser DevTools (F12):")
    print(f'   localStorage.setItem("auth_token", "{token}")')
    print("   localStorage.setItem("auth_user", \'{{\"id":"user_admin_001","username":"admin","role":"admin"}}\')")
    print("   window.location.reload()")
else:
    print(f"❌ Login failed: {login_response.status_code}")
    print(login_response.text)
