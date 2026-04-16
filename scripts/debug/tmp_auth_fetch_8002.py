import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.test import Client
from tickets.models import Ticket
from urllib.request import Request, urlopen
from urllib.error import HTTPError

User = get_user_model()
u = User.objects.filter(username='testuser1').first() or User.objects.filter(is_active=True).first()
if not u:
    raise SystemExit('No user found')

c = Client()
c.force_login(u)

u_tickets = Ticket.objects.filter(created_by=u, status__in=['Open', 'In Progress'])
if not u_tickets.exists():
    raise SystemExit('No ticket found for user')
t = u_tickets.first()
url = '/dashboard/user-dashboard/ticket/' + t.ticket_id + '/edit/'
headers = {
    'Cookie': '; '.join([f'{k}={v.value}' for k, v in c.cookies.items()]),
    'X-Requested-With': 'XMLHttpRequest'
}
for port in (8002,):
    req = Request(f'http://127.0.0.1:{port}' + url, headers=headers)
    try:
        with urlopen(req, timeout=10) as resp:
            print(port, 'STATUS', resp.status)
            body = resp.read(1000).decode('utf-8', 'replace')
            print(body[:1000])
    except HTTPError as e:
        print(port, 'HTTPERROR', e.code)
        print(e.read(1000).decode('utf-8', 'replace')[:1000])
    except Exception as e:
        print(port, 'ERR', repr(e))
