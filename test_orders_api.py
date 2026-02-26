import urllib.request
import json
import urllib.error

# Login first
req = urllib.request.Request(
    'http://localhost:8000/api/auth/login', 
    data=json.dumps({'username': 'admin', 'password': 'admin'}).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)
try:
    auth_resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    token = auth_resp['access_token']
except urllib.error.HTTPError as e:
    print('ERROR login:', e.code, e.read().decode('utf-8'))
    exit(1)

# Get orders
req = urllib.request.Request(
    'http://localhost:8000/api/orders', 
    headers={'Authorization': f'Bearer {token}'}
)
try:
    print(urllib.request.urlopen(req).read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('ERROR orders:', e.code, e.read().decode('utf-8'))
