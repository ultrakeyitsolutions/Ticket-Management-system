from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import models
from django.http import HttpResponse, Http404, JsonResponse
from django.views.generic import View
from .models import Ticket, MutedChat, TicketAttachment, TicketStatusHistory, TicketComment, ChatMessageAttachment
from .forms import TicketForm
from .serializers import DashboardStatsSerializer, RecentTicketSerializer, TicketSerializer, TicketCommentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Avg
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import mimetypes
import os


# ---------------------------------------------------------------------------
# Helper: get a user's role name safely (returns '' if no profile/role)
# ---------------------------------------------------------------------------
def get_role_name(user):
    profile = getattr(user, 'userprofile', None)
    role = getattr(profile, 'role', None)
    return getattr(role, 'name', '').lower()


def record_status_change(ticket, old_status, new_status, changed_by_user):
    """Record a ticket status change in the audit trail."""
    if old_status != new_status:
        TicketStatusHistory.objects.create(
            ticket=ticket,
            old_status=old_status or '',
            new_status=new_status,
            changed_by=changed_by_user
        )


# ---------------------------------------------------------------------------
# Ticket CRUD views
# ---------------------------------------------------------------------------

def ticket_list(request):
    if request.user.is_authenticated:
        role = get_role_name(request.user)
        if role == 'superadmin':
            return redirect('superadmin:superadmin_tickets')
        elif role == 'admin':
            tickets = Ticket.objects.all()
        else:
            tickets = Ticket.objects.filter(created_by=request.user)
    else:
        tickets = Ticket.objects.none()
    return render(request, "ticket_list.html", {"tickets": tickets})


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            if ticket.category == "Others":
                other_value = request.POST.get("category_other", "").strip()
                if other_value:
                    ticket.category = other_value
            ticket.created_by = request.user
            ticket.save()

            record_status_change(ticket, "Created", ticket.status, request.user)

            files = request.FILES.getlist('attachments')
            for f in files:
                TicketAttachment.objects.create(ticket=ticket, file=f)

            messages.success(request, "Ticket created successfully!")
            return redirect("dashboards:user_dashboard_page", page="tickets")
    else:
        form = TicketForm()
    return render(request, "ticket_form.html", {"form": form})


@login_required
def ticket_edit(request, ticket_id):
    # FIX: look up by ticket_id (e.g. "TCKT-DF01E584"), not integer pk
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    # FIX: safe permission check – no AttributeError if userprofile is missing
    role = get_role_name(request.user)
    if request.user != ticket.created_by and role != "admin":
        messages.error(request, "You don't have permission to edit this ticket.")
        return redirect("tickets:ticket_list")

    if request.method == "POST":
        old_status = ticket.status
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            updated_ticket = form.save()
            record_status_change(updated_ticket, old_status, updated_ticket.status, request.user)
            messages.success(request, "Ticket updated successfully!")
            return redirect("dashboards:admin_dashboard_page", page="tickets.html")
    else:
        form = TicketForm(instance=ticket)

    return render(request, "ticket_form.html", {"form": form, "ticket": ticket})


@login_required
def ticket_delete(request, ticket_id):
    # FIX: look up by ticket_id string
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    role = get_role_name(request.user)
    if request.user != ticket.created_by and role != "admin":
        messages.error(request, "You don't have permission to delete this ticket.")
        return redirect("tickets:ticket_list")

    ticket.delete()
    messages.success(request, "Ticket deleted successfully!")
    return redirect("dashboards:admin_dashboard_page", page="tickets.html")


@login_required
def ticket_detail(request, ticket_id):
    # FIX: look up by ticket_id string
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    if not can_view_ticket(request.user, ticket):
        messages.error(request, "You don't have permission to view this ticket.")
        return redirect('tickets:ticket_list')

    role = get_role_name(request.user)
    if request.user.is_staff or role in ['admin', 'superadmin']:
        comments = ticket.comments.all().select_related('author')
    else:
        comments = ticket.comments.filter(
            models.Q(is_internal=False) | models.Q(author=request.user)
        ).select_related('author')

    context = {
        'ticket': ticket,
        'comments': comments,
        'user': request.user,
    }
    return render(request, 'ticket_detail.html', context)


def can_view_ticket(user, ticket):
    if ticket.created_by == user:
        return True
    if ticket.assigned_to == user:
        return True
    if user.is_staff:
        return True
    return False


# ---------------------------------------------------------------------------
# REST API views
# ---------------------------------------------------------------------------

class DashboardStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.now().date()
        total_tickets = Ticket.objects.count()
        open_tickets = Ticket.objects.filter(status="Open").count()
        resolved_today = Ticket.objects.filter(status="Resolved", updated_at__date=today).count()
        avg_rating = 0

        distribution = {
            "open": open_tickets,
            "in_progress": Ticket.objects.filter(status="In Progress").count(),
            "resolved": Ticket.objects.filter(status="Resolved").count(),
        }

        data = {
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "resolved_today": resolved_today,
            "avg_rating": round(avg_rating, 1),
            "distribution": distribution,
        }

        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)


class RecentTicketsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        recent = Ticket.objects.order_by("-created_at")[:10]
        serializer = RecentTicketSerializer(recent, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class TicketListCreateView(APIView):
    authentication_classes = []

    def get_permissions(self):
        return [AllowAny()]

    def get(self, request):
        if not request.user.is_authenticated:
            qs = Ticket.objects.all().order_by("-created_at")
        elif (
            request.user.is_superuser
            or request.user.is_staff
            or get_role_name(request.user) == "admin"
        ):
            qs = Ticket.objects.all().order_by("-created_at")
        else:
            qs = Ticket.objects.filter(created_by=request.user).order_by("-created_at")
        serializer = TicketSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TicketSerializer(data=request.data)
        if serializer.is_valid():
            django_user = getattr(getattr(request, "_request", None), "user", None)

            creator = None
            customer_name = (
                request.data.get('customer') or request.data.get('customer_username') or ''
            ).strip()

            if customer_name:
                creator, _ = User.objects.get_or_create(
                    username=customer_name, defaults={'email': ''}
                )
                if not creator.has_usable_password():
                    creator.set_unusable_password()
                    creator.save()
            elif django_user and django_user.is_authenticated:
                creator = django_user
            else:
                guest, created = User.objects.get_or_create(
                    username='guest', defaults={'email': ''}
                )
                if created:
                    guest.set_unusable_password()
                    guest.save()
                creator = guest

            ticket = serializer.save(created_by=creator)

            record_status_change(
                ticket, None, ticket.status,
                django_user if django_user and django_user.is_authenticated else creator
            )

            try:
                if django_user and getattr(django_user, 'is_authenticated', False):
                    if get_role_name(django_user) == 'agent':
                        ticket.assigned_to = django_user
                        ticket.save(update_fields=['assigned_to'])
            except Exception:
                pass

            out = TicketSerializer(ticket)
            return Response(out.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TicketStatusUpdateView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def patch(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        new_status = request.data.get("status")
        valid_status = [c[0] for c in Ticket.STATUS_CHOICES]
        if new_status not in valid_status:
            return Response({"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        old_status = ticket.status
        ticket.status = new_status
        ticket.save()

        django_user = getattr(getattr(request, "_request", None), "user", None)
        changed_by_user = django_user if django_user and django_user.is_authenticated else None
        record_status_change(ticket, old_status, new_status, changed_by_user)

        return Response({"status": ticket.status})


class MutedChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({'detail': 'contact_id is required'}, status=400)
        try:
            contact = User.objects.get(id=contact_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=404)
        if MutedChat.objects.filter(user=request.user, contact=contact).exists():
            return Response({'detail': 'Already muted'}, status=400)
        MutedChat.objects.create(user=request.user, contact=contact)
        return Response({'detail': 'Muted'}, status=201)

    def delete(self, request):
        contact_id = request.data.get('contact_id') or request.query_params.get('contact_id')
        if not contact_id:
            return Response({'detail': 'contact_id is required'}, status=400)
        try:
            contact = User.objects.get(id=contact_id)
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=404)
        qs = MutedChat.objects.filter(user=request.user, contact=contact)
        if qs.exists():
            qs.delete()
            return Response({'detail': 'Unmuted'}, status=200)
        return Response({'detail': 'Not muted'}, status=404)


# ---------------------------------------------------------------------------
# Ticket Comment API views
# ---------------------------------------------------------------------------

class TicketCommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        try:
            ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
            if not self._can_view(request.user, ticket):
                return Response({'detail': 'Permission denied'}, status=403)

            role = get_role_name(request.user)
            if request.user.is_staff or role in ['admin', 'superadmin']:
                comments = ticket.comments.all().select_related('author')
            else:
                comments = ticket.comments.filter(
                    models.Q(is_internal=False) | models.Q(author=request.user)
                ).select_related('author')

            serializer = TicketCommentSerializer(comments, many=True)
            return Response({'success': True, 'comments': serializer.data})
        except Exception as e:
            return Response({'detail': str(e)}, status=500)

    def post(self, request, ticket_id):
        try:
            ticket = get_object_or_404(Ticket, ticket_id=ticket_id)
            if not self._can_comment(request.user, ticket):
                return Response({'detail': 'Permission denied'}, status=403)

            content = request.data.get('content', '').strip()
            is_internal = request.data.get('is_internal', False)

            if not content:
                return Response({'detail': 'Content is required'}, status=400)
            if is_internal and not request.user.is_staff:
                return Response({'detail': 'Only staff can create internal comments'}, status=403)

            comment = TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                content=content,
                is_internal=is_internal
            )
            serializer = TicketCommentSerializer(comment)
            return Response({'success': True, 'comment': serializer.data}, status=201)
        except Exception as e:
            return Response({'detail': str(e)}, status=500)

    def _can_view(self, user, ticket):
        return (
            ticket.created_by == user
            or ticket.assigned_to == user
            or user.is_staff
        )

    def _can_comment(self, user, ticket):
        return self._can_view(user, ticket)


class TicketCommentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, ticket_id, comment_id):
        try:
            comment = get_object_or_404(TicketComment, id=comment_id, ticket__ticket_id=ticket_id)
            if not self._can_edit(request.user, comment):
                return Response({'detail': 'Permission denied'}, status=403)

            content = request.data.get('content', '').strip()
            if not content:
                return Response({'detail': 'Content is required'}, status=400)

            comment.content = content
            comment.save()
            serializer = TicketCommentSerializer(comment)
            return Response({'success': True, 'comment': serializer.data})
        except Exception as e:
            return Response({'detail': str(e)}, status=500)

    def delete(self, request, ticket_id, comment_id):
        try:
            comment = get_object_or_404(TicketComment, id=comment_id, ticket__ticket_id=ticket_id)
            if not self._can_delete(request.user, comment):
                return Response({'detail': 'Permission denied'}, status=403)

            comment.delete()
            return Response({'success': True, 'message': 'Comment deleted successfully'})
        except Exception as e:
            return Response({'detail': str(e)}, status=500)

    def _can_edit(self, user, comment):
        return (comment.author == user and comment.can_edit) or user.is_staff

    def _can_delete(self, user, comment):
        return comment.author == user or user.is_staff


# ---------------------------------------------------------------------------
# Chat attachment views
# ---------------------------------------------------------------------------

class ChatAttachmentView(LoginRequiredMixin, View):

    def get(self, request, attachment_id):
        attachment = get_object_or_404(ChatMessageAttachment, id=attachment_id)
        if not self._can_access(request.user, attachment):
            raise Http404("Attachment not found")

        file_path = attachment.file.path
        if not os.path.exists(file_path):
            raise Http404("File not found")

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type)

        filename = os.path.basename(file_path)
        if mime_type.startswith('image/') or mime_type == 'application/pdf':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        response['Cache-Control'] = 'public, max-age=3600'
        return response

    def _can_access(self, user, attachment):
        message = attachment.message
        return (
            user.is_staff
            or user.is_superuser
            or message.sender == user
            or message.recipient == user
        )


class ChatAttachmentDeleteView(LoginRequiredMixin, View):

    def delete(self, request, attachment_id):
        attachment = get_object_or_404(ChatMessageAttachment, id=attachment_id)
        if not self._can_delete(request.user, attachment):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        try:
            if attachment.file and hasattr(attachment.file, 'delete'):
                attachment.file.delete(save=False)
            attachment.delete()
            return JsonResponse({'success': True, 'message': 'Attachment deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def _can_delete(self, user, attachment):
        return attachment.message.sender == user or user.is_staff or user.is_superuser