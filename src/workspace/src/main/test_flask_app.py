import requests
response = requests.get('http://localhost:55384/hello')
print(response.json())
assert response.status_code == 200
assert response.json() == {"message": "Hello from Antigravity Agent"}