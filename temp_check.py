import requests

for path in ['/', '/login', '/health', '/dashboard']:
    try:
        response = requests.get('http://127.0.0.1:5000' + path, timeout=10)
        print(path, response.status_code, response.headers.get('content-type'))
    except Exception as exc:
        print(path, 'ERROR', exc)
