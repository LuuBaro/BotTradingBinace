import urllib.request
import json
import urllib.error

req = urllib.request.Request(
    'http://localhost:8000/api/auth/login', 
    data=json.dumps({'username': 'admin', 'password': 'admin'}).encode('utf-8'), 
    headers={'Content-Type': 'application/json'}
)
try:
    print(urllib.request.urlopen(req).read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print('ERROR', e.code, e.read().decode('utf-8'))
