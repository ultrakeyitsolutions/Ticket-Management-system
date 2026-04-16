import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.test import Client
from tickets.models import Ticket
from urllib.request import Request, urlopen

User = get_user_model()
u = User.objects.filter(username='testuser1').first() or User.objects.filter(is_active=True).first()
if not u:
    raise SystemExit('No user found')

c = Client()
c.force_login(u)
url = '/dashboard/user-dashboard/ticket/'
t = Ticket.objects.filter(created_by=u, status__in=['Open', 'In Progress']).first()
if not t:
    raise SystemExit('No ticket found for user')
url += t.ticket_id + '/edit/'
print('TICKET', t.ticket_id)
print('COOKIES', c.cookies.items())
headers = {
    'Cookie': '; '.join([f'{k}={v.value}' for k, v in c.cookies.items()]),
    'X-Requested-With': 'XMLHttpRequest'
}
req = Request('http://127.0.0.1:8000' + url, headers=headers)
try:
    with urlopen(req, timeout=10) as resp:
        print('STATUS', resp.status)
        body = resp.read(1000)
        print(body.decode('utf-8', errors='replace'))
except Exception as e:
    print('ERR', repr(e))
