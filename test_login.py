import requests
import json

resp = requests.post('http://localhost:8001/api/auth/login', json={'username': 'admin', 'password': 'password'})
print(f'Status: {resp.status_code}')
print(f'Response: {resp.text}')
if resp.status_code == 200:
    data = resp.json()
    if 'access_token' in data:
        print(f"\nToken: {data['access_token']}")
        
        # Now test positions endpoint with token
        headers = {'Authorization': f"Bearer {data['access_token']}"}
        pos_resp = requests.get('http://localhost:8001/api/positions', headers=headers)
        print(f"\nPositions Status: {pos_resp.status_code}")
        print(f"Positions: {pos_resp.json()}")
