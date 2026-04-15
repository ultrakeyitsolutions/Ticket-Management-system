from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.core.models import Ticket
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check agent performance data'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Get all unique statuses
        statuses = Ticket.objects.values_list('status', flat=True).distinct()
        self.stdout.write("All ticket statuses in database:")
        for status in statuses:
            count = Ticket.objects.filter(status=status).count()
            self.stdout.write(f"  {status}: {count} tickets")

        # Check today's tickets
        self.stdout.write(f"\nTickets updated today ({today}):")
        for status in statuses:
            count = Ticket.objects.filter(status=status, updated_at__date=today).count()
            if count > 0:
                self.stdout.write(f"  {status}: {count} tickets")

        # Check agent users
        agent_users = User.objects.filter(is_staff=True)
        self.stdout.write(f"\nAgent users:")
        for agent in agent_users:
            self.stdout.write(f"  {agent.username} (ID: {agent.id})")
            
            # Check tickets assigned to this agent
            assigned = Ticket.objects.filter(assigned_to=agent)
            self.stdout.write(f"    Total assigned: {assigned.count()}")
            
            # Check resolved/closed today
            resolved_today = assigned.filter(status__in=['Resolved', 'Closed'], updated_at__date=today).count()
            self.stdout.write(f"    Resolved/Closed today: {resolved_today}")
            
            # Show recent tickets
            recent = assigned.filter(updated_at__date=today).values('ticket_id', 'status', 'updated_at')
            for ticket in recent:
                self.stdout.write(f"      Ticket {ticket['ticket_id']}: {ticket['status']} at {ticket['updated_at']}")
