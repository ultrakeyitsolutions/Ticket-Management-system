import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.test import Client
from tickets.models import Ticket

User = get_user_model()
user = None
for u in User.objects.filter(is_active=True).order_by('id'):
    if Ticket.objects.filter(created_by=u, status__in=['Open','In Progress']).exists():
        user = u
        break
if not user:
    raise SystemExit('no user with editable ticket')

client = Client()
client.force_login(user)

ticket = Ticket.objects.filter(created_by=user, status__in=['Open','In Progress']).first()
url = f'/dashboard/user-dashboard/ticket/{ticket.ticket_id}/edit/'
print('USER', user.username, 'TICKET', ticket.ticket_id, 'URL', url)

get_resp = client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('GET', get_resp.status_code, get_resp['Content-Type'][:60])
if get_resp.status_code != 200:
    print(get_resp.content.decode('utf-8','replace')[:1000])

post_data = {
    'title': ticket.title,
    'description': ticket.description,
    'priority': ticket.priority,
    'category': ticket.category or 'General',
}
post_resp = client.post(url, post_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print('POST status', post_resp.status_code)
print('POST content:', post_resp.content.decode('utf-8','replace')[:2000])
print('POST content-type', post_resp.headers.get('Content-Type'))
