import urllib.request
url = 'http://127.0.0.1:8002/dashboard/user-dashboard/ticket/SEC-TCK-001/edit/'
req = urllib.request.Request(url, headers={'X-Requested-With': 'XMLHttpRequest'})
with urllib.request.urlopen(req) as r:
    print('STATUS', r.status)
    print('CT', r.headers.get('Content-Type'))
    print(r.read(500).decode('utf-8', 'replace'))
