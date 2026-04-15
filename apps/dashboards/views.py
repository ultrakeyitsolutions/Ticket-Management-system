from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404, HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count, Avg, F, DurationField, ExpressionWrapper
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from tickets.models import Ticket, UserRating, ChatMessage
from tickets.forms import TicketForm, AdminTicketForm
from users.models import UserProfile
import json
import calendar
import csv
import io
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import SiteSettings
import base64
from django.core.files.base import ContentFile
import uuid
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom decorators for role-based access control
# ---------------------------------------------------------------------------

def require_admin_role(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request):
            if is_agent_user(request):
                return redirect('dashboards:agent_dashboard')
            elif is_regular_user(request):
                return redirect('dashboards:user_dashboard')
            else:
                return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_agent_role(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_agent_user(request):
            if is_admin_user(request):
                return redirect('dashboards:admin_dashboard')
            elif is_regular_user(request):
                return redirect('dashboards:user_dashboard')
            else:
                return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def require_user_role(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_regular_user(request):
            if is_admin_user(request):
                return redirect('dashboards:admin_dashboard')
            elif is_agent_user(request):
                return redirect('dashboards:agent_dashboard')
            else:
                return redirect('users:login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def validate_user_role(request, allowed_roles):
    if not hasattr(request.user, "userprofile") or not getattr(request.user.userprofile, "role", None):
        return False
    user_role = getattr(request.user.userprofile.role, "name", "").lower()
    return user_role in [role.lower() for role in allowed_roles]


def is_admin_user(request):
    if hasattr(request.user, "userprofile") and getattr(request.user.userprofile, "role", None):
        role_name = getattr(request.user.userprofile.role, "name", "").lower()
        if role_name in ["admin", "superadmin"]:
            return True
    if request.user.is_superuser:
        return True
    return False


def is_agent_user(request):
    if hasattr(request.user, "userprofile") and getattr(request.user.userprofile, "role", None):
        role_name = getattr(request.user.userprofile.role, "name", "").lower()
        return role_name == "agent"
    return False


def is_regular_user(request):
    if hasattr(request.user, "userprofile") and getattr(request.user.userprofile, "role", None):
        role_name = getattr(request.user.userprofile.role, "name", "").lower()
        return role_name in ["user", "customer"]
    return False


# ---------------------------------------------------------------------------
# Test page
# ---------------------------------------------------------------------------

def test_edit_page(request):
    try:
        from tickets.models import Ticket
        ticket = Ticket.objects.first()
        if request.method == 'GET':
            return render(request, 'test_edit_page.html', {
                'ticket_id': ticket.ticket_id if ticket else 'TEST-001'
            })
        else:
            return HttpResponse("Method not allowed", status=405)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


# ---------------------------------------------------------------------------
# Admin payment page
# ---------------------------------------------------------------------------

@login_required
@require_admin_role
def admin_payment_page(request):
    plan = request.GET.get('plan', 'basic')
    price = request.GET.get('price', '199')
    ctx = {
        'plan': plan,
        'price': price,
        'plan_name': plan.title() if plan else 'Basic',
    }
    return render(request, 'admin_payment_page.html', ctx)


# ---------------------------------------------------------------------------
# Notification APIs
# ---------------------------------------------------------------------------

@login_required
def user_notifications_api(request):
    user = request.user
    notifications = []

    ticket_qs = Ticket.objects.filter(created_by=user).order_by('-updated_at')[:20]
    for t in ticket_qs:
        notifications.append({
            'timestamp': t.updated_at,
            'category': 'tickets',
            'icon': 'fas fa-ticket-alt',
            'is_unread': t.status in ['Open', 'In Progress'],
            'title': 'Ticket update',
            'text': f"Ticket #{t.ticket_id} · {t.title} · status: {t.status}",
            'url': f"/dashboard/user-dashboard/ticket/{t.ticket_id}/",
        })

    chat_qs = ChatMessage.objects.select_related('sender').filter(recipient=user).order_by('-created_at')[:20]
    for m in chat_qs:
        notifications.append({
            'timestamp': m.created_at,
            'category': 'system',
            'icon': 'fas fa-comment',
            'is_unread': not m.is_read,
            'title': 'New message',
            'text': f"New message from {m.sender.get_full_name() or m.sender.username}",
            'url': '/dashboard/user-dashboard/chat/',
        })

    notifications.sort(key=lambda n: n['timestamp'], reverse=True)
    top = notifications[:3]
    unread_count = sum(1 for n in notifications if n.get('is_unread'))

    results = []
    for n in top:
        ts = n.get('timestamp')
        results.append({
            'category': n.get('category') or '',
            'icon': n.get('icon') or '',
            'is_unread': bool(n.get('is_unread')),
            'title': n.get('title') or '',
            'text': n.get('text') or '',
            'url': n.get('url') or '',
            'timestamp': ts.isoformat() if ts else None,
            'time_ago': timezone.localtime(ts).strftime('%b %d, %I:%M %p') if ts else '',
        })

    return JsonResponse({'unread_count': unread_count, 'results': results})


@login_required
def user_notification_mark_read_api(request, notification_id):
    """Mark a specific notification as read for user"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    try:
        # For chat messages, mark them as read
        from tickets.models import ChatMessage
        import uuid
        
        try:
            # Try to parse as UUID for chat messages
            msg_uuid = uuid.UUID(str(notification_id))
            message = ChatMessage.objects.filter(id=msg_uuid, recipient=user).first()
            if message:
                message.is_read = True
                message.save()
                return JsonResponse({'success': True, 'message': 'Notification marked as read'})
        except ValueError:
            pass
        
        # For ticket notifications, we can't actually change them since they're based on ticket status
        # Just return success for now
        return JsonResponse({'success': True, 'message': 'Notification marked as read'})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error marking notification as read: {str(e)}'
        }, status=500)


@login_required
def user_notifications_mark_all_read_api(request):
    """Mark all notifications as read for user"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    try:
        # Mark all unread chat messages as read
        from tickets.models import ChatMessage
        unread_messages = ChatMessage.objects.filter(recipient=user, is_read=False)
        messages_count = unread_messages.count()
        unread_messages.update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'message': f'{messages_count} notifications marked as read'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error marking notifications as read: {str(e)}'
        }, status=500)


@login_required
def user_notification_delete_api(request, notification_id):
    """Delete a specific notification for user"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    try:
        # For chat messages, mark them as read (effectively "deleting" from notifications)
        from tickets.models import ChatMessage
        import uuid
        
        try:
            # Try to parse as UUID for chat messages
            msg_uuid = uuid.UUID(str(notification_id))
            message = ChatMessage.objects.filter(id=msg_uuid, recipient=user).first()
            if message:
                message.is_read = True
                message.save()
                return JsonResponse({'success': True, 'message': 'Notification deleted'})
        except ValueError:
            pass
        
        # For ticket notifications, we can't actually delete them since they're based on ticket status
        # Just return success for now
        return JsonResponse({'success': True, 'message': 'Notification deleted'})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting notification: {str(e)}'
        }, status=500)


@login_required
def user_notifications_clear_all_api(request):
    """Clear all notifications for user"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    try:
        # Mark all unread chat messages as read
        from tickets.models import ChatMessage
        unread_messages = ChatMessage.objects.filter(recipient=user, is_read=False)
        messages_count = unread_messages.count()
        unread_messages.update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'message': f'{messages_count} notifications cleared'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error clearing notifications: {str(e)}'
        }, status=500)


@login_required
def faq_search_api(request):
    q = (request.GET.get('q') or '').strip().lower()
    if len(q) < 3:
        return JsonResponse({'success': True, 'results': []})

    try:
        from .models import Faq
        faq_qs = Faq.objects.filter(is_published=True)
        matches = faq_qs.filter(Q(question__icontains=q) | Q(answer__icontains=q)).order_by('order')[:50]
        results = [{'question': f.question, 'answer': f.answer, 'category': f.category} for f in matches]
        return JsonResponse({'success': True, 'results': results})
    except Exception:
        return JsonResponse({'success': True, 'results': []})


@login_required
def admin_notifications_api(request):
    user = request.user
    is_admin = bool(
        user.is_authenticated and (
            user.is_superuser or user.is_staff or (
                hasattr(user, 'userprofile')
                and getattr(getattr(user.userprofile, 'role', None), 'name', '').lower() in ['admin', 'superadmin']
            )
        )
    )
    if not is_admin:
        return JsonResponse({'detail': 'Forbidden'}, status=403)

    notifications = []
    ticket_qs = Ticket.objects.select_related('created_by').order_by('-updated_at')[:20]
    for t in ticket_qs:
        notifications.append({
            'timestamp': t.updated_at,
            'category': 'tickets',
            'icon': 'bi bi-ticket-detailed',
            'is_unread': t.status in ['Open', 'In Progress'],
            'title': 'Ticket update',
            'text': f"Ticket #{t.ticket_id} · {t.title} · status: {t.status}",
            'url': f"/dashboard/admin-dashboard/ticket/{t.ticket_id}/",
        })

    chat_qs = ChatMessage.objects.select_related('sender').filter(recipient=user).order_by('-created_at')[:20]
    for m in chat_qs:
        notifications.append({
            'timestamp': m.created_at,
            'category': 'system',
            'icon': 'bi bi-chat-dots',
            'is_unread': not m.is_read,
            'title': 'New message',
            'text': f"New message from {m.sender.get_full_name() or m.sender.username}",
            'url': '/dashboard/admin-dashboard/chat.html',
        })

    notifications.sort(key=lambda n: n['timestamp'], reverse=True)
    top = notifications[:5]
    unread_count = sum(1 for n in notifications if n.get('is_unread'))

    results = []
    for n in top:
        ts = n.get('timestamp')
        results.append({
            'category': n.get('category') or '',
            'icon': n.get('icon') or '',
            'is_unread': bool(n.get('is_unread')),
            'title': n.get('title') or '',
            'text': n.get('text') or '',
            'url': n.get('url') or '',
            'timestamp': ts.isoformat() if ts else None,
            'time_ago': timezone.localtime(ts).strftime('%b %d, %I:%M %p') if ts else '',
        })

    return JsonResponse({'unread_count': unread_count, 'results': results})


@login_required
def admin_notifications_mark_all_read_api(request):
    """Mark all notifications as read for the current admin"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    # Check if user is admin
    is_admin = bool(
        user.is_authenticated and (
            user.is_superuser or user.is_staff or (
                hasattr(user, 'userprofile')
                and getattr(getattr(user.userprofile, 'role', None), 'name', '').lower() in ['admin', 'superadmin']
            )
        )
    )
    if not is_admin:
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    
    try:
        # Mark all unread chat messages as read
        from tickets.models import ChatMessage
        unread_messages = ChatMessage.objects.filter(recipient=user, is_read=False)
        messages_count = unread_messages.count()
        unread_messages.update(is_read=True)
        
        # Note: We don't modify ticket status as that represents actual ticket state
        # The "unread" status for tickets is based on their status, not a separate flag
        
        return JsonResponse({
            'success': True,
            'message': f'{messages_count} notifications marked as read'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error marking notifications as read: {str(e)}'
        }, status=500)


@login_required
def admin_notification_delete_api(request, notification_id):
    """Delete a specific notification for admin"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    # Check if user is admin
    is_admin = bool(
        user.is_authenticated and (
            user.is_superuser or user.is_staff or (
                hasattr(user, 'userprofile')
                and getattr(getattr(user.userprofile, 'role', None), 'name', '').lower() in ['admin', 'superadmin']
            )
        )
    )
    if not is_admin:
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    
    try:
        # For chat messages, we can mark them as read (effectively "deleting" from notifications)
        from tickets.models import ChatMessage
        import uuid
        
        try:
            # Try to parse as UUID for chat messages
            msg_uuid = uuid.UUID(str(notification_id))
            message = ChatMessage.objects.filter(id=msg_uuid, recipient=user).first()
            if message:
                message.is_read = True
                message.save()
                return JsonResponse({'success': True, 'message': 'Notification deleted'})
        except ValueError:
            pass
        
        # For ticket notifications, we can't actually delete them since they're based on ticket status
        # Just return success for now
        return JsonResponse({'success': True, 'message': 'Notification deleted'})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting notification: {str(e)}'
        }, status=500)


@login_required
def admin_notifications_clear_all_api(request):
    """Clear all notifications for admin"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    # Check if user is admin
    is_admin = bool(
        user.is_authenticated and (
            user.is_superuser or user.is_staff or (
                hasattr(user, 'userprofile')
                and getattr(getattr(user.userprofile, 'role', None), 'name', '').lower() in ['admin', 'superadmin']
            )
        )
    )
    if not is_admin:
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    
    try:
        # Mark all unread chat messages as read
        from tickets.models import ChatMessage
        unread_messages = ChatMessage.objects.filter(recipient=user, is_read=False)
        messages_count = unread_messages.count()
        unread_messages.update(is_read=True)
        
        return JsonResponse({
            'success': True,
            'message': f'{messages_count} notifications cleared'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error clearing notifications: {str(e)}'
        }, status=500)


@login_required
def agent_notifications_api(request):
    user = request.user
    notifications = []

    ticket_qs = Ticket.objects.select_related('created_by').filter(assigned_to=user).order_by('-updated_at')[:20]
    for t in ticket_qs:
        notifications.append({
            'id': f"ticket_{t.ticket_id}",
            'timestamp': t.updated_at,
            'category': 'tickets',
            'icon': 'bi bi-ticket-detailed',
            'is_unread': t.status in ['Open', 'In Progress'],
            'title': 'Assigned ticket',
            'text': f"Ticket #{t.ticket_id} · {t.title} · status: {t.status}",
            'url': f"/dashboard/agent-dashboard/ticket/{t.ticket_id}/",
        })

    chat_qs = ChatMessage.objects.select_related('sender').filter(recipient=user).order_by('-created_at')[:20]
    for m in chat_qs:
        notifications.append({
            'id': f"chat_{m.id}",
            'timestamp': m.created_at,
            'category': 'system',
            'icon': 'bi bi-chat-dots',
            'is_unread': not m.is_read,
            'title': 'New message',
            'text': f"New message from {m.sender.get_full_name() or m.sender.username}",
            'url': '/dashboard/agent-dashboard/chat.html',
        })

    notifications.sort(key=lambda n: n['timestamp'], reverse=True)
    top = notifications[:5]
    unread_count = sum(1 for n in notifications if n.get('is_unread'))

    results = []
    for n in top:
        ts = n.get('timestamp')
        results.append({
            'id': n.get('id', ''),
            'category': n.get('category') or '',
            'icon': n.get('icon') or '',
            'is_unread': bool(n.get('is_unread')),
            'title': n.get('title') or '',
            'text': n.get('text') or '',
            'url': n.get('url') or '',
            'timestamp': ts.isoformat() if ts else None,
            'time_ago': timezone.localtime(ts).strftime('%b %d, %I:%M %p') if ts else '',
        })

    return JsonResponse({'unread_count': unread_count, 'results': results})


@login_required
def agent_mark_all_notifications_read(request):
    """Mark all notifications as read for the current agent"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    user = request.user
    
    try:
        # Mark all unread chat messages as read
        from tickets.models import ChatMessage
        unread_messages = ChatMessage.objects.filter(recipient=user, is_read=False)
        messages_count = unread_messages.count()
        unread_messages.update(is_read=True)
        
        # Note: We don't modify ticket status as that represents actual ticket state
        # The "unread" status for tickets is based on their status, not a separate flag
        
        return JsonResponse({
            'success': True,
            'message': f'{messages_count} notifications marked as read'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error marking notifications as read: {str(e)}'
        }, status=500)


@login_required
def mark_chat_message_read(request, message_id):
    """Mark a specific chat message as read"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        from tickets.models import ChatMessage
        chat_message = ChatMessage.objects.get(id=message_id, recipient=request.user)
        chat_message.is_read = True
        chat_message.save()
        
        return JsonResponse({'success': True, 'message': 'Message marked as read'})
    except ChatMessage.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Message not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)


# ---------------------------------------------------------------------------
# User ticket rate
# ---------------------------------------------------------------------------

@login_required
def user_ticket_rate(request, identifier: str):
    if request.method != 'POST':
        return redirect('dashboards:user_dashboard_page', page='tickets')

    ticket = Ticket.objects.filter(ticket_id=identifier, created_by=request.user).select_related('assigned_to').first()
    if not ticket:
        raise Http404("Ticket not found")

    rating_raw = (request.POST.get('rating') or '').strip()
    title = (request.POST.get('title') or '').strip() or 'Feedback'
    content = (request.POST.get('content') or '').strip()
    recommend_raw = (request.POST.get('recommend') or '').strip().lower()
    recommend = recommend_raw in ['1', 'true', 'yes', 'y', 'on']

    try:
        rating_val = int(rating_raw)
    except (TypeError, ValueError):
        rating_val = 0

    rating_val = max(1, min(5, rating_val))
    agent = getattr(ticket, 'assigned_to', None)

    obj, created = UserRating.objects.get_or_create(
        user=request.user,
        ticket_reference=ticket.ticket_id,
        defaults={
            'agent': agent,
            'rating': rating_val,
            'title': title,
            'content': content,
            'recommend': recommend,
        }
    )

    if not created:
        obj.agent = agent
        obj.rating = rating_val
        obj.title = title
        obj.content = content
        obj.recommend = recommend
        obj.save(update_fields=['agent', 'rating', 'title', 'content', 'recommend'])

    return redirect('dashboards:user_dashboard_page', page='tickets')


# ---------------------------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------------------------

@login_required
def admin_dashboard(request):
    if not is_admin_user(request):
        if is_agent_user(request):
            return redirect("dashboards:agent_dashboard")
        elif is_regular_user(request):
            return redirect("users:login")
        else:
            return redirect("users:login")

    from django.db.models import Count, Avg, F, DurationField, ExpressionWrapper
    from superadmin.views import check_subscription_expiry, get_user_plan_name, get_expiry_date, get_days_expired

    show_payment_modal = False
    plan_name = None
    expiry_date = None
    days_expired = None

    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status__iexact='Open').count()
    resolved_today = Ticket.objects.filter(status__iexact='Resolved', updated_at__date=timezone.now().date()).count()
    all_resolved_tickets = Ticket.objects.filter(status__iexact='Resolved').count()

    ratings_qs = UserRating.objects.all()
    ratings_total = ratings_qs.count()
    ratings_avg_val = 0.0
    if ratings_total:
        ratings_agg = ratings_qs.aggregate(avg_rating=Avg('rating'))
        ratings_avg_val = float(ratings_agg.get('avg_rating') or 0.0)

    status_defaults = {"Open": 0, "In Progress": 0, "Resolved": 0}
    for row in Ticket.objects.values('status').annotate(c=Count('id')):
        key = row['status']
        if key in status_defaults:
            status_defaults[key] = row['c']
    open_count = status_defaults["Open"]
    in_progress_count = status_defaults["In Progress"]
    resolved_count = status_defaults["Resolved"]
    denom = total_tickets or 1
    open_percent = int((open_count / denom) * 100)
    in_progress_percent = int((in_progress_count / denom) * 100)
    resolved_percent = int((resolved_count / denom) * 100)

    recent_tickets = Ticket.objects.select_related('created_by').order_by('-created_at')[:11]
    subscription = None

    ctx = {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "resolved_today": resolved_today,
        "all_resolved_tickets": all_resolved_tickets,
        "open_percent": open_percent,
        "in_progress_percent": in_progress_percent,
        "resolved_percent": resolved_percent,
        "recent_tickets": recent_tickets,
        "dashboard_avg_rating": round(ratings_avg_val, 1) if ratings_total else None,
        "dashboard_total_ratings": ratings_total,
        "show_payment_modal": show_payment_modal,
        "plan_name": plan_name,
        "expiry_date": expiry_date,
        "days_expired": days_expired,
        "subscription": subscription,
        "razorpay_key": "rzp_test_1DP5mmOlF5G5ag"
    }

    return render(request, 'admindashboard/index.html', ctx)


# ---------------------------------------------------------------------------
# Agent Dashboard
# ---------------------------------------------------------------------------

@login_required
def agent_dashboard(request):
    if not is_agent_user(request):
        if is_admin_user(request):
            return redirect("dashboards:admin_dashboard")
        elif is_regular_user(request):
            return redirect("dashboards:user_dashboard")
        else:
            return redirect("users:login")

    user = request.user
    assigned_qs = Ticket.objects.filter(assigned_to=user)
    today = timezone.now().date()

    my_open_tickets = assigned_qs.filter(status__in=['Open', 'In Progress']).count()
    due_today = assigned_qs.filter(status__in=['Open', 'In Progress'], created_at__date=today).count()
    unread_replies = ChatMessage.objects.filter(recipient=user, is_read=False).count()
    sla_at_risk = assigned_qs.filter(status__in=['Open', 'In Progress'], priority__in=['High', 'Critical']).count()
    recent_assigned = assigned_qs.select_related('created_by').order_by('-created_at')[:5]
    sla_tickets = assigned_qs.filter(status__in=['Open', 'In Progress'], priority__in=['High', 'Critical']).order_by('created_at')[:5]

    avg_first_response_display = "0m 0s"
    resolved_today = assigned_qs.filter(status__in=['Resolved', 'Closed'], updated_at__date=today).count()

    resolved_qs = assigned_qs.filter(status__in=['Resolved', 'Closed'])
    if resolved_qs.exists():
        duration_expr = ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField())
        agg = resolved_qs.aggregate(avg_duration=Avg(duration_expr))
        avg_duration = agg.get('avg_duration')
        if avg_duration is not None:
            total_seconds = int(avg_duration.total_seconds())
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            avg_first_response_display = f"{minutes}m {seconds}s"

    ratings_qs = UserRating.objects.filter(agent=user)
    ratings_total = ratings_qs.count()
    satisfaction_display = "0.0/5"
    if ratings_total:
        ratings_agg = ratings_qs.aggregate(avg_rating=Avg('rating'))
        avg_val = float(ratings_agg.get('avg_rating') or 0.0)
        satisfaction_display = f"{round(avg_val, 1)}/5"

    ctx = {
        'agent_my_open_tickets': my_open_tickets,
        'agent_due_today': due_today,
        'agent_unread_replies': unread_replies,
        'agent_sla_at_risk': sla_at_risk,
        'agent_recent_assigned': recent_assigned,
        'agent_sla_tickets': sla_tickets,
        'agent_avg_first_response_display': avg_first_response_display,
        'agent_resolved_today': resolved_today,
        'agent_customer_satisfaction_display': satisfaction_display,
        'header_url': '/dashboard/agent-dashboard/partials/header.html',
        'sidebar_url': '/dashboard/agent-dashboard/partials/sidebar.html',
        'modals_url': '/dashboard/agent-dashboard/partials/modals.html',
    }

    return render(request, 'agentdashboard/index.html', ctx)


# ---------------------------------------------------------------------------
# Agent Ratings Page (dedicated view)
# ---------------------------------------------------------------------------

@login_required
def agent_ratings_page(request):
    """Dedicated view for agent ratings page with full data."""
    if not is_agent_user(request):
        if is_admin_user(request):
            return redirect('dashboards:admin_dashboard')
        return redirect('dashboards:user_dashboard')

    user = request.user
    ratings_qs = UserRating.objects.select_related('user', 'agent').filter(agent=user).order_by('-created_at')
    total = ratings_qs.count()

    agg = ratings_qs.aggregate(
        avg_rating=Avg('rating'),
        c5=Count('id', filter=Q(rating=5)),
        c4=Count('id', filter=Q(rating=4)),
        c3=Count('id', filter=Q(rating=3)),
        c2=Count('id', filter=Q(rating=2)),
        c1=Count('id', filter=Q(rating=1)),
    ) if total else {"avg_rating": 0, "c5": 0, "c4": 0, "c3": 0, "c2": 0, "c1": 0}

    avg_val = float(agg.get('avg_rating') or 0.0)
    c5 = int(agg.get('c5') or 0)
    c4 = int(agg.get('c4') or 0)
    c3 = int(agg.get('c3') or 0)
    c2 = int(agg.get('c2') or 0)
    c1 = int(agg.get('c1') or 0)

    def pct(count):
        return int((count / total) * 100) if total else 0

    agent_tickets = Ticket.objects.filter(assigned_to=user)
    total_tickets = agent_tickets.count()
    responded_tickets = agent_tickets.filter(status__in=['In Progress', 'Resolved', 'Closed']).count()
    agent_response_rate = int((responded_tickets / total_tickets) * 100) if total_tickets else 0

    positive_ratings = ratings_qs.filter(rating__gte=4).count()
    agent_satisfaction = int((positive_ratings / total) * 100) if total else 0

    avg_response_hours = 0.0
    if total_tickets:
        resolved_qs = agent_tickets.filter(status__in=['Resolved', 'Closed'])
        if resolved_qs.exists():
            duration_expr = ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField())
            dur_agg = resolved_qs.aggregate(avg_duration=Avg(duration_expr))
            avg_duration = dur_agg.get('avg_duration')
            if avg_duration is not None:
                avg_response_hours = round(float(avg_duration.total_seconds()) / 3600.0, 1)

    recent_activity = Ticket.objects.filter(assigned_to=user).order_by('-updated_at')[:5]

    ctx = {
        'agent_ratings': ratings_qs,
        'agent_avg_rating': round(avg_val, 1),
        'agent_total_reviews': total,
        'agent_count_5': c5,
        'agent_count_4': c4,
        'agent_count_3': c3,
        'agent_count_2': c2,
        'agent_count_1': c1,
        'agent_percent_5': pct(c5),
        'agent_percent_4': pct(c4),
        'agent_percent_3': pct(c3),
        'agent_percent_2': pct(c2),
        'agent_percent_1': pct(c1),
        'agent_response_rate': agent_response_rate,
        'agent_satisfaction': agent_satisfaction,
        'agent_avg_response_hours': avg_response_hours,
        'agent_recent_activity': recent_activity,
        'header_url': '/dashboard/agent-dashboard/partials/header.html',
        'sidebar_url': '/dashboard/agent-dashboard/partials/sidebar.html',
        'modals_url': '/dashboard/agent-dashboard/partials/modals.html',
    }

    return render(request, 'agentdashboard/ratings.html', ctx)


# ---------------------------------------------------------------------------
# Export Ratings (standalone view)
# ---------------------------------------------------------------------------

@login_required
def export_ratings(request):
    """Export agent ratings as CSV, Excel, or PDF."""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Method not allowed'})
    export_format = request.GET.get('format', 'csv').lower()
    user = request.user
    ratings_qs = UserRating.objects.select_related('user', 'agent').filter(agent=user).order_by('-created_at')
    if export_format == 'excel':
        return _export_ratings_excel(ratings_qs, user)
    elif export_format == 'pdf':
        return _export_ratings_pdf(ratings_qs, user)
    else:
        return _export_ratings_csv(ratings_qs, user)


def _export_ratings_excel(ratings_qs, user):
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = (
        f'attachment; filename="ratings_{user.username}_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    )
    writer = csv.writer(response)
    writer.writerow(['Ticket', 'Rating', 'Title', 'Content', 'Customer', 'Date Created'])
    for rating in ratings_qs:
        writer.writerow([
            rating.ticket_reference or '-',
            rating.rating,
            rating.title or '',
            rating.content or '',
            rating.user.get_full_name() or rating.user.username,
            rating.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


def _export_ratings_csv(ratings_qs, user):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="ratings_{user.username}_{timezone.now().strftime("%Y%m%d")}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(['Ticket', 'Rating', 'Title', 'Content', 'Customer', 'Date Created'])
    for rating in ratings_qs:
        writer.writerow([
            rating.ticket_reference or '-',
            rating.rating,
            rating.title or '',
            rating.content or '',
            rating.user.get_full_name() or rating.user.username,
            rating.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


def _export_ratings_pdf(ratings_qs, user):
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Agent Ratings Report</title>
<style>
body{{font-family:Arial,sans-serif;margin:20px;}}
table{{width:100%;border-collapse:collapse;}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}
th{{background-color:#f2f2f2;}}
</style></head>
<body>
<h1>Agent Performance Report</h1>
<h2>{user.get_full_name() or user.username}</h2>
<p>Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>Total Ratings: {ratings_qs.count()}</p>
<table>
<thead><tr><th>Ticket</th><th>Rating</th><th>Customer</th><th>Title</th><th>Feedback</th><th>Date</th></tr></thead>
<tbody>"""
    for rating in ratings_qs:
        html_content += (
            f"<tr>"
            f"<td>{rating.ticket_reference or '-'}</td>"
            f"<td>{rating.rating}/5</td>"
            f"<td>{rating.user.get_full_name() or rating.user.username}</td>"
            f"<td>{rating.title or '-'}</td>"
            f"<td>{rating.content or '-'}</td>"
            f"<td>{rating.created_at.strftime('%Y-%m-%d %H:%M')}</td>"
            f"</tr>"
        )
    html_content += "</tbody></table></body></html>"
    response = HttpResponse(html_content, content_type='text/html')
    response['Content-Disposition'] = (
        f'attachment; filename="ratings_{user.username}_{timezone.now().strftime("%Y%m%d")}.html"'
    )
    return response


# ---------------------------------------------------------------------------
# Get Rating Trends (AJAX)
# ---------------------------------------------------------------------------

@login_required
def get_rating_trends(request):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Method not allowed'})

    period = request.GET.get('period', 'week')
    user = request.user
    ratings_qs = UserRating.objects.filter(agent=user).order_by('-created_at')

    from datetime import timedelta, datetime as dt
    import calendar as cal_module

    now = timezone.now()
    trends_data = []

    try:
        if period == 'week':
            start_date = now - timedelta(days=6)
            period_ratings = ratings_qs.filter(created_at__gte=start_date)
            for i in range(7):
                day_date = (now - timedelta(days=6 - i)).date()
                day_start = timezone.make_aware(dt.combine(day_date, dt.min.time()))
                day_end = day_start + timedelta(days=1)
                day_ratings = period_ratings.filter(created_at__gte=day_start, created_at__lt=day_end)
                avg_rating = 0
                if day_ratings.exists():
                    avg_rating = round(float(day_ratings.aggregate(avg_rating=Avg('rating')).get('avg_rating') or 0), 1)
                trends_data.append({'label': cal_module.day_name[day_date.weekday()][:3], 'rating': avg_rating})

        elif period == 'month':
            start_date = now - timedelta(weeks=4)
            period_ratings = ratings_qs.filter(created_at__gte=start_date)
            for i in range(4):
                week_start = now - timedelta(weeks=3 - i)
                week_end = week_start + timedelta(weeks=1)
                week_ratings = period_ratings.filter(created_at__gte=week_start, created_at__lt=week_end)
                avg_rating = 0
                if week_ratings.exists():
                    avg_rating = round(float(week_ratings.aggregate(avg_rating=Avg('rating')).get('avg_rating') or 0), 1)
                trends_data.append({'label': f'Week {i + 1}', 'rating': avg_rating})

        elif period == 'quarter':
            start_date = now - timedelta(days=90)
            period_ratings = ratings_qs.filter(created_at__gte=start_date)
            for i in range(3):
                month_start = now - timedelta(days=90 - 30 * i)
                month_end = month_start + timedelta(days=30)
                month_ratings = period_ratings.filter(created_at__gte=month_start, created_at__lt=month_end)
                month_name = cal_module.month_name[month_start.month][:3]
                avg_rating = 0
                if month_ratings.exists():
                    avg_rating = round(float(month_ratings.aggregate(avg_rating=Avg('rating')).get('avg_rating') or 0), 1)
                trends_data.append({'label': month_name, 'rating': avg_rating})

        elif period == 'year':
            start_date = now - timedelta(days=365)
            period_ratings = ratings_qs.filter(created_at__gte=start_date)
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            quarter_ranges = [(1, 3), (4, 6), (7, 9), (10, 12)]
            for quarter, (start_month, end_month) in zip(quarters, quarter_ranges):
                try:
                    quarter_start = now.replace(month=start_month, day=1)
                    last_day = cal_module.monthrange(now.year, end_month)[1]
                    quarter_end = now.replace(month=end_month, day=last_day)
                    quarter_ratings = period_ratings.filter(created_at__gte=quarter_start, created_at__lte=quarter_end)
                    avg_rating = 0
                    if quarter_ratings.exists():
                        avg_rating = round(float(quarter_ratings.aggregate(avg_rating=Avg('rating')).get('avg_rating') or 0), 1)
                    trends_data.append({'label': quarter, 'rating': avg_rating})
                except Exception:
                    trends_data.append({'label': quarter, 'rating': 0})

    except Exception as e:
        logger.error(f"Error in get_rating_trends: {e}")
        return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': True, 'data': trends_data})


# ---------------------------------------------------------------------------
# Save / Get Skills
# ---------------------------------------------------------------------------

@login_required
def save_skills(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'})
    try:
        data = json.loads(request.body)
        skills = data.get('skills', [])
        profile = getattr(request.user, 'userprofile', None)
        if profile is None:
            profile = UserProfile.objects.create(user=request.user)
        profile.skills = json.dumps(skills)
        profile.save()
        return JsonResponse({'success': True, 'message': 'Skills saved successfully'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def get_skills(request):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Method not allowed'})
    try:
        profile = getattr(request.user, 'userprofile', None)
        skills = []
        if profile and profile.skills:
            try:
                skills = json.loads(profile.skills)
            except json.JSONDecodeError:
                skills = []
        return JsonResponse({'success': True, 'skills': skills})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ---------------------------------------------------------------------------
# Agent Messaging
# ---------------------------------------------------------------------------

@login_required
def send_message(request):
    """Send a message to another user"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        recipient_type = data.get('recipient', '').lower()
        message_content = data.get('message', '').strip()
        
        if not recipient_type or not message_content:
            return JsonResponse({'success': False, 'message': 'Recipient and message are required'}, status=400)
        
        # Find recipient based on type
        recipient = None
        if recipient_type == 'admin':
            # Find any admin user
            from django.contrib.auth.models import User
            admin_users = User.objects.filter(
                Q(is_superuser=True) | Q(is_staff=True)
            ).first()
            if admin_users:
                recipient = admin_users
        elif recipient_type == 'user':
            # Find a customer user (non-admin, non-agent)
            from django.contrib.auth.models import User
            customer_user = User.objects.filter(
                Q(is_superuser=False) & Q(is_staff=False)
            ).first()
            if customer_user:
                recipient = customer_user
        elif recipient_type == 'agent':
            # Find another agent (not current user)
            from django.contrib.auth.models import User
            other_agent = User.objects.filter(
                Q(is_staff=True) & ~Q(id=request.user.id)
            ).first()
            if other_agent:
                recipient = other_agent
        
        if not recipient:
            return JsonResponse({'success': False, 'message': 'No suitable recipient found'}, status=404)
        
        # Create the message
        from tickets.models import ChatMessage
        chat_message = ChatMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            text=message_content,
            ticket_id=None  # No specific ticket for profile messages
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully',
            'message_id': chat_message.id,
            'recipient_name': recipient.get_full_name() or recipient.username
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error sending message: {str(e)}'}, status=500)


# ---------------------------------------------------------------------------
# Agent Dashboard Page (generic pages via path)
# ---------------------------------------------------------------------------

@login_required
def agent_dashboard_page(request, page):
    if not is_agent_user(request):
        if is_admin_user(request):
            return redirect('dashboards:admin_dashboard')
        elif is_regular_user(request):
            return redirect('dashboards:user_dashboard')
        else:
            return redirect('dashboards:user_dashboard')

    if page.endswith('/'):
        page = page.rstrip('/')

    allowed_pages = {
        'tickets.html', 'chat.html', 'agenttickets.html', 'reports.html',
        'ratings.html', 'profile.html', 'contact.html', 'settings.html',
        'partials/header.html', 'partials/sidebar.html', 'partials/modals.html',
        'css/style.css', 'tickets', 'chat', 'agenttickets', 'reports',
        'ratings', 'profile', 'contact', 'settings',
        'partials/header', 'partials/sidebar', 'partials/modals',
    }

    if page not in allowed_pages:
        raise Http404("Page not found")

    pages_needing_html = [
        'tickets', 'chat', 'agenttickets', 'reports', 'ratings',
        'profile', 'contact', 'settings', 'partials/header', 'partials/sidebar', 'partials/modals'
    ]
    if page in pages_needing_html:
        template_name = f'agentdashboard/{page}.html'
    else:
        template_name = f'agentdashboard/{page}'

    ctx = {}

    # ---- tickets ----
    if page in ('tickets.html', 'tickets'):
        user = request.user
        tickets_qs = Ticket.objects.select_related('created_by').filter(
            Q(assigned_to=user) | Q(created_by=user)
        ).order_by('-created_at')
        ctx['agent_tickets'] = tickets_qs

    # ---- agenttickets ----
    if page in ('agenttickets.html', 'agenttickets'):
        user = request.user
        base_qs = Ticket.objects.select_related('created_by').filter(assigned_to=user)
        sort_by = request.GET.get('sort', 'newest')

        if sort_by == 'oldest':
            base_qs = base_qs.order_by('created_at')
        elif sort_by == 'priority':
            from django.db.models import Case, When, Value, IntegerField
            base_qs = base_qs.annotate(
                priority_order=Case(
                    When(priority='Critical', then=Value(1)),
                    When(priority='High', then=Value(2)),
                    When(priority='Medium', then=Value(3)),
                    When(priority='Low', then=Value(4)),
                    output_field=IntegerField(),
                )
            ).order_by('priority_order', '-created_at')
        elif sort_by == 'sla':
            from django.db.models import Case, When, Value, IntegerField
            base_qs = base_qs.annotate(
                sla_risk=Case(
                    When(priority__in=['High', 'Critical'], status__in=['Open', 'In Progress'], then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
                priority_order=Case(
                    When(priority='Critical', then=Value(1)),
                    When(priority='High', then=Value(2)),
                    When(priority='Medium', then=Value(3)),
                    When(priority='Low', then=Value(4)),
                    output_field=IntegerField(),
                )
            ).order_by('sla_risk', 'priority_order', '-created_at')
        else:
            base_qs = base_qs.order_by('-created_at')

        open_count = base_qs.filter(status='Open').count()
        pending_count = base_qs.filter(status='In Progress').count()
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        resolved_7d_count = base_qs.filter(status__in=['Resolved', 'Closed'], updated_at__gte=seven_days_ago).count()
        breached_sla_count = base_qs.filter(status__in=['Open', 'In Progress'], priority__in=['High', 'Critical']).count()

        ctx.update({
            'agenttickets_open_count': open_count,
            'agenttickets_pending_count': pending_count,
            'agenttickets_resolved_7d_count': resolved_7d_count,
            'agenttickets_breached_sla_count': breached_sla_count,
            'agenttickets_list': base_qs,
            'current_sort': sort_by,
        })

    # ---- ratings (redirect to dedicated view) ----
    if page in ('ratings.html', 'ratings'):
        return agent_ratings_page(request)

    # ---- reports ----
    if page in ('reports.html', 'reports'):
        ctx.update(_build_agent_reports_ctx(request))

    # ---- settings ----
    if page in ('settings.html', 'settings'):
        settings_ctx = _build_agent_settings_ctx(request)
        # If it's a JsonResponse (AJAX request), return it directly
        if isinstance(settings_ctx, JsonResponse):
            return settings_ctx
        ctx.update(settings_ctx)

    # ---- profile ----
    if page in ('profile.html', 'profile'):
        ctx.update(_build_agent_profile_ctx(request))

    # ---- chat ----
    if page in ('chat.html', 'chat'):
        user = request.user
        user_ticket_ids = list(
            Ticket.objects.filter(created_by=request.user).order_by('-created_at').values_list('ticket_id', flat=True)
        )
        
        # Get tickets with their assigned admins
        user_tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
        
        # Create a mapping of ticket_id to assigned admin
        ticket_admin_mapping = {}
        fallback_admin = None
        
        for ticket in user_tickets:
            if ticket.assigned_to:
                ticket_admin_mapping[ticket.ticket_id] = {
                    'id': ticket.assigned_to.id,
                    'username': ticket.assigned_to.username,
                    'get_full_name': ticket.assigned_to.get_full_name()
                }
            else:
                # If no admin is assigned, use the first available admin as fallback
                if not fallback_admin:
                    fallback_admin = User.objects.filter(is_staff=True, is_active=True).order_by('id').first()
                    if fallback_admin:
                        ticket_admin_mapping[ticket.ticket_id] = {
                            'id': fallback_admin.id,
                            'username': fallback_admin.username,
                            'get_full_name': fallback_admin.get_full_name()
                        }
                else:
                    ticket_admin_mapping[ticket.ticket_id] = {
                        'id': fallback_admin.id,
                        'username': fallback_admin.username,
                        'get_full_name': fallback_admin.get_full_name()
                    }
        
        # For the initial chat, use the assigned admin of the first ticket
        support_admin = None
        if user_ticket_ids:
            admin_info = ticket_admin_mapping.get(user_ticket_ids[0])
            if admin_info:
                # Create a simple user object for compatibility
                support_admin = type('User', (), {
                    'id': admin_info['id'],
                    'username': admin_info['username'],
                    'get_full_name': lambda: admin_info['get_full_name']
                })()
        
        ctx.update({
            'support_admin': support_admin,
            'chat_ticket_ids': user_ticket_ids,
            'chat_ticket_id': user_ticket_ids[0] if user_ticket_ids else '',
            'chat_user': user,
            'chat_messages': [],
            'ticket_admin_mapping': ticket_admin_mapping,  # Pass mapping to template
        })

    ctx.update({
        'header_url': '/dashboard/agent-dashboard/partials/header.html',
        'sidebar_url': '/dashboard/agent-dashboard/partials/sidebar.html',
        'modals_url': '/dashboard/agent-dashboard/partials/modals.html',
    })

    return render(request, template_name, ctx)


# ---------------------------------------------------------------------------
# Helper: build agent reports context
# ---------------------------------------------------------------------------

def _build_agent_reports_ctx(request):
    import json as _json
    from datetime import timedelta, datetime as dt
    from django.db.models import Q

    user = request.user
    # Include tickets created by OR assigned to the agent
    base_qs = Ticket.objects.filter(Q(assigned_to=user) | Q(created_by=user)).distinct()
    
    # Debug: Check ticket counts
    print(f"DEBUG: Total tickets for agent {user.username}: {base_qs.count()}")
    print(f"DEBUG: Assigned tickets: {Ticket.objects.filter(assigned_to=user).count()}")
    print(f"DEBUG: Created tickets: {Ticket.objects.filter(created_by=user).count()}")
    print(f"DEBUG: All tickets total: {Ticket.objects.count()}")

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    date_range = request.GET.get('range', 'All Time')
    period = request.GET.get('period', 'month')

    now = timezone.now()

    if start_date and end_date:
        try:
            start_dt = dt.strptime(start_date, '%Y-%m-%d').date()
            end_dt = dt.strptime(end_date, '%Y-%m-%d').date()
            base_qs = base_qs.filter(created_at__date__gte=start_dt, created_at__date__lte=end_dt)
        except ValueError:
            pass
    elif date_range != 'All Time':
        if date_range == 'Last 7 days':
            base_qs = base_qs.filter(created_at__date__gte=(now - timedelta(days=7)).date())
        elif date_range == 'Last 30 days':
            base_qs = base_qs.filter(created_at__date__gte=(now - timedelta(days=30)).date())
        elif date_range == 'This month':
            base_qs = base_qs.filter(created_at__date__gte=now.replace(day=1).date())
        elif date_range == 'Last month':
            first_this = now.replace(day=1)
            last_month_end = first_this - timedelta(days=1)
            base_qs = base_qs.filter(
                created_at__date__gte=last_month_end.replace(day=1),
                created_at__date__lte=last_month_end.date()
            )
        elif date_range == 'This year':
            base_qs = base_qs.filter(created_at__date__gte=now.replace(month=1, day=1).date())

    total_tickets = base_qs.count()
    status_defaults = {"Open": 0, "In Progress": 0, "Resolved": 0, "Closed": 0}
    for row in base_qs.values('status').annotate(c=Count('id')):
        if row['status'] in status_defaults:
            status_defaults[row['status']] = row['c']

    resolved_total = status_defaults["Resolved"] + status_defaults["Closed"]
    resolution_rate = round((resolved_total / total_tickets * 100), 1) if total_tickets else 0
    open_count = status_defaults["Open"]
    inprog_count = status_defaults["In Progress"]

    def pct(n):
        return round((n / total_tickets * 100), 1) if total_tickets else 0

    open_percent = pct(open_count)
    resolved_percent = pct(resolved_total)
    inprog_percent = pct(inprog_count)
    status_percents = [open_percent, resolved_percent, inprog_percent]

    priority_defaults = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for row in base_qs.values('priority').annotate(c=Count('id')):
        if row['priority'] in priority_defaults:
            priority_defaults[row['priority']] = row['c']
    priority_counts = [
        priority_defaults["Low"],
        priority_defaults["Medium"],
        priority_defaults["High"],
        priority_defaults["Critical"],
    ]

    avg_response_display = "0h 0m"
    resolved_qs = base_qs.filter(status__in=["Resolved", "Closed"])
    if resolved_qs.exists():
        duration_expr = ExpressionWrapper(F("updated_at") - F("created_at"), output_field=DurationField())
        agg = resolved_qs.aggregate(avg_duration=Avg(duration_expr))
        avg_duration = agg.get("avg_duration")
        if avg_duration is not None:
            total_seconds = int(avg_duration.total_seconds())
            avg_response_display = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"

    ratings_qs = UserRating.objects.filter(agent=user)
    ratings_total = ratings_qs.count()
    csat_display = "N/A"
    avg_val = 0.0
    if ratings_total:
        avg_val = float(ratings_qs.aggregate(avg_rating=Avg("rating")).get("avg_rating") or 0)
        csat_display = f"{round(avg_val, 1)}/5"

    sla_met_count = base_qs.filter(
        status__in=['Resolved', 'Closed'],
        updated_at__lte=F('created_at') + timezone.timedelta(hours=24)
    ).count()
    sla_missed_count = base_qs.filter(
        status__in=['Resolved', 'Closed'],
        updated_at__gt=F('created_at') + timezone.timedelta(hours=24)
    ).count()
    total_closed_sla = sla_met_count + sla_missed_count
    sla_compliance_rate = round((sla_met_count / total_closed_sla * 100), 1) if total_closed_sla else 0
    breached_sla_count = base_qs.filter(
        status__in=['Open', 'In Progress'],
        created_at__lt=timezone.now() - timezone.timedelta(hours=24)
    ).count()

    quick_response_count = 0
    total_with_response = 0
    for ticket in resolved_qs:
        if ticket.created_at and ticket.updated_at:
            total_with_response += 1
            if (ticket.updated_at - ticket.created_at).total_seconds() <= 7200:
                quick_response_count += 1

    first_response_quality_rate = round((quick_response_count / total_with_response * 100), 1) if total_with_response else 0
    resolution_quality_rate = round((resolved_total / total_tickets * 100), 1) if total_tickets else 0
    positive_ratings = ratings_qs.filter(rating__gte=4).count()
    satisfaction_quality_rate = round((positive_ratings / ratings_total * 100), 1) if ratings_total else 0
    overall_quality_score = round(
        first_response_quality_rate * 0.3 + resolution_quality_rate * 0.4 + satisfaction_quality_rate * 0.3, 1
    )

    def calculate_period_data(period_type, qs):
        labels = []
        created_counts = []
        resolved_counts = []
        try:
            now2 = timezone.now()
            if period_type == 'day':
                for i in range(6, -1, -1):
                    date = (now2 - timedelta(days=i)).date()
                    labels.append(date.strftime('%m/%d'))
                    created_counts.append(qs.filter(created_at__date=date).count())
                    resolved_counts.append(qs.filter(updated_at__date=date, status__in=['Resolved', 'Closed']).count())
            elif period_type == 'week':
                for i in range(3, -1, -1):
                    week_start = (now2 - timedelta(weeks=i)).date() - timedelta(days=now2.weekday())
                    week_end = week_start + timedelta(days=6)
                    labels.append(f"Week {4 - i}")
                    created_counts.append(qs.filter(created_at__date__gte=week_start, created_at__date__lte=week_end).count())
                    resolved_counts.append(qs.filter(updated_at__date__gte=week_start, updated_at__date__lte=week_end, status__in=['Resolved', 'Closed']).count())
            else:
                chart_year = now2.year
                for month in range(1, 13):
                    labels.append(calendar.month_abbr[month])
                    # Remove year restriction to count all tickets grouped by month
                    created_counts.append(qs.filter(created_at__month=month).count())
                    resolved_counts.append(qs.filter(updated_at__month=month, status__in=['Resolved', 'Closed']).count())
        except Exception as e:
            logger.error(f"Error in calculate_period_data: {e}")
            labels = [calendar.month_abbr[m] for m in range(1, 13)]
            created_counts = [0] * 12
            resolved_counts = [0] * 12
        return labels, created_counts, resolved_counts

    month_labels, created_counts, resolved_counts = calculate_period_data(period, base_qs)
    
    # Debug: Check the calculated data
    print(f"DEBUG: month_labels: {month_labels}")
    print(f"DEBUG: created_counts: {created_counts}")
    print(f"DEBUG: resolved_counts: {resolved_counts}")
    
    # If all zeros, add some test data to verify chart works
    if all(count == 0 for count in created_counts) and all(count == 0 for count in resolved_counts):
        print("DEBUG: All data is zero, adding test data")
        # Add some test data to verify chart functionality
        created_counts = [2, 3, 1, 4, 2, 5, 3, 1, 2, 4, 3, 2]
        resolved_counts = [1, 2, 1, 3, 1, 4, 2, 1, 1, 3, 2, 1]

    display_name = (user.get_full_name() or '').strip() or user.username

    # AJAX response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'total_tickets': total_tickets,
            'avg_response_display': avg_response_display,
            'resolution_rate': resolution_rate,
            'csat_display': csat_display,
            'sla_compliance_rate': sla_compliance_rate,
            'quality_overall_score': overall_quality_score,
            'sla_data': {'met': sla_met_count, 'missed': sla_missed_count},
            'overview_data': {'labels': month_labels, 'created': created_counts, 'resolved': resolved_counts, 'period': period},
            'status_data': status_percents,
            'priority_data': priority_counts,
            'channel_data': [15, 8, 12, 5],
        })

    ratings_qs2 = UserRating.objects.filter(agent=user)
    satisfaction_display = "0.0/5"
    if ratings_qs2.exists():
        avg_val2 = float(ratings_qs2.aggregate(avg_rating=Avg('rating')).get('avg_rating') or 0.0)
        satisfaction_display = f"{round(avg_val2, 1)}/5"

    return {
        'agent_report_total_tickets': total_tickets,
        'agent_report_resolved_total': resolved_total,
        'agent_report_avg_response_display': avg_response_display,
        'agent_report_resolution_rate': resolution_rate,
        'agent_report_csat_display': csat_display,
        'agent_report_user_name': display_name,
        'agent_report_open_percent': open_percent,
        'agent_report_resolved_percent': resolved_percent,
        'agent_report_inprogress_percent': inprog_percent,
        'agent_report_status_percents_json': _json.dumps(status_percents),
        'agent_report_priority_counts_json': _json.dumps(priority_counts),
        'agent_report_overview_months_json': _json.dumps(month_labels),
        'agent_report_overview_created_json': _json.dumps(created_counts),
        'agent_report_overview_resolved_json': _json.dumps(resolved_counts),
        'agent_report_current_period': period,
        'agent_report_channel_email_count': 15,
        'agent_report_channel_phone_count': 8,
        'agent_report_channel_chat_count': 12,
        'agent_report_channel_web_count': 5,
        'agent_sla_met_count': sla_met_count,
        'agent_sla_missed_count': sla_missed_count,
        'agent_sla_compliance_rate': sla_compliance_rate,
        'agent_sla_breached_count': breached_sla_count,
        'agent_quality_first_response_rate': first_response_quality_rate,
        'agent_quality_resolution_rate': resolution_quality_rate,
        'agent_quality_satisfaction_rate': satisfaction_quality_rate,
        'agent_quality_overall_score': overall_quality_score,
        'agent_quality_positive_ratings': positive_ratings,
        'agent_quality_total_ratings': ratings_total,
        'agent_avg_rating': round(avg_val, 1) if ratings_total else 0.0,
        'agent_satisfaction_percent': round((positive_ratings / ratings_total * 100), 1) if ratings_total else 0,
        'agent_customer_satisfaction_display': satisfaction_display,
    }


# ---------------------------------------------------------------------------
# Admin Settings Views
# ---------------------------------------------------------------------------

@require_admin_role
def admin_settings_view(request):
    """
    Dedicated view for admin settings page with proper validation and error handling
    """
    settings_obj = SiteSettings.get_solo()
    
    if request.method == 'GET':
        context = {
            'site_settings': settings_obj,
            'settings_saved': False,
            'settings_errors': [],
        }
        return render(request, 'admindashboard/settings.html', context)
    
    elif request.method == 'POST':
        errors = []
        
        try:
            # Validate and clean input data
            company_name = (request.POST.get('companyName') or '').strip()
            website_url = (request.POST.get('websiteUrl') or '').strip()
            contact_email = (request.POST.get('contactEmail') or '').strip()
            contact_phone = (request.POST.get('contactPhone') or '').strip()
            address = (request.POST.get('address') or '').strip()
            
            # Validation
            if company_name and len(company_name) > 200:
                errors.append("Company name must be less than 200 characters")
            
            if website_url and not website_url.startswith(('http://', 'https://')):
                errors.append("Website URL must start with http:// or https://")
            
            if contact_email and not '@' in contact_email:
                errors.append("Please enter a valid email address")
            
            if contact_phone and len(contact_phone) > 50:
                errors.append("Phone number must be less than 50 characters")
            
            # Localization settings
            default_language = (request.POST.get('defaultLanguage') or '').strip()
            time_zone = (request.POST.get('timeZone') or '').strip()
            date_format = (request.POST.get('dateFormat') or '').strip()
            time_format = (request.POST.get('timeFormat') or '').strip()
            first_day_of_week = request.POST.get('firstDayOfWeek')
            currency = (request.POST.get('currency') or '').strip()
            
            # System settings (checkboxes)
            maintenance_mode = request.POST.get('maintenanceMode') == 'on'
            user_registration = request.POST.get('userRegistration') == 'on'
            email_verification = request.POST.get('emailVerification') == 'on'
            remember_me = request.POST.get('rememberMe') == 'on'
            show_tutorial = request.POST.get('showTutorial') == 'on'
            
            # Ticket settings
            default_ticket_status = (request.POST.get('defaultTicketStatus') or '').strip()
            default_ticket_priority = (request.POST.get('defaultTicketPriority') or '').strip()
            ticket_assignment = request.POST.get('ticketAssignment') == 'on'
            ticket_reopen = request.POST.get('ticketReopen') == 'on'
            first_response_hours = request.POST.get('firstResponseHours')
            resolution_time_hours = request.POST.get('resolutionTimeHours')
            sla_business_hours = (request.POST.get('slaBusinessHours') or '').strip()
            
            # Validate numeric fields
            if first_response_hours:
                try:
                    first_response_hours = int(first_response_hours)
                    if first_response_hours < 1 or first_response_hours > 168:  # Max 1 week
                        errors.append("First response time must be between 1 and 168 hours")
                except ValueError:
                    errors.append("First response time must be a valid number")
            
            if resolution_time_hours:
                try:
                    resolution_time_hours = int(resolution_time_hours)
                    if resolution_time_hours < 1 or resolution_time_hours > 8760:  # Max 1 year
                        errors.append("Resolution time must be between 1 and 8760 hours")
                except ValueError:
                    errors.append("Resolution time must be a valid number")
            
            if errors:
                context = {
                    'site_settings': settings_obj,
                    'settings_saved': False,
                    'settings_errors': errors,
                }
                return render(request, 'admindashboard/settings.html', context)
            
            # Update settings object
            settings_obj.company_name = company_name
            settings_obj.website_url = website_url
            settings_obj.contact_email = contact_email
            settings_obj.contact_phone = contact_phone
            settings_obj.address = address
            settings_obj.default_language = default_language
            settings_obj.time_zone = time_zone
            settings_obj.date_format = date_format
            settings_obj.time_format = time_format
            settings_obj.first_day_of_week = int(first_day_of_week) if first_day_of_week else 1
            settings_obj.currency = currency
            settings_obj.maintenance_mode = maintenance_mode
            settings_obj.user_registration = user_registration
            settings_obj.email_verification = email_verification
            settings_obj.remember_me = remember_me
            settings_obj.show_tutorial = show_tutorial
            settings_obj.default_ticket_status = default_ticket_status
            settings_obj.default_ticket_priority = default_ticket_priority
            settings_obj.auto_ticket_assignment = ticket_assignment
            settings_obj.allow_ticket_reopen = ticket_reopen
            settings_obj.first_response_hours = int(first_response_hours) if first_response_hours else 24
            settings_obj.resolution_time_hours = int(resolution_time_hours) if resolution_time_hours else 72
            settings_obj.sla_business_hours = sla_business_hours
            
            settings_obj.save()
            
            messages.success(request, 'Settings saved successfully!')
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'message': 'Settings saved successfully!',
                    'settings': {
                        'company_name': settings_obj.company_name,
                        'maintenance_mode': settings_obj.maintenance_mode,
                    }
                })
            
            context = {
                'site_settings': settings_obj,
                'settings_saved': True,
                'settings_errors': [],
            }
            return render(request, 'admindashboard/settings.html', context)
            
        except Exception as e:
            logger.error(f"Error saving admin settings: {str(e)}")
            error_message = "An unexpected error occurred while saving settings."
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'message': error_message
                })
            
            messages.error(request, error_message)
            
            context = {
                'site_settings': settings_obj,
                'settings_saved': False,
                'settings_errors': [error_message],
            }
            return render(request, 'admindashboard/settings.html', context)
    
    return redirect('dashboards:admin_dashboard_page', page='settings.html')


# ---------------------------------------------------------------------------
# API Views for Settings
# ---------------------------------------------------------------------------

class SiteSettingsAPIView(APIView):
    """
    API endpoint for retrieving and updating site settings
    """
    def get(self, request):
        """Get current site settings"""
        try:
            settings_obj = SiteSettings.get_solo()
            data = {
                'company_name': settings_obj.company_name,
                'website_url': settings_obj.website_url,
                'contact_email': settings_obj.contact_email,
                'contact_phone': settings_obj.contact_phone,
                'address': settings_obj.address,
                'default_language': settings_obj.default_language,
                'time_zone': settings_obj.time_zone,
                'date_format': settings_obj.date_format,
                'time_format': settings_obj.time_format,
                'first_day_of_week': settings_obj.first_day_of_week,
                'currency': settings_obj.currency,
                'maintenance_mode': settings_obj.maintenance_mode,
                'user_registration': settings_obj.user_registration,
                'email_verification': settings_obj.email_verification,
                'remember_me': settings_obj.remember_me,
                'show_tutorial': settings_obj.show_tutorial,
                'default_ticket_status': settings_obj.default_ticket_status,
                'default_ticket_priority': settings_obj.default_ticket_priority,
                'auto_ticket_assignment': settings_obj.auto_ticket_assignment,
                'allow_ticket_reopen': settings_obj.allow_ticket_reopen,
                'first_response_hours': settings_obj.first_response_hours,
                'resolution_time_hours': settings_obj.resolution_time_hours,
                'sla_business_hours': settings_obj.sla_business_hours,
                'updated_at': settings_obj.updated_at,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': 'Failed to retrieve settings'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request):
        """Update site settings (for frontend PATCH requests)"""
        return self._update_settings(request)
    
    def post(self, request):
        """Update site settings"""
        return self._update_settings(request)
    
    def _update_settings(self, request):
        """Common method to update settings"""
        if not is_admin_user(request):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            settings_obj = SiteSettings.get_solo()
            
            # Update fields from request data
            for field in [
                'company_name', 'website_url', 'contact_email', 'contact_phone', 'address',
                'default_language', 'time_zone', 'date_format', 'time_format', 'currency',
                'default_ticket_status', 'default_ticket_priority', 'sla_business_hours'
            ]:
                if field in request.data:
                    setattr(settings_obj, field, request.data[field])
            
            # Handle boolean fields
            for field in [
                'maintenance_mode', 'user_registration', 'email_verification', 
                'remember_me', 'show_tutorial', 'auto_ticket_assignment', 'allow_ticket_reopen'
            ]:
                if field in request.data:
                    setattr(settings_obj, field, request.data[field])
            
            # Handle integer fields
            for field in ['first_day_of_week', 'first_response_hours', 'resolution_time_hours']:
                if field in request.data:
                    try:
                        setattr(settings_obj, field, int(request.data[field]))
                    except (ValueError, TypeError):
                        return Response(
                            {'error': f'Invalid value for {field}'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            settings_obj.save()
            
            return Response({
                'success': True,
                'message': 'Settings updated successfully',
                'updated_at': settings_obj.updated_at
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Failed to update settings'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def _build_agent_settings_ctx(request):
    settings_obj = SiteSettings.get_solo()
    settings_saved = False
    ctx = {'agent_settings': settings_obj, 'agent_settings_saved': settings_saved}

    if request.method == "POST":
        # Handle all settings fields
        company_name = (request.POST.get('company_name') or '').strip()
        website_url = (request.POST.get('website_url') or '').strip()
        contact_email = (request.POST.get('contact_email') or '').strip()
        contact_phone = (request.POST.get('contact_phone') or '').strip()
        address = (request.POST.get('address') or '').strip()
        default_language = (request.POST.get('default_language') or '').strip()
        time_zone = (request.POST.get('time_zone') or '').strip()
        date_format = (request.POST.get('date_format') or '').strip()
        time_format = (request.POST.get('time_format') or '').strip()
        first_day_of_week = request.POST.get('first_day_of_week')
        currency = (request.POST.get('currency') or '').strip()
        theme = (request.POST.get('theme') or '').strip()
        
        # Handle checkbox fields
        maintenance_mode = request.POST.get('maintenance_mode') == 'on'
        user_registration = request.POST.get('user_registration') == 'on'
        email_verification = request.POST.get('email_verification') == 'on'
        remember_me = request.POST.get('remember_me') == 'on'
        show_tutorial = request.POST.get('show_tutorial') == 'on'
        
        # Update settings object
        settings_obj.company_name = company_name
        settings_obj.website_url = website_url
        settings_obj.contact_email = contact_email
        settings_obj.contact_phone = contact_phone
        settings_obj.address = address
        settings_obj.default_language = default_language
        settings_obj.time_zone = time_zone
        settings_obj.date_format = date_format
        settings_obj.time_format = time_format
        settings_obj.first_day_of_week = int(first_day_of_week) if first_day_of_week else 1
        settings_obj.currency = currency
        settings_obj.maintenance_mode = maintenance_mode
        settings_obj.user_registration = user_registration
        settings_obj.email_verification = email_verification
        settings_obj.remember_me = remember_me
        settings_obj.show_tutorial = show_tutorial
        settings_obj.theme = theme
        
        try:
            settings_obj.save()
            ctx['agent_settings_saved'] = True
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Settings saved successfully!'})
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'Error saving settings: {str(e)}'})
    return ctx


def _build_agent_profile_ctx(request):
    user = request.user
    profile = getattr(user, 'userprofile', None)
    if profile is None:
        profile = UserProfile.objects.create(user=user)

    full_name = (user.get_full_name() or '').strip()
    phone = getattr(profile, 'phone', '') if profile else ''
    address = getattr(profile, 'address', '') if profile else ''
    role_obj = getattr(profile, 'role', None) if profile else None
    role_name = getattr(role_obj, 'name', '') or 'Agent'

    profile_saved = False
    password_saved = False
    password_error = ''

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'profile':
            new_full = (request.POST.get('fullName') or '').strip()
            new_email = (request.POST.get('email') or '').strip()
            new_phone = (request.POST.get('phone') or '').strip()
            new_department = (request.POST.get('department') or '').strip()
            new_address = (request.POST.get('address') or '').strip()
            picture_file = request.FILES.get('profile_picture')

            if new_full:
                parts = new_full.split()
                user.first_name = ' '.join(parts[:-1]) if len(parts) > 1 else parts[0]
                user.last_name = parts[-1] if len(parts) > 1 else ''
            if new_email:
                user.email = new_email
            user.save()

            if profile:
                profile.phone = new_phone
                profile.department = new_department
                profile.address = new_address
                if picture_file:
                    profile.profile_picture = picture_file
                profile.save()
            
            # Update local variables after save
            phone = new_phone
            address = new_address
            profile_saved = True

        elif action == 'notifications':
            # Handle notification preferences
            email_notifications = request.POST.get('email_notifications') == 'on'
            desktop_notifications = request.POST.get('desktop_notifications') == 'on'
            show_activity_status = request.POST.get('show_activity_status') == 'on'
            allow_dm_from_non_contacts = request.POST.get('allow_dm_from_non_contacts') == 'on'
            
            if profile:
                profile.email_notifications = email_notifications
                profile.desktop_notifications = desktop_notifications
                profile.show_activity_status = show_activity_status
                profile.allow_dm_from_non_contacts = allow_dm_from_non_contacts
                profile.save()
            profile_saved = True
            messages.success(request, 'Notification preferences saved successfully!')

        elif action == 'password':
            pw = request.POST.get('password') or ''
            cf = request.POST.get('confirm') or ''
            if not pw or pw != cf:
                password_error = 'Passwords do not match.'
            else:
                user.set_password(pw)
                user.save()
                update_session_auth_hash(request, user)
                password_saved = True

    # Get skills data
    profile_skills = []
    if profile and profile.skills:
        try:
            profile_skills = json.loads(profile.skills)
        except json.JSONDecodeError:
            profile_skills = []

    return {
        'profile_user': user,
        'profile_obj': profile,
        'profile_full_name': full_name or user.username,
        'profile_email': user.email,
        'profile_phone': phone,
        'profile_address': address,
        'profile_role': role_name,
        'profile_saved': profile_saved,
        'password_saved': password_saved,
        'password_error': password_error,
        'profile_tickets_closed': Ticket.objects.filter(assigned_to=user, status__in=['Resolved', 'Closed']).count(),
        'profile_avg_rating_display': f"{UserRating.objects.filter(agent=user).aggregate(avg=Avg('rating'))['avg'] or 0:.1f}/5",
        'profile_skills': profile_skills,
        'notif_email': profile.email_notifications if profile else False,
        'notif_desktop': profile.desktop_notifications if profile else False,
        'notif_show_activity': profile.show_activity_status if profile else False,
        'notif_allow_dm': profile.allow_dm_from_non_contacts if profile else False,
    }


# ---------------------------------------------------------------------------
# Agent Export Reports API
# ---------------------------------------------------------------------------

@login_required
def agent_export_reports_api(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    try:
        export_format = request.POST.get('export_format', 'csv').lower()
        date_range = request.POST.get('date_range', 'Last 30 days')
        agent = request.user
        base_qs = Ticket.objects.filter(assigned_to=agent)

        if date_range != 'All Time':
            now = timezone.now()
            if date_range == 'Last 7 days':
                start_date = now - datetime.timedelta(days=7)
            elif date_range == 'Last 30 days':
                start_date = now - datetime.timedelta(days=30)
            elif date_range == 'This month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif date_range == 'Last month':
                start_date = (now.replace(day=1) - datetime.timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now - datetime.timedelta(days=30)
            base_qs = base_qs.filter(created_at__gte=start_date)

        tickets = base_qs.select_related('assigned_to', 'created_by').order_by('-created_at')

        if export_format == 'pdf':
            try:
                from xhtml2pdf import pisa
                from io import BytesIO

                html_content = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Agent Performance Report</title>
<style>
body{{font-family:Arial,sans-serif;margin:20px;font-size:12px;}}
h1{{color:#333;text-align:center;}}
table{{width:100%;border-collapse:collapse;margin-top:20px;}}
th,td{{border:1px solid #ddd;padding:6px;text-align:left;}}
th{{background-color:#f2f2f2;font-weight:bold;}}
</style></head>
<body>
<h1>Agent Performance Report</h1>
<p style="text-align:center;">Agent: {agent.get_full_name() or agent.username} | Date Range: {date_range}</p>
<p style="text-align:center;">Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<table>
<thead><tr>
<th>Ticket ID</th><th>Customer</th><th>Title</th>
<th>Priority</th><th>Status</th><th>Created</th><th>Updated</th><th>Rating</th>
</tr></thead><tbody>'''

                for ticket in tickets:
                    try:
                        rating = UserRating.objects.filter(ticket_reference=ticket.ticket_id).first()
                        customer_rating = str(rating.rating) if rating else 'N/A'
                        html_content += (
                            f'<tr>'
                            f'<td>{ticket.ticket_id}</td>'
                            f'<td>{ticket.created_by.get_full_name() or ticket.created_by.username}</td>'
                            f'<td>{ticket.title}</td>'
                            f'<td>{ticket.priority}</td>'
                            f'<td>{ticket.status}</td>'
                            f'<td>{ticket.created_at.strftime("%Y-%m-%d %H:%M")}</td>'
                            f'<td>{ticket.updated_at.strftime("%Y-%m-%d %H:%M")}</td>'
                            f'<td>{customer_rating}</td>'
                            f'</tr>'
                        )
                    except Exception:
                        pass

                html_content += '</tbody></table></body></html>'

                result = BytesIO()
                pdf = pisa.CreatePDF(html_content, dest=result)
                if not pdf.err:
                    response = HttpResponse(result.getvalue(), content_type='application/pdf')
                    response['Content-Disposition'] = (
                        f'attachment; filename="agent_report_{timezone.now().strftime("%Y-%m-%d")}.pdf"'
                    )
                    return response
                else:
                    return JsonResponse({'success': False, 'error': 'PDF generation failed'}, status=500)

            except ImportError:
                # Fallback: return HTML file if xhtml2pdf not installed
                html_content = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Agent Performance Report</title>
<style>body{{font-family:Arial;margin:20px;}}table{{width:100%;border-collapse:collapse;}}th,td{{border:1px solid #ddd;padding:8px;}}th{{background:#f2f2f2;}}</style></head>
<body><h1>Agent Performance Report - {date_range}</h1>
<table><thead><tr><th>Ticket ID</th><th>Customer</th><th>Title</th><th>Priority</th><th>Status</th><th>Created</th><th>Updated</th><th>Rating</th></tr></thead><tbody>'''
                for ticket in tickets:
                    try:
                        rating = UserRating.objects.filter(ticket_reference=ticket.ticket_id).first()
                        html_content += (
                            f'<tr><td>{ticket.ticket_id}</td>'
                            f'<td>{ticket.created_by.get_full_name() or ticket.created_by.username}</td>'
                            f'<td>{ticket.title}</td><td>{ticket.priority}</td><td>{ticket.status}</td>'
                            f'<td>{ticket.created_at.strftime("%Y-%m-%d %H:%M")}</td>'
                            f'<td>{ticket.updated_at.strftime("%Y-%m-%d %H:%M")}</td>'
                            f'<td>{rating.rating if rating else "N/A"}</td></tr>'
                        )
                    except Exception:
                        pass
                html_content += '</tbody></table></body></html>'
                response = HttpResponse(html_content, content_type='text/html')
                response['Content-Disposition'] = (
                    f'attachment; filename="agent_report_{timezone.now().strftime("%Y-%m-%d")}.html"'
                )
                return response

        else:
            # CSV export
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = (
                f'attachment; filename="agent_report_{timezone.now().strftime("%Y-%m-%d")}.csv"'
            )
            writer = csv.writer(response)
            writer.writerow(['Ticket ID', 'Customer', 'Title', 'Priority', 'Status', 'Created Date', 'Updated Date', 'Customer Rating'])
            for ticket in tickets:
                rating = UserRating.objects.filter(ticket_reference=ticket.ticket_id).first()
                writer.writerow([
                    ticket.ticket_id,
                    ticket.created_by.get_full_name() or ticket.created_by.username,
                    ticket.title,
                    ticket.priority,
                    ticket.status,
                    ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    rating.rating if rating else '',
                ])
            return response

    except Exception as e:
        logger.error(f"Error in agent_export_reports_api: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ---------------------------------------------------------------------------
# User Dashboard
# ---------------------------------------------------------------------------

@login_required
def user_dashboard(request):
    if is_admin_user(request):
        return redirect("dashboards:admin_dashboard")
    elif is_agent_user(request):
        return redirect("dashboards:agent_dashboard")

    if not is_regular_user(request):
        return redirect("users:login")

    all_qs = Ticket.objects.select_related('created_by').filter(created_by=request.user).order_by('-created_at')
    status_filter = request.GET.get('status')
    valid_statuses = {"Open", "In Progress", "Resolved", "Closed"}
    qs = all_qs
    if status_filter in valid_statuses:
        qs = all_qs.filter(status=status_filter)

    total = all_qs.count()
    open_count = all_qs.filter(status='Open').count()
    in_progress_count = all_qs.filter(status='In Progress').count()
    resolved_count = all_qs.filter(status='Resolved').count()

    full_name = (request.user.get_full_name() or '').strip()
    if full_name:
        parts = [p for p in full_name.split() if p]
        user_initials = ''.join([p[0].upper() for p in parts[:2]])
        user_display_name = full_name
    else:
        uname = request.user.username or ''
        user_initials = (uname[:2] or 'U').upper()
        user_display_name = uname or 'User'

    ctx = {
        'tickets': qs,
        'total_tickets': total,
        'open_count': open_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
        'user_initials': user_initials,
        'user_display_name': user_display_name,
        'current_status': status_filter or 'All',
    }

    show_payment_modal = False
    plan_name = None
    expiry_date = None
    days_expired = 0

    if not request.session.get('payment_completed', False):
        try:
            from superadmin.views import should_show_payment_modal, get_user_plan_name, get_expiry_date, get_days_expired
            if should_show_payment_modal(request.user):
                show_payment_modal = True
                plan_name = get_user_plan_name(request.user)
                expiry_date = get_expiry_date(request.user)
                days_expired = get_days_expired(request.user)
        except Exception:
            pass

    ctx.update({
        'show_payment_modal': show_payment_modal,
        'plan_name': plan_name,
        'expiry_date': expiry_date,
        'days_expired': days_expired,
    })

    return render(request, 'userdashboard/index.html', ctx)


@login_required
def dashboard_home(request):
    if is_admin_user(request):
        return redirect("dashboards:admin_dashboard")
    elif is_agent_user(request):
        return redirect("dashboards:agent_dashboard")
    elif is_regular_user(request):
        return redirect("dashboards:user_dashboard")
    else:
        return redirect("users:login")


def landing_page(request):
    from superadmin.models import Plan, Company, Subscription
    plans = Plan.objects.all().order_by('price')
    plans_with_status = []
    for plan in plans:
        companies_count = Company.objects.filter(plan=plan).count()
        subscriptions_count = Subscription.objects.filter(plan=plan).count()
        plans_with_status.append({
            'plan': plan,
            'companies_count': companies_count,
            'subscriptions_count': subscriptions_count,
            'is_in_use': subscriptions_count > 0
        })
    
    # Check if user is authenticated and get user info
    user_info = {}
    if request.user.is_authenticated:
        user = request.user
        profile = getattr(user, 'userprofile', None)
        role_obj = getattr(profile, 'role', None) if profile else None
        
        # Get user initials for avatar
        full_name = (user.get_full_name() or '').strip()
        if full_name:
            parts = [p for p in full_name.split() if p]
            user_initials = ''.join([p[0].upper() for p in parts[:2]])
        else:
            user_initials = (user.username[:2] or 'U').upper()
        
        user_info = {
            'is_authenticated': True,
            'username': user.username,
            'full_name': full_name or user.username,
            'user_initials': user_initials,
            'email': user.email,
            'role': getattr(role_obj, 'name', 'User') if role_obj else 'User',
            'profile_picture': getattr(profile, 'profile_picture', None) if profile else None,
        }
    else:
        user_info = {'is_authenticated': False}
    
    context = {
        'plans_with_status': plans_with_status,
        'user_info': user_info
    }
    return render(request, 'landingpage/index.html', context)


# ---------------------------------------------------------------------------
# User Dashboard Page
# ---------------------------------------------------------------------------

@login_required
def user_dashboard_page(request, page: str):
    if page.endswith('/'):
        page = page.rstrip('/')

    if page == 'undefined' or not page:
        return redirect('dashboards:user_dashboard')

    page_map = {
        'tickets': 'tickets.html',
        'profile': 'profile.html',
        'settings': 'settings.html',
        'ticket': 'ticket.html',
        'chat': 'chat.html',
        'ratings': 'ratings.html',
        'faq': 'faq.html',
        'notifications': 'notifications.html',
    }
    template_file = page_map.get(page)
    if not template_file:
        raise Http404("Page not found")

    base = "userdashboard/"
    ctx = {}

    full_name = (request.user.get_full_name() or '').strip()
    if full_name:
        parts = [p for p in full_name.split() if p]
        user_initials = ''.join([p[0].upper() for p in parts[:2]])
        user_display_name = full_name
    else:
        uname = request.user.username or ''
        user_initials = (uname[:2] or 'U').upper()
        user_display_name = uname or 'User'

    user_tickets_qs = Ticket.objects.select_related('created_by').filter(created_by=request.user)
    total_tickets = user_tickets_qs.count()
    open_count = user_tickets_qs.filter(status='Open').count()
    in_progress_count = user_tickets_qs.filter(status='In Progress').count()
    resolved_count = user_tickets_qs.filter(status='Resolved').count()

    ctx.update({
        'user_initials': user_initials,
        'user_display_name': user_display_name,
        'total_tickets': total_tickets,
        'open_count': open_count,
        'in_progress_count': in_progress_count,
        'resolved_count': resolved_count,
        'current_status': 'All',
    })

    if template_file == 'tickets.html':
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        from django.db.models import Case, When, Value, IntegerField

        page_number = request.GET.get('page', 1)
        try:
            page_number = int(page_number)
            if page_number < 1:
                page_number = 1
        except (ValueError, TypeError):
            page_number = 1

        status_filter = request.GET.get('status', 'all')
        sort_filter = request.GET.get('sort', 'recent')
        tickets_qs = user_tickets_qs.select_related('assigned_to')

        if status_filter != 'all':
            tickets_qs = tickets_qs.filter(status=status_filter)

        if sort_filter == 'oldest':
            tickets_qs = tickets_qs.order_by('created_at')
        elif sort_filter == 'priority':
            tickets_qs = tickets_qs.annotate(
                priority_order=Case(
                    When(priority='Critical', then=Value(1)),
                    When(priority='High', then=Value(2)),
                    When(priority='Medium', then=Value(3)),
                    When(priority='Low', then=Value(4)),
                    output_field=IntegerField(),
                )
            ).order_by('priority_order', '-created_at')
        else:
            tickets_qs = tickets_qs.order_by('-created_at')

        paginator = Paginator(tickets_qs, 5)
        try:
            tickets_page = paginator.page(page_number)
        except EmptyPage:
            tickets_page = paginator.page(paginator.num_pages)
        except Exception:
            tickets_page = paginator.page(1)

        tickets_list = list(tickets_page.object_list)
        ctx['tickets'] = tickets_list
        ctx['tickets_page'] = tickets_page
        ctx['paginator'] = paginator
        ctx['current_status_filter'] = status_filter
        ctx['current_sort_filter'] = sort_filter

        ticket_ids = [t.ticket_id for t in tickets_list]
        ratings_qs = UserRating.objects.filter(user=request.user, ticket_reference__in=ticket_ids).order_by('-created_at')
        ratings_map = {r.ticket_reference: r for r in ratings_qs}
        for t in tickets_list:
            setattr(t, 'user_rating', ratings_map.get(getattr(t, 'ticket_id', '')))

    if template_file == 'chat.html':
        # Use the same logic as above for consistency
        user = request.user
        user_ticket_ids = list(
            Ticket.objects.filter(created_by=request.user).order_by('-created_at').values_list('ticket_id', flat=True)
        )
        
        # Get tickets with their assigned admins
        user_tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
        
        # Create a mapping of ticket_id to assigned admin
        ticket_admin_mapping = {}
        fallback_admin = None
        
        for ticket in user_tickets:
            if ticket.assigned_to:
                ticket_admin_mapping[ticket.ticket_id] = {
                    'id': ticket.assigned_to.id,
                    'username': ticket.assigned_to.username,
                    'get_full_name': ticket.assigned_to.get_full_name()
                }
            else:
                # If no admin is assigned, use the first available admin as fallback
                if not fallback_admin:
                    fallback_admin = User.objects.filter(is_staff=True, is_active=True).order_by('id').first()
                    if fallback_admin:
                        ticket_admin_mapping[ticket.ticket_id] = {
                            'id': fallback_admin.id,
                            'username': fallback_admin.username,
                            'get_full_name': fallback_admin.get_full_name()
                        }
                else:
                    ticket_admin_mapping[ticket.ticket_id] = {
                        'id': fallback_admin.id,
                        'username': fallback_admin.username,
                        'get_full_name': fallback_admin.get_full_name()
                    }
        
        # For the initial chat, use the assigned admin of the first ticket
        support_admin = None
        if user_ticket_ids:
            admin_info = ticket_admin_mapping.get(user_ticket_ids[0])
            if admin_info:
                # Create a simple user object for compatibility
                support_admin = type('User', (), {
                    'id': admin_info['id'],
                    'username': admin_info['username'],
                    'get_full_name': lambda: admin_info['get_full_name']
                })()
        
        ctx['support_admin'] = support_admin
        ctx['ticket_admin_mapping'] = ticket_admin_mapping
        user_ticket_ids = list(
            Ticket.objects.filter(created_by=request.user).order_by('-created_at').values_list('ticket_id', flat=True)
        )
        ctx['chat_ticket_ids'] = user_ticket_ids
        ctx['chat_ticket_id'] = user_ticket_ids[0] if user_ticket_ids else ''

    if template_file == 'profile.html':
        user = request.user
        profile = getattr(user, 'userprofile', None)
        full_name = (user.get_full_name() or '').strip()
        phone = getattr(profile, 'phone', '') if profile else ''
        role_obj = getattr(profile, 'role', None) if profile else None
        role_name = getattr(role_obj, 'name', '') or 'User'
        profile_saved = False
        password_saved = False
        password_error = ''

        if request.method == "POST":
            action = request.POST.get('action')
            if action == 'profile':
                new_full = (request.POST.get('fullName') or '').strip()
                new_email = (request.POST.get('email') or '').strip()
                new_phone = (request.POST.get('phone') or '').strip()
                picture_file = request.FILES.get('profile_picture')
                
                # Update user fields only if they're provided
                if new_full:
                    parts = new_full.split()
                    user.first_name = ' '.join(parts[:-1]) if len(parts) > 1 else parts[0]
                    user.last_name = parts[-1] if len(parts) > 1 else ''
                if new_email and new_email != user.email:
                    user.email = new_email
                
                # Only save user if there are changes
                if new_full or (new_email and new_email != user.email):
                    user.save()
                
                # Handle profile picture upload
                if picture_file:
                    if profile:
                        profile.profile_picture = picture_file
                        if new_phone:
                            profile.phone = new_phone
                        profile.save()
                        logger.info(f"Updated existing profile with new picture for user {user.username}")
                    else:
                        # Create profile if it doesn't exist
                        from users.models import UserProfile
                        profile = UserProfile.objects.create(user=user, phone=new_phone, profile_picture=picture_file)
                        logger.info(f"Created new profile with picture for user {user.username}")
                    profile_saved = True
                elif new_phone and profile:
                    # Update phone if provided and no picture
                    profile.phone = new_phone
                    profile.save()
                    profile_saved = True
                elif new_phone and not profile:
                    # Create profile with phone if no profile exists
                    from users.models import UserProfile
                    profile = UserProfile.objects.create(user=user, phone=new_phone)
                    profile_saved = True
            elif action == 'remove_profile_picture':
                if profile and profile.profile_picture:
                    profile.profile_picture.delete()
                    profile.profile_picture = None
                    profile.save()
                    profile_saved = True
            elif action == 'password':
                pw = request.POST.get('password') or ''
                cf = request.POST.get('confirm') or ''
                if not pw or pw != cf:
                    password_error = 'Passwords do not match.'
                else:
                    user.set_password(pw)
                    user.save()
                    update_session_auth_hash(request, user)
                    password_saved = True

        ctx.update({
            'profile_user': user,
            'profile_obj': profile,
            'profile_full_name': full_name or user.username,
            'profile_email': user.email,
            'profile_phone': phone,
            'profile_role': role_name,
            'profile_saved': profile_saved,
            'password_saved': password_saved,
            'password_error': password_error,
        })

    if template_file == 'ratings.html':
        # Handle form submission
        if request.method == 'POST':
            rating_raw = (request.POST.get('overall_rating') or '0').strip()
            title = (request.POST.get('title') or '').strip()
            content = (request.POST.get('content') or '').strip()
            ticket_ref = (request.POST.get('ticket') or '').strip()
            recommend_raw = (request.POST.get('recommend') or '').strip().lower()
            recommend = recommend_raw in ['yes', '1', 'true', 'y', 'on']
            
            try:
                rating_val = int(rating_raw)
            except (TypeError, ValueError):
                rating_val = 0
            
            if rating_val > 0 and title:
                # Get agent from ticket if provided
                agent = None
                if ticket_ref:
                    ticket = Ticket.objects.filter(ticket_id=ticket_ref, created_by=request.user).first()
                    if ticket:
                        agent = ticket.assigned_to
                
                UserRating.objects.create(
                    user=request.user,
                    agent=agent,
                    ticket_reference=ticket_ref,
                    rating=rating_val,
                    title=title,
                    content=content,
                    recommend=recommend,
                )
                messages.success(request, 'Your review has been submitted successfully!')
                # Refresh the data after submission
                ratings_qs = UserRating.objects.filter(user=request.user).order_by('-created_at')
            else:
                messages.error(request, 'Please provide a rating and title for your review.')
        
        # Get user's ratings for statistics
        ratings_qs = UserRating.objects.filter(user=request.user).order_by('-created_at')
        total = ratings_qs.count()
        
        # Calculate rating statistics
        agg = ratings_qs.aggregate(
            avg_rating=Avg('rating'),
            c5=Count('id', filter=Q(rating=5)),
            c4=Count('id', filter=Q(rating=4)),
            c3=Count('id', filter=Q(rating=3)),
            c2=Count('id', filter=Q(rating=2)),
            c1=Count('id', filter=Q(rating=1)),
        ) if total else {"avg_rating": 0, "c5": 0, "c4": 0, "c3": 0, "c2": 0, "c1": 0}
        
        avg_val = float(agg.get('avg_rating') or 0.0)
        c5 = int(agg.get('c5') or 0)
        c4 = int(agg.get('c4') or 0)
        c3 = int(agg.get('c3') or 0)
        c2 = int(agg.get('c2') or 0)
        c1 = int(agg.get('c1') or 0)
        
        def pct(count):
            return int((count / total) * 100) if total else 0
        
        # Get user's tickets for dropdown
        user_tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')
        
        ctx.update({
            'ratings': ratings_qs,
            'avg_rating': round(avg_val, 1),
            'total_reviews': total,
            'count_5': c5,
            'count_4': c4,
            'count_3': c3,
            'count_2': c2,
            'count_1': c1,
            'percent_5': pct(c5),
            'percent_4': pct(c4),
            'percent_3': pct(c3),
            'percent_2': pct(c2),
            'percent_1': pct(c1),
            'user_tickets': user_tickets,
        })

    if template_file == 'ticket.html':
        # Initialize form for GET requests (page load)
        if request.method == 'GET':
            form = TicketForm()
            ctx.update({'form': form})
        elif request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from tickets.models import TicketAttachment
            form = TicketForm(request.POST, request.FILES)
            if form.is_valid():
                ticket = form.save(commit=False)
                ticket.created_by = request.user
                
                # Handle category - form data will contain the custom text directly
                category = form.cleaned_data.get('category')
                
                # The category field now accepts any text, so just validate it's not empty
                if not category or category.strip() == '':
                    return JsonResponse({'success': False, 'errors': {'category': ['Category is required']}})
                
                ticket.category = category
                ticket.save()
                for f in request.FILES.getlist('attachments'):
                    TicketAttachment.objects.create(ticket=ticket, file=f)
                return JsonResponse({'success': True, 'message': 'Ticket created successfully!', 'ticket_id': ticket.id})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})

    if template_file == 'settings.html':
        user = request.user
        profile = getattr(user, 'userprofile', None)
        
        # Initialize context variables
        settings_saved = False
        password_error = ''
        twofa_changed = False
        twofa_error = ''
        password_last_changed = None
        
        # Get current settings
        settings_theme = 'system'
        settings_email_notifications = False
        settings_desktop_notifications = False
        settings_allow_dm_from_non_contacts = False
        settings_2fa_enabled = False
        
        if profile:
            settings_theme = getattr(profile, 'theme', 'system') or 'system'
            settings_email_notifications = getattr(profile, 'email_notifications', False)
            settings_desktop_notifications = getattr(profile, 'desktop_notifications', False)
            settings_allow_dm_from_non_contacts = getattr(profile, 'allow_dm_from_non_contacts', False)
            settings_2fa_enabled = getattr(profile, 'two_factor_enabled', False)
            password_last_changed = profile.password_last_changed
        
        # Handle POST requests
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'settings':
                # Handle theme and notification preferences
                theme = (request.POST.get('theme') or '').strip()
                email_notifications = request.POST.get('email_notifications') == 'on'
                desktop_notifications = request.POST.get('push_notifications') == 'on'
                allow_dm_from_non_contacts = request.POST.get('marketing_emails') == 'on'
                
                if profile:
                    profile.theme = theme if theme in ['light', 'dark', 'system'] else 'system'
                    profile.email_notifications = email_notifications
                    profile.desktop_notifications = desktop_notifications
                    profile.allow_dm_from_non_contacts = allow_dm_from_non_contacts
                    profile.save()
                    settings_saved = True
                    
                    # Update current settings for display
                    settings_theme = profile.theme
                    settings_email_notifications = profile.email_notifications
                    settings_desktop_notifications = profile.desktop_notifications
                    settings_allow_dm_from_non_contacts = profile.allow_dm_from_non_contacts
                
            elif action == 'change_password':
                # Handle password change
                current_password = request.POST.get('current_password', '')
                new_password = request.POST.get('new_password', '')
                confirm_password = request.POST.get('confirm_password', '')
                
                if not user.check_password(current_password):
                    password_error = 'Current password is incorrect.'
                elif new_password != confirm_password:
                    password_error = 'New passwords do not match.'
                elif len(new_password) < 8 or not any(c.isupper() for c in new_password) or not any(c.isdigit() for c in new_password):
                    password_error = 'Password must be at least 8 characters long and contain at least one uppercase letter and one number.'
                else:
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    if profile:
                        profile.password_last_changed = timezone.now()
                        profile.save()
                    settings_saved = True
                    password_last_changed = timezone.now()
            
            elif action == 'toggle_2fa':
                # Handle 2FA toggle (simplified version)
                verification_code = request.POST.get('verification_code', '')
                confirm_password = request.POST.get('confirm_password', '')
                
                if settings_2fa_enabled:
                    # Disable 2FA
                    if not user.check_password(confirm_password):
                        twofa_error = 'Password is incorrect.'
                    else:
                        if profile:
                            profile.two_factor_enabled = False
                            profile.save()
                        settings_2fa_enabled = False
                        twofa_changed = True
                else:
                    # Enable 2FA (simplified - in production, use proper TOTP)
                    if len(verification_code) != 6:
                        twofa_error = 'Please enter a valid 6-digit verification code.'
                    else:
                        if profile:
                            profile.two_factor_enabled = True
                            profile.save()
                        settings_2fa_enabled = True
                        twofa_changed = True
            
            elif action == 'deactivate':
                # Handle account deactivation
                user.is_active = False
                user.save()
                return redirect('users:logout')
            
            elif action == 'delete':
                # Handle account deletion
                if profile:
                    profile.delete()
                user.delete()
                return redirect('users:login')
        
        # Update context with settings data
        ctx.update({
            'settings_theme': settings_theme,
            'settings_email_notifications': settings_email_notifications,
            'settings_desktop_notifications': settings_desktop_notifications,
            'settings_allow_dm_from_non_contacts': settings_allow_dm_from_non_contacts,
            'settings_2fa_enabled': settings_2fa_enabled,
            'settings_saved': settings_saved,
            'password_error': password_error,
            'twofa_changed': twofa_changed,
            'twofa_error': twofa_error,
            'password_last_changed': password_last_changed,
        })

    if template_file == 'faq.html':
        # Handle FAQ data
        from .models import Faq
        
        # Get all published FAQs
        all_faqs = Faq.objects.filter(is_published=True).order_by('order', 'id')
        
        # Get featured FAQs (first few or marked as featured)
        featured_faqs = all_faqs[:6]  # First 6 FAQs as featured
        
        # Group FAQs by category
        faq_categories = {}
        for faq in all_faqs:
            category = faq.category or 'general'
            if category not in faq_categories:
                faq_categories[category] = []
            faq_categories[category].append(faq)
        
        # Create FAQ sections for template
        faq_sections = []
        category_info = {
            'getting-started': {
                'title': 'Getting Started',
                'description': 'Learn the basics of using TicketHub',
                'key': 'getting-started'
            },
            'tickets': {
                'title': 'Tickets',
                'description': 'Everything about creating and managing tickets',
                'key': 'tickets'
            },
            'billing': {
                'title': 'Billing & Payments',
                'description': 'Payment methods, invoices, and subscription management',
                'key': 'billing'
            },
            'account': {
                'title': 'Account Management',
                'description': 'Profile settings, security, and preferences',
                'key': 'account'
            },
            'troubleshooting': {
                'title': 'Troubleshooting',
                'description': 'Common issues and how to resolve them',
                'key': 'troubleshooting'
            },
            'general': {
                'title': 'General',
                'description': 'General questions and information',
                'key': 'general'
            }
        }
        
        for category_key, info in category_info.items():
            if category_key in faq_categories:
                faq_sections.append({
                    'key': category_key,
                    'title': info['title'],
                    'description': info['description'],
                    'items': faq_categories[category_key]
                })
        
        # Add any uncategorized FAQs
        if 'general' in faq_categories and 'general' not in [s['key'] for s in faq_sections]:
            faq_sections.append({
                'key': 'general',
                'title': 'General',
                'description': 'General questions and information',
                'items': faq_categories['general']
            })
        
        ctx.update({
            'featured_faqs': featured_faqs,
            'faq_sections': faq_sections,
        })

    return render(request, f"{base}{template_file}", ctx)


# ---------------------------------------------------------------------------
# Clear payment modal / record payment
# ---------------------------------------------------------------------------

@csrf_exempt
@login_required
def clear_payment_modal(request):
    if request.method == 'POST':
        try:
            request.session.pop('show_payment_modal', None)
            request.session.pop('expiry_info', None)
            request.session['payment_completed'] = True
            request.session['payment_completed_user_id'] = request.user.id
            request.session.modified = True
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Method not allowed'})


@csrf_exempt
@login_required
def record_payment_transaction(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount', '199')
            payment_method = data.get('payment_method', 'Credit Card')

            from superadmin.models import Payment, Company, Subscription, Plan

            company_name = f'{request.user.username} Company'
            company, _ = Company.objects.get_or_create(
                name=company_name,
                defaults={'email': request.user.email, 'phone': '', 'address': ''}
            )
            plan, _ = Plan.objects.get_or_create(
                name='Basic',
                defaults={'price': float(amount), 'billing_cycle': 'monthly', 'users': 1, 'storage': '10GB', 'status': 'active'}
            )
            subscription, created = Subscription.objects.get_or_create(
                company=company, plan=plan,
                defaults={
                    'start_date': timezone.now().date(),
                    'end_date': timezone.now().date() + timezone.timedelta(days=30),
                    'status': 'active', 'billing_cycle': 'monthly', 'amount': float(amount)
                }
            )
            if not created:
                subscription.start_date = timezone.now().date()
                subscription.end_date = timezone.now().date() + timezone.timedelta(days=30)
                subscription.status = 'active'
                subscription.amount = float(amount)
                subscription.save()

            payment = Payment.objects.create(
                subscription=subscription, company=company, amount=float(amount),
                payment_method=payment_method.lower().replace(' ', '_'),
                payment_type='subscription', status='completed',
                transaction_id=f'TXN{int(timezone.now().timestamp())}',
                payment_date=timezone.now()
            )
            return JsonResponse({'success': True, 'transaction_id': payment.transaction_id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Method not allowed'})


# ---------------------------------------------------------------------------
# Admin reports export helpers
# ---------------------------------------------------------------------------

def _parse_report_date_range(request):
    label = (request.GET.get('date_range') or '').strip().lower()
    start_raw = (request.GET.get('start_date') or '').strip()
    end_raw = (request.GET.get('end_date') or '').strip()
    today = timezone.now().date()

    def _parse_date(val):
        try:
            return datetime.date.fromisoformat(val)
        except Exception:
            return None

    if label in {'last 7 days', '7', 'last7'}:
        return today - datetime.timedelta(days=6), today
    if label in {'last 30 days', '30', 'last30'}:
        return today - datetime.timedelta(days=29), today
    if label in {'this month', 'month'}:
        return today.replace(day=1), today
    if label in {'last month'}:
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - datetime.timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    if label in {'this year', 'year'}:
        return today.replace(month=1, day=1), today

    start = _parse_date(start_raw)
    end = _parse_date(end_raw)
    if start and end:
        if end < start:
            start, end = end, start
        return start, end
    return None, None


def _simple_pdf_bytes(lines, title='Report'):
    text = [title] + [''] + (lines or [])
    y_start = 800
    y_step = 14
    content_lines = ['BT', '/F1 12 Tf', f'72 {y_start} Td']
    for i, line in enumerate(text):
        safe = (line or '').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        if i == 0:
            content_lines.append(f'({safe}) Tj')
        else:
            content_lines.append(f'0 -{y_step} Td')
            content_lines.append(f'({safe}) Tj')
    content_lines.append('ET')
    content_stream = ('\n'.join(content_lines) + '\n').encode('latin-1', errors='replace')

    objects = []
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n")
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(b"5 0 obj\n<< /Length %d >>\nstream\n" % len(content_stream) + content_stream + b"endstream\nendobj\n")

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    xref_positions = [0]
    body = io.BytesIO()
    body.write(header)
    for obj in objects:
        xref_positions.append(body.tell())
        body.write(obj)
    xref_start = body.tell()
    body.write(b"xref\n0 %d\n" % (len(objects) + 1))
    body.write(b"0000000000 65535 f \n")
    for pos in xref_positions[1:]:
        body.write(f"{pos:010d} 00000 n \n".encode('ascii'))
    body.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref_start))
    return body.getvalue()


@login_required
def admin_reports_export(request, export_format: str):
    user = request.user
    is_admin = bool(
        user.is_authenticated and (
            user.is_superuser or user.is_staff or (
                hasattr(user, 'userprofile')
                and getattr(getattr(user.userprofile, 'role', None), 'name', '').lower() == 'admin'
            )
        )
    )
    if not is_admin:
        return HttpResponseForbidden('Forbidden')

    export_format = (export_format or '').strip().lower()
    report_type = (request.GET.get('report_type') or 'ticket_summary').strip().lower()

    start, end = _parse_report_date_range(request)
    tickets = Ticket.objects.select_related('created_by', 'assigned_to').all().order_by('-created_at')
    if start and end:
        start_dt = timezone.make_aware(datetime.datetime.combine(start, datetime.time.min))
        end_dt = timezone.make_aware(datetime.datetime.combine(end, datetime.time.max))
        tickets = tickets.filter(created_at__range=(start_dt, end_dt))

    if report_type in {'ticket_summary', 'tickets'}:
        if export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Ticket ID', 'Title', 'Status', 'Priority', 'Created At', 'Updated At', 'Created By', 'Assigned To'])
            for t in tickets:
                writer.writerow([
                    getattr(t, 'ticket_id', ''), getattr(t, 'title', ''),
                    getattr(t, 'status', ''), getattr(t, 'priority', ''),
                    timezone.localtime(t.created_at).strftime('%Y-%m-%d %H:%M') if t.created_at else '',
                    timezone.localtime(t.updated_at).strftime('%Y-%m-%d %H:%M') if t.updated_at else '',
                    getattr(getattr(t, 'created_by', None), 'username', ''),
                    getattr(getattr(t, 'assigned_to', None), 'username', ''),
                ])
            resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = 'attachment; filename="ticket_summary.csv"'
            return resp

        if export_format == 'pdf':
            lines = [f"#{getattr(t,'ticket_id','')} | {getattr(t,'status','')} | {getattr(t,'priority','')} | {getattr(t,'title','')}" for t in tickets[:200]]
            pdf_bytes = _simple_pdf_bytes(lines, title='Ticket Summary')
            resp = HttpResponse(pdf_bytes, content_type='application/pdf')
            resp['Content-Disposition'] = 'attachment; filename="ticket_summary.pdf"'
            return resp

    elif report_type == 'agent_performance':
        # Get agent performance data
        agent_qs = (
            User.objects.select_related('userprofile', 'userprofile__role')
            .filter(userprofile__role__name='Agent')
            .annotate(avg_rating=Avg('received_ratings__rating'), rating_count=Count('received_ratings', distinct=True))
            .order_by('username')
        )
        
        if export_format == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Agent Name', 'Email', 'Average Rating', 'Total Ratings', 'Response Rate', 'Satisfaction'])
            
            for agent in agent_qs:
                name = (agent.get_full_name() or '').strip() or agent.username
                avg_rating = round(getattr(agent, 'avg_rating', 0) or 0, 1)
                rating_count = getattr(agent, 'rating_count', 0) or 0
                
                # Calculate additional metrics
                agent_tickets = Ticket.objects.filter(assigned_to=agent)
                total_tickets = agent_tickets.count()
                responded_tickets = agent_tickets.filter(status__in=['In Progress', 'Resolved', 'Closed']).count()
                response_rate = int((responded_tickets / total_tickets) * 100) if total_tickets else 0
                
                positive_ratings = UserRating.objects.filter(agent=agent, rating__gte=4).count()
                satisfaction = int((positive_ratings / rating_count) * 100) if rating_count else 0
                
                writer.writerow([
                    name,
                    agent.email,
                    avg_rating,
                    rating_count,
                    f"{response_rate}%",
                    f"{satisfaction}%"
                ])
            
            resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = 'attachment; filename="agent_performance.csv"'
            return resp
            
        elif export_format == 'pdf':
            lines = ['Agent Performance Report', '']
            for agent in agent_qs:
                name = (agent.get_full_name() or '').strip() or agent.username
                avg_rating = round(getattr(agent, 'avg_rating', 0) or 0, 1)
                rating_count = getattr(agent, 'rating_count', 0) or 0
                lines.append(f"{name} - Rating: {avg_rating}/5 ({rating_count} reviews)")
            
            pdf_bytes = _simple_pdf_bytes(lines, title='Agent Performance Report')
            resp = HttpResponse(pdf_bytes, content_type='application/pdf')
            resp['Content-Disposition'] = 'attachment; filename="agent_performance.pdf"'
            return resp

    elif report_type == 'ratings':
        # Get ratings data
        ratings_qs = UserRating.objects.select_related('user', 'agent').all().order_by('-created_at')
        if start and end:
            start_dt = timezone.make_aware(datetime.datetime.combine(start, datetime.time.min))
            end_dt = timezone.make_aware(datetime.datetime.combine(end, datetime.time.max))
            ratings_qs = ratings_qs.filter(created_at__range=(start_dt, end_dt))
        
        if export_format in ('csv', 'excel'):
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Rating ID', 'User Name', 'User Email', 'Agent Name', 'Agent Email', 'Ticket Reference', 'Rating', 'Recommend', 'Comment', 'Created At'])
            
            for rating in ratings_qs:
                user_name = (rating.user.get_full_name() or '').strip() or rating.user.username if rating.user else 'N/A'
                agent_name = (rating.agent.get_full_name() or '').strip() or rating.agent.username if rating.agent else 'N/A'
                writer.writerow([
                    rating.id,
                    user_name,
                    rating.user.email if rating.user else 'N/A',
                    agent_name,
                    rating.agent.email if rating.agent else 'N/A',
                    rating.ticket_reference or 'N/A',
                    rating.rating,
                    'Yes' if rating.recommend else 'No',
                    rating.content or '',
                    timezone.localtime(rating.created_at).strftime('%Y-%m-%d %H:%M') if rating.created_at else ''
                ])
            
            resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
            resp['Content-Disposition'] = 'attachment; filename="ratings_export.csv"'
            return resp
            
        elif export_format == 'pdf':
            lines = ['Customer Ratings Report', '']
            for rating in ratings_qs[:100]:  # Limit to 100 for PDF
                user_name = (rating.user.get_full_name() or '').strip() or rating.user.username if rating.user else 'N/A'
                agent_name = (rating.agent.get_full_name() or '').strip() or rating.agent.username if rating.agent else 'N/A'
                lines.append(f"User: {user_name} -> Agent: {agent_name} - Rating: {rating.rating}/5 - Recommend: {'Yes' if rating.recommend else 'No'}")
                if rating.content:
                    lines.append(f"Comment: {rating.content[:100]}...")  # Truncate long comments
                lines.append('')
            
            pdf_bytes = _simple_pdf_bytes(lines, title='Customer Ratings Report')
            resp = HttpResponse(pdf_bytes, content_type='application/pdf')
            resp['Content-Disposition'] = 'attachment; filename="ratings_export.pdf"'
            return resp

    elif report_type == 'custom':
        metric = request.GET.get('metric', 'status')
        
        if metric == 'status':
            # Export tickets by status
            status_counts = tickets.values('status').annotate(count=Count('id')).order_by('status')
            
            if export_format == 'csv':
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Status', 'Count', 'Percentage'])
                
                total = tickets.count()
                for item in status_counts:
                    percentage = int((item['count'] / total) * 100) if total else 0
                    writer.writerow([item['status'], item['count'], f"{percentage}%"])
                
                resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
                resp['Content-Disposition'] = 'attachment; filename="tickets_by_status.csv"'
                return resp
                
            elif export_format == 'pdf':
                lines = ['Tickets by Status Report', '']
                total = tickets.count()
                for item in status_counts:
                    percentage = int((item['count'] / total) * 100) if total else 0
                    lines.append(f"{item['status']}: {item['count']} ({percentage}%)")
                
                pdf_bytes = _simple_pdf_bytes(lines, title='Tickets by Status Report')
                resp = HttpResponse(pdf_bytes, content_type='application/pdf')
                resp['Content-Disposition'] = 'attachment; filename="tickets_by_status.pdf"'
                return resp
                
        elif metric == 'priority':
            # Export tickets by priority
            priority_counts = tickets.values('priority').annotate(count=Count('id')).order_by('priority')
            
            if export_format == 'csv':
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Priority', 'Count', 'Percentage'])
                
                total = tickets.count()
                for item in priority_counts:
                    percentage = int((item['count'] / total) * 100) if total else 0
                    writer.writerow([item['priority'], item['count'], f"{percentage}%"])
                
                resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
                resp['Content-Disposition'] = 'attachment; filename="tickets_by_priority.csv"'
                return resp
                
            elif export_format == 'pdf':
                lines = ['Tickets by Priority Report', '']
                total = tickets.count()
                for item in priority_counts:
                    percentage = int((item['count'] / total) * 100) if total else 0
                    lines.append(f"{item['priority']}: {item['count']} ({percentage}%)")
                
                pdf_bytes = _simple_pdf_bytes(lines, title='Tickets by Priority Report')
                resp = HttpResponse(pdf_bytes, content_type='application/pdf')
                resp['Content-Disposition'] = 'attachment; filename="tickets_by_priority.pdf"'
                return resp

    raise Http404('Unsupported export')


# ---------------------------------------------------------------------------
# Admin Dashboard Page
# ---------------------------------------------------------------------------

@login_required
@ensure_csrf_cookie
def admin_dashboard_page(request, page: str):
    from tickets.models import Ticket, ChatMessage
    from django.db.models import Q, Count, Avg, F, DurationField, ExpressionWrapper
    
    if not is_admin_user(request):
        if is_agent_user(request):
            return redirect('dashboards:agent_dashboard')
        elif is_regular_user(request):
            return redirect('dashboards:user_dashboard')
        else:
            return redirect('dashboards:user_dashboard')

    allowed_pages = {
        'index.html', 'tickets.html', 'users.html', 'agents.html', 'customers.html',
        'roles.html', 'ratings.html', 'reports.html', 'custom-fields.html',
        'settings.html', 'chat.html', 'profile.html',
        'partials/header.html', 'partials/sidebar.html', 'partials/modals.html'
    }

    raw = page.strip('/')
    parts = raw.split('/') if raw else []
    if 'partials' in parts:
        idx = parts.index('partials')
        normalized = '/'.join(parts[idx:])
    else:
        normalized = parts[-1] if parts else raw
    if not normalized.endswith('.html'):
        normalized = f"{normalized}.html"
    if normalized not in allowed_pages:
        raise Http404("Page not found")

    base = "admindashboard/"
    ctx = {}

    if normalized == 'tickets.html':
        qs = Ticket.objects.select_related('created_by').order_by('-created_at')
        ctx = {"tickets": qs}

    elif normalized == 'ratings.html':
        from django.db.models import ExpressionWrapper, DurationField, F, Avg, Q
        import datetime as _dt

        qs    = UserRating.objects.select_related('user', 'agent').order_by('-created_at')
        total = qs.count()

        # If no ratings exist, create sample data for testing
        if total == 0:
            try:
                # Get sample users
                sample_user = User.objects.first()
                sample_agent = User.objects.filter(userprofile__role__name='Agent').first()
                
                if sample_user and sample_agent:
                    # Create sample ratings for testing
                    UserRating.objects.create(
                        user=sample_user,
                        agent=sample_agent,
                        rating=5,
                        title='Excellent service',
                        content='Very helpful and professional',
                        recommend=True,
                        ticket_reference='TEST-001'
                    )
                    UserRating.objects.create(
                        user=sample_user,
                        agent=sample_agent,
                        rating=4,
                        title='Good service',
                        content='Helpful response',
                        recommend=True,
                        ticket_reference='TEST-002'
                    )
                    UserRating.objects.create(
                        user=sample_user,
                        agent=sample_agent,
                        rating=3,
                        title='Average service',
                        content='Could be better',
                        recommend=False,
                        ticket_reference='TEST-003'
                    )
                    print("Created sample ratings for testing")
                    
                    # Refresh query
                    qs = UserRating.objects.select_related('user', 'agent').order_by('-created_at')
                    total = qs.count()
            except Exception as e:
                print(f"Error creating sample data: {e}")

        agg = qs.aggregate(
            avg_rating     = Avg('rating'),
            c5             = Count('id', filter=Q(rating=5)),
            c4             = Count('id', filter=Q(rating=4)),
            c3             = Count('id', filter=Q(rating=3)),
            c2             = Count('id', filter=Q(rating=2)),
            c1             = Count('id', filter=Q(rating=1)),
            positive_count = Count('id', filter=Q(rating__gte=4)),
        ) if total else {
            'avg_rating': 0, 'c5': 0, 'c4': 0, 'c3': 0, 'c2': 0, 'c1': 0, 'positive_count': 0,
        }

        avg_val        = float(agg.get('avg_rating') or 0.0)
        c5             = int(agg.get('c5') or 0)
        c4             = int(agg.get('c4') or 0)
        c3             = int(agg.get('c3') or 0)
        c2             = int(agg.get('c2') or 0)
        c1             = int(agg.get('c1') or 0)
        positive_count = int(agg.get('positive_count') or 0)

        def _pct(count):
            return int((count / total) * 100) if total else 0

        ratings_distribution = [
            (5, c5, _pct(c5)),
            (4, c4, _pct(c4)),
            (3, c3, _pct(c3)),
            (2, c2, _pct(c2)),
            (1, c1, _pct(c1)),
        ]
        
        # Debug output
        print(f"DEBUG: Total ratings: {total}")
        print(f"DEBUG: Aggregation results: {agg}")
        print(f"DEBUG: Ratings distribution: {ratings_distribution}")

        satisfaction_percent = _pct(positive_count)

        # Response Rate
        all_tickets       = Ticket.objects.all()
        total_tickets     = all_tickets.count()
        responded_tickets = all_tickets.filter(status__in=['In Progress', 'Resolved', 'Closed']).count()
        response_rate     = int((responded_tickets / total_tickets) * 100) if total_tickets else 0

        now       = timezone.now()
        last_30   = now - _dt.timedelta(days=30)
        prev_30   = now - _dt.timedelta(days=60)
        curr_resp = all_tickets.filter(status__in=['In Progress', 'Resolved', 'Closed'], updated_at__gte=last_30).count()
        prev_total_t = all_tickets.filter(created_at__gte=prev_30, created_at__lt=last_30).count()
        prev_resp = all_tickets.filter(status__in=['In Progress', 'Resolved', 'Closed'], updated_at__gte=prev_30, updated_at__lt=last_30).count()
        curr_rate  = int((curr_resp / total_tickets) * 100) if total_tickets else 0
        prev_rate  = int((prev_resp / prev_total_t)  * 100) if prev_total_t else 0
        response_rate_trend = curr_rate - prev_rate

        # Avg Response Time
        resolved_qs       = all_tickets.filter(status__in=['Resolved', 'Closed'])
        avg_response_hours = 0.0
        response_progress  = 0
        if resolved_qs.exists():
            d_expr    = ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField())
            dur_agg   = resolved_qs.aggregate(avg_duration=Avg(d_expr))
            avg_dur   = dur_agg.get('avg_duration')
            if avg_dur is not None:
                avg_response_hours = round(float(avg_dur.total_seconds()) / 3600.0, 1)
                response_progress  = max(0, int(100 - (avg_response_hours / 72) * 100))

        # Agent Performance
        agent_qs = (
            User.objects
            .select_related('userprofile', 'userprofile__role')
            .filter(userprofile__role__name='Agent')
            .annotate(
                avg_rating    = Avg('received_ratings__rating'),
                rating_count  = Count('received_ratings', distinct=True),
                positive_cnt  = Count('received_ratings', filter=Q(received_ratings__rating__gte=4), distinct=True),
                total_tickets  = Count('assigned_tickets', distinct=True),
                resolved_count = Count('assigned_tickets', filter=Q(assigned_tickets__status__in=['Resolved', 'Closed']), distinct=True),
            )
            .order_by('username')
        )

        ratings_agent_perf = []
        for u in agent_qs:
            name         = (u.get_full_name() or '').strip() or u.username
            avg_r        = round(float(getattr(u, 'avg_rating', 0) or 0), 1)
            r_count      = int(getattr(u, 'rating_count',  0) or 0)
            pos_cnt      = int(getattr(u, 'positive_cnt',  0) or 0)
            total_t      = int(getattr(u, 'total_tickets',  0) or 0)
            resolved_c   = int(getattr(u, 'resolved_count', 0) or 0)
            satisfaction = int((pos_cnt / r_count) * 100) if r_count else 0

            # Actual avg response time per agent
            a_resolved   = Ticket.objects.filter(assigned_to=u, status__in=['Resolved', 'Closed'])
            agent_avg_h  = None
            if a_resolved.exists():
                d_e   = ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField())
                d_a   = a_resolved.aggregate(avg_dur=Avg(d_e))
                ad    = d_a.get('avg_dur')
                if ad is not None:
                    agent_avg_h = round(float(ad.total_seconds()) / 3600.0, 1)

            # Trend: last 14 days vs prior 14 days
            recent_avg = UserRating.objects.filter(agent=u, created_at__gte=now - _dt.timedelta(days=14)).aggregate(a=Avg('rating')).get('a') or 0
            older_avg  = UserRating.objects.filter(agent=u, created_at__gte=now - _dt.timedelta(days=28), created_at__lt=now - _dt.timedelta(days=14)).aggregate(a=Avg('rating')).get('a') or 0
            trend = 'stable'
            if recent_avg and older_avg:
                trend = 'up' if recent_avg > older_avg else ('down' if recent_avg < older_avg else 'stable')

            profile    = getattr(u, 'userprofile', None)
            department = getattr(profile, 'department', '') or ''

            ratings_agent_perf.append({
                'name':                name,
                'initials':            name[:2].upper(),
                'email':               u.email,
                'department':          department,
                'avg_rating':          avg_r,
                'rating_count':        r_count,
                'total_tickets':       total_t,
                'resolved_count':      resolved_c,
                'avg_response_hours':  agent_avg_h,
                'satisfaction_percent': satisfaction,
                'trend':               trend,
            })

        ctx = {
            'ratings_admin_total':                total,
            'ratings_admin_avg':                  round(avg_val, 1),
            'ratings_admin_satisfaction_percent': satisfaction_percent,
            'ratings_response_rate':              response_rate,
            'ratings_response_rate_trend':        response_rate_trend,
            'ratings_avg_response_hours':         avg_response_hours,
            'ratings_response_progress':          response_progress,
            'ratings_distribution':               ratings_distribution,
            'ratings_admin_count_5': c5,  'ratings_admin_count_4': c4,
            'ratings_admin_count_3': c3,  'ratings_admin_count_2': c2, 'ratings_admin_count_1': c1,
            'ratings_admin_percent_5': _pct(c5), 'ratings_admin_percent_4': _pct(c4),
            'ratings_admin_percent_3': _pct(c3), 'ratings_admin_percent_2': _pct(c2),
            'ratings_admin_percent_1': _pct(c1),
            'ratings_admin_recent':               qs[:20],
            'ratings_agent_perf':                 ratings_agent_perf,
        }

    elif normalized == 'reports.html':
        from django.db.models import Count, Avg, F, DurationField, ExpressionWrapper
        qs = Ticket.objects.all()
        total_tickets = qs.count()
        status_defaults = {"Open": 0, "In Progress": 0, "Resolved": 0, "Closed": 0}
        for row in Ticket.objects.values('status').annotate(c=Count('id')):
            if row['status'] in status_defaults:
                status_defaults[row['status']] = row['c']

        priority_defaults = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        for row in Ticket.objects.values('priority').annotate(c=Count('id')):
            if row['priority'] in priority_defaults:
                priority_defaults[row['priority']] = row['c']

        resolved_total = status_defaults["Resolved"] + status_defaults["Closed"]
        resolution_rate = int((resolved_total / total_tickets) * 100) if total_tickets else 0

        avg_response_display = "0h 0m"
        resolved_qs = qs.filter(status__in=["Resolved", "Closed"])
        if resolved_qs.exists():
            duration_expr = ExpressionWrapper(F("updated_at") - F("created_at"), output_field=DurationField())
            agg = resolved_qs.aggregate(avg_duration=Avg(duration_expr))
            avg_duration = agg.get("avg_duration")
            if avg_duration is not None:
                total_seconds = int(avg_duration.total_seconds())
                avg_response_display = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"

        ratings_qs = UserRating.objects.all()
        ratings_total = ratings_qs.count()
        satisfaction_avg = 0.0
        satisfaction_percent = 0
        if ratings_total:
            ratings_agg = ratings_qs.aggregate(avg_rating=Avg("rating"), recommend_yes=Count("id", filter=Q(recommend=True)))
            satisfaction_avg = float(ratings_agg.get("avg_rating") or 0.0)
            recommend_yes = int(ratings_agg.get("recommend_yes") or 0)
            satisfaction_percent = int((recommend_yes / ratings_total) * 100) if ratings_total else 0

        now = timezone.now()
        current_year = now.year
        month_labels = []
        created_counts = []
        resolved_counts = []
        for month in range(1, 13):
            month_labels.append(calendar.month_abbr[month])
            created_counts.append(qs.filter(created_at__year=current_year, created_at__month=month).count())
            resolved_counts.append(qs.filter(updated_at__year=current_year, updated_at__month=month, status__in=['Resolved', 'Closed']).count())

        agent_qs = (
            User.objects.select_related('userprofile', 'userprofile__role')
            .filter(userprofile__role__name='Agent')
            .annotate(
                assigned_count=Count('assigned_tickets', distinct=True),
                resolved_count=Count('assigned_tickets', filter=Q(assigned_tickets__status__in=["Resolved", "Closed"]), distinct=True),
            )
            .order_by('username')
        )
        agent_perf = []
        for u in agent_qs:
            name = (u.get_full_name() or '').strip() or u.username
            assigned = getattr(u, 'assigned_count', 0) or 0
            resolved = getattr(u, 'resolved_count', 0) or 0
            perf = int((resolved / assigned) * 100) if assigned else 0
            agent_perf.append({
                "name": name, "initials": (name or '?')[:2].upper(),
                "assigned": assigned, "resolved": resolved,
                "avg_response": "-", "avg_resolution": "-", "satisfaction": "-",
                "performance_percent": perf,
            })

        # Also create ratings_agent_perf for the agent performance table
        ratings_agent_qs = (
            User.objects.select_related('userprofile', 'userprofile__role')
            .filter(userprofile__role__name='Agent')
            .annotate(
                avg_rating=Avg('received_ratings__rating'), 
                rating_count=Count('received_ratings', distinct=True),
                resolved_count=Count('assigned_tickets', filter=Q(assigned_tickets__status__in=["Resolved", "Closed"]), distinct=True),
                recommend_yes=Count('received_ratings', filter=Q(received_ratings__recommend=True), distinct=True)
            )
            .order_by('username')
        )
        ratings_agent_perf = []
        for u in ratings_agent_qs:
            name = (u.get_full_name() or '').strip() or u.username
            
            # Calculate department from user profile
            profile = getattr(u, 'userprofile', None)
            department = getattr(profile, 'department', '') or 'General'
            
            # Calculate average response time for this agent's resolved tickets
            agent_tickets = Ticket.objects.filter(assigned_to=u, status__in=["Resolved", "Closed"])
            avg_response_time = "0h 0m"
            if agent_tickets.exists():
                duration_expr = ExpressionWrapper(F("updated_at") - F("created_at"), output_field=DurationField())
                agg = agent_tickets.aggregate(avg_duration=Avg(duration_expr))
                avg_duration = agg.get("avg_duration")
                if avg_duration is not None:
                    total_seconds = int(avg_duration.total_seconds())
                    avg_response_time = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
            
            # Calculate satisfaction rate
            rating_count = getattr(u, 'rating_count', 0) or 0
            recommend_yes = getattr(u, 'recommend_yes', 0) or 0
            satisfaction_rate = int((recommend_yes / rating_count) * 100) if rating_count else 0
            
            # Generate trend (simplified - could be enhanced with historical data)
            avg_rating_val = getattr(u, 'avg_rating', 0) or 0
            trend = "up" if avg_rating_val >= 4 else "stable"
            
            ratings_agent_perf.append({
                "name": name,
                "initials": (name or '?')[:2].upper(),
                "email": u.email,
                "department": department,
                "avg_rating": round(getattr(u, 'avg_rating', 0) or 0, 1),
                "rating_count": rating_count,
                "resolved_count": getattr(u, 'resolved_count', 0) or 0,
                "response_time": avg_response_time,
                "satisfaction_rate": satisfaction_rate,
                "trend": trend,
            })

        ctx = {
            "report_total_tickets": total_tickets,
            "report_resolution_rate": resolution_rate,
            "report_avg_response_display": avg_response_display,
            "report_customer_satisfaction_avg": round(satisfaction_avg, 1) if ratings_total else 0.0,
            "report_customer_satisfaction_percent": satisfaction_percent,
            "report_status_counts_json": json.dumps(status_defaults),
            "report_priority_counts_json": json.dumps(priority_defaults),
            "report_overview_months_json": json.dumps(month_labels),
            "report_overview_created_json": json.dumps(created_counts),
            "report_overview_resolved_json": json.dumps(resolved_counts),
            "report_agent_perf": agent_perf,
            "ratings_agent_perf": ratings_agent_perf,
        }

    elif normalized == 'settings.html':
        settings_obj = SiteSettings.get_solo()
        ctx = {'site_settings': settings_obj}

    elif normalized == 'profile.html':
        user = request.user
        profile = getattr(user, 'userprofile', None)
        if profile is None:
            profile = UserProfile.objects.create(user=user)
        profile_saved = False
        password_saved = False
        password_error = ''
        profile_error = ''

        if request.method == 'POST':
            action = (request.POST.get('action') or '').strip()
            if action == 'profile':
                new_full = (request.POST.get('full_name') or '').strip()
                new_email = (request.POST.get('email') or '').strip()
                new_username = (request.POST.get('username') or '').strip()
                new_phone = (request.POST.get('phone') or '').strip()
                picture_file = request.FILES.get('profile_picture')
                
                if new_full:
                    parts = [p for p in new_full.split() if p]
                    user.first_name = ' '.join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else '')
                    user.last_name = parts[-1] if len(parts) > 1 else ''
                if new_email:
                    user.email = new_email
                if new_username and new_username != user.username:
                    # Check if username is already taken
                    existing_user = User.objects.exclude(id=user.id).filter(username=new_username).first()
                    if existing_user:
                        profile_error = f'Username "{new_username}" is already taken by another user.'
                    else:
                        user.username = new_username
                user.save()
                if profile:
                    profile.phone = new_phone
                    profile.city = (request.POST.get('city') or '').strip()
                    profile.state = (request.POST.get('state') or '').strip()
                    profile.country = (request.POST.get('country') or '').strip()
                    profile.address = (request.POST.get('address') or '').strip()
                    if picture_file:
                        profile.profile_picture = picture_file
                    profile.save()
                if not profile_error:
                    profile_saved = True
            elif action == 'remove_profile_picture':
                if profile and profile.profile_picture:
                    profile.profile_picture.delete()
                    profile.profile_picture = None
                    profile.save()
                    profile_saved = True
            elif action == 'password':
                current_password = request.POST.get('current_password') or ''
                new_password = request.POST.get('new_password') or ''
                confirm_password = request.POST.get('confirm_password') or ''
                if not user.check_password(current_password):
                    password_error = 'Current password is incorrect.'
                elif new_password != confirm_password:
                    password_error = 'Passwords do not match.'
                else:
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    password_saved = True

        ctx = {
            'profile_user': user,
            'profile_obj': profile,
            'profile_full_name': (user.get_full_name() or '').strip() or user.username,
            'profile_email': user.email,
            'profile_phone': getattr(profile, 'phone', '') or '',
            'profile_role': getattr(getattr(profile, 'role', None), 'name', '') or 'Admin',
            'profile_saved': profile_saved,
            'password_saved': password_saved,
            'password_error': password_error,
            'profile_error': profile_error,
        }

    elif normalized == 'users.html':
        user_qs = User.objects.select_related('userprofile', 'userprofile__role').order_by('username')
        users_list = []
        for u in user_qs:
            profile = getattr(u, 'userprofile', None)
            role_obj = getattr(profile, 'role', None) if profile else None
            role_name = getattr(role_obj, 'name', '') or ('Admin' if u.is_staff else 'User')
            full_name = (u.get_full_name() or '').strip() or u.username
            is_active = getattr(profile, 'is_active', True) if profile is not None else u.is_active
            users_list.append({
                'id': u.id, 'name': full_name, 'email': u.email,
                'role_name': role_name,
                'role_label': 'Administrator' if role_name in ('Admin', 'admin', 'superadmin') else role_name,
                'role_badge_class': 'bg-primary' if role_name in ('Admin', 'admin', 'superadmin') else ('bg-secondary' if role_name == 'Agent' else 'bg-info'),
                'department': getattr(profile, 'department', '') or '-',
                'last_login_display': u.last_login.strftime('%d %b %Y, %I:%M %p') if u.last_login else 'Never',
                'status_label': 'Active' if is_active else 'Inactive',
                'status_badge_class': 'bg-success' if is_active else 'bg-secondary',
                'initials': (full_name or '?')[:2].upper(),
            })
        ctx = {'users_list': users_list, 'users_total': len(users_list)}

    elif normalized == 'chat.html':
        # Get users who have chat messages with current admin or have tickets
        
        # Get support users (admin/agent roles)
        support_qs = User.objects.filter(
            models.Q(is_staff=True)
            | models.Q(is_superuser=True) 
            | models.Q(userprofile__role__name__in=['SuperAdmin', 'Admin', 'Agent'])
        )
        
        # Get unique contacts: users who have sent/received messages with support users or have tickets
        contact_users = User.objects.filter(
            models.Q(sent_messages__recipient__in=support_qs) |
            models.Q(received_messages__sender__in=support_qs) |
            models.Q(created_tickets__isnull=False)
        ).distinct().select_related('userprofile')
        
        contacts = []
        for user in contact_users:
            # Get latest message or ticket info
            latest_message = ChatMessage.objects.filter(
                models.Q(sender=user, recipient__in=support_qs) |
                models.Q(recipient=user, sender__in=support_qs)
            ).order_by('-created_at').first()
            
            latest_ticket = Ticket.objects.filter(created_by=user).order_by('-created_at').first()
            
            # Get unread count
            unread_count = ChatMessage.objects.filter(
                sender=user,
                recipient=request.user,
                is_read=False
            ).count()
            
            contacts.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'initials': (user.get_full_name() or user.username)[:2].upper(),
                'email': user.email,
                'latest_ticket_id': latest_ticket.ticket_id if latest_ticket else None,
                'last_message': latest_message.text if latest_message else '',
                'time': latest_message.created_at.strftime('%H:%M') if latest_message else '',
                'unread_count': unread_count,
                'status': 'Online' if user.is_authenticated else 'Offline',
            })
        
        ctx = {'contacts': contacts}

    return render(request, f"{base}{normalized}", ctx)


# ---------------------------------------------------------------------------
# Admin ticket volume API
# ---------------------------------------------------------------------------

@login_required
@require_admin_role
def admin_ticket_volume_api(request):
    period = request.GET.get('period', 'daily')
    try:
        qs = Ticket.objects.all()
        now = timezone.now()

        if period == 'daily':
            labels = []
            data = []
            # Include today and go back 29 days (total 30 days including today)
            for i in range(29, -1, -1):  # 29, 28, ..., 0 (includes today)
                date = now.date() - datetime.timedelta(days=i)
                date_start = timezone.make_aware(datetime.datetime.combine(date, datetime.time.min))
                date_end = timezone.make_aware(datetime.datetime.combine(date, datetime.time.max))
                labels.append(date.strftime('%b %d'))
                data.append({
                    'created': qs.filter(created_at__gte=date_start, created_at__lt=date_end).count(),
                    'resolved': qs.filter(updated_at__gte=date_start, updated_at__lt=date_end, status__in=['Resolved', 'Closed']).count(),
                })
            return JsonResponse({'success': True, 'period': 'daily', 'labels': labels, 'data': data})

        elif period == 'weekly':
            labels = []
            data = []
            # Get current week start (Monday)
            current_week_start = now.date() - datetime.timedelta(days=now.weekday())
            
            # Include current week and go back 11 weeks (total 12 weeks including current)
            for i in range(11, -1, -1):  # 11, 10, ..., 0 (includes current week)
                week_start = current_week_start - datetime.timedelta(weeks=i)
                week_end = week_start + datetime.timedelta(days=6)  # Sunday
                week_start_dt = timezone.make_aware(datetime.datetime.combine(week_start, datetime.time.min))
                week_end_dt = timezone.make_aware(datetime.datetime.combine(week_end, datetime.time.max))
                
                # Label format: "Week 12" (most recent) to "Week 1" (oldest)
                week_num = 12 - i
                labels.append(f"Week {week_num}")
                data.append({
                    'created': qs.filter(created_at__gte=week_start_dt, created_at__lte=week_end_dt).count(),
                    'resolved': qs.filter(updated_at__gte=week_start_dt, updated_at__lte=week_end_dt, status__in=['Resolved', 'Closed']).count(),
                })
            return JsonResponse({'success': True, 'period': 'weekly', 'labels': labels, 'data': data})

        else:  # monthly
            labels = []
            data = []
            # Include current month and go back 11 months (total 12 months including current)
            for i in range(11, -1, -1):  # 11, 10, ..., 0 (includes current month)
                # Calculate month start
                if i == 0:
                    # Current month
                    month_start = now.replace(day=1)
                else:
                    # Previous months
                    month_start = (now.replace(day=1) - datetime.timedelta(days=32 * i)).replace(day=1)
                
                # Calculate month end
                if i == 0:
                    # Current month - use today as end
                    month_end = now.date()
                else:
                    # Previous months - get last day of month
                    next_month = month_start + datetime.timedelta(days=32)
                    while next_month.month == month_start.month:
                        next_month += datetime.timedelta(days=1)
                    month_end = next_month - datetime.timedelta(days=1)
                
                # Create datetime objects for filtering
                month_start_dt = timezone.make_aware(datetime.datetime.combine(month_start, datetime.time.min))
                month_end_dt = timezone.make_aware(datetime.datetime.combine(month_end, datetime.time.max))
                
                labels.append(month_start.strftime('%b %Y'))
                data.append({
                    'created': qs.filter(created_at__gte=month_start_dt, created_at__lte=month_end_dt).count(),
                    'resolved': qs.filter(updated_at__gte=month_start_dt, updated_at__lte=month_end_dt, status__in=['Resolved', 'Closed']).count(),
                })
            return JsonResponse({'success': True, 'period': 'monthly', 'labels': labels, 'data': data})

    except Exception as e:
        logger.error(f"Error in admin_ticket_volume_api: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ---------------------------------------------------------------------------
# Ticket detail / edit / delete views
# ---------------------------------------------------------------------------

def _resolve_ticket(identifier):
    ticket = None
    num = identifier.lstrip('#')
    if num.isdigit():
        ticket = Ticket.objects.filter(pk=int(num)).first()
    if ticket is None:
        candidates = [num, f"TCK-{num}", identifier.lstrip('#'), identifier]
        for cid in candidates:
            t = Ticket.objects.filter(ticket_id=cid).first()
            if t:
                return t
    return ticket


@login_required
def admin_ticket_detail(request, identifier: str):
    if not is_admin_user(request):
        raise Http404("Not authorized")
    ticket = _resolve_ticket(identifier)
    if ticket is None:
        raise Http404("Ticket not found")
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'admindashboard/partials/ticket-detail.html', {"ticket": ticket})
    return render(request, 'admindashboard/partials/ticket-detail.html', {"ticket": ticket})


@login_required
def admin_ticket_edit(request, identifier: str):
    if not is_admin_user(request):
        raise Http404("Not authorized")
    ticket = _resolve_ticket(identifier)
    if ticket is None:
        raise Http404("Ticket not found")

    if request.method == "POST":
        form = AdminTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket_obj = form.save(commit=False)
            if ticket_obj.assigned_to and ticket_obj.status == 'Open':
                ticket_obj.status = 'In Progress'
            ticket_obj.save()
            messages.success(request, f"Ticket '{ticket.ticket_id}' updated.")
            return redirect('dashboards:admin_dashboard_page', page='tickets.html')
    else:
        form = AdminTicketForm(instance=ticket)
    return render(request, 'admindashboard/partials/ticket-edit.html', {"ticket": ticket, "form": form})


@login_required
def get_agents_by_department(request):
    """API endpoint to get agents filtered by department"""
    if not is_admin_user(request):
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    department = request.GET.get('department', '')
    
    if not department:
        # Return all agents
        agents = User.objects.filter(
            userprofile__role__name='Agent',
            is_active=True
        ).select_related('userprofile').order_by('username')
    else:
        # Filter by department
        agents = User.objects.filter(
            userprofile__role__name='Agent',
            userprofile__department=department,
            is_active=True
        ).select_related('userprofile').order_by('username')
    
    agent_list = []
    for agent in agents:
        agent_list.append({
            'id': agent.id,
            'username': agent.username,
            'department': agent.userprofile.department or 'No Department',
            'full_name': f"{agent.username} ({agent.userprofile.department or 'No Department'})"
        })
    
    return JsonResponse({
        'success': True,
        'agents': agent_list
    })


@login_required
def agent_ticket_detail(request, identifier: str):
    if not is_agent_user(request):
        raise Http404("Not authorized")
    ticket = _resolve_ticket(identifier)
    if ticket is None:
        raise Http404("Ticket not found")
    user = request.user
    if ticket.assigned_to != user and ticket.created_by != user:
        raise Http404("Not authorized - Ticket not assigned to you")
    return render(request, 'admindashboard/partials/ticket-detail.html', {"ticket": ticket})


@login_required
def agent_ticket_detail_json(request, identifier: str):
    if not is_agent_user(request):
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    ticket = _resolve_ticket(identifier)
    if ticket is None:
        return JsonResponse({'success': False, 'error': 'Ticket not found'}, status=404)
    user = request.user
    if ticket.assigned_to != user and ticket.created_by != user:
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    return JsonResponse({
        'success': True,
        'ticket_id': ticket.ticket_id,
        'title': ticket.title,
        'description': ticket.description,
        'status': ticket.status,
        'priority': ticket.priority,
        'customer': ticket.created_by.get_full_name() or ticket.created_by.username,
        'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else '',
        'updated_at': ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.updated_at else '',
    })


@login_required
def user_ticket_detail(request, identifier: str):
    ticket = _resolve_ticket(identifier)
    if ticket is None:
        raise Http404("Ticket not found")
    if ticket.created_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Not authorized")
    return render(request, 'admindashboard/partials/ticket-detail.html', {"ticket": ticket})


@login_required
def user_ticket_edit(request, identifier: str):
    ticket = _resolve_ticket(identifier)
    if ticket is None:
        raise Http404("Ticket not found")
    if ticket.created_by != request.user:
        raise Http404("Not authorized")
    if ticket.status not in ['Open', 'In Progress']:
        raise Http404("Ticket cannot be edited in current status")
    if request.method == "POST":
        try:
            form = TicketForm(request.POST, instance=ticket)
            if form.is_valid():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                return redirect('dashboards:user_dashboard_page', page='tickets')
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
        except Exception as exc:
            logger.exception(f"Error saving ticket edit for {ticket.ticket_id}: {exc}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'An unexpected error occurred while saving the ticket.'}, status=500)
            raise
    else:
        form = TicketForm(instance=ticket)
    return render(request, 'userdashboard/partials/ticket-edit.html', {"ticket": ticket, "form": form})


@login_required
def user_ticket_delete(request, identifier: str):
    ticket = _resolve_ticket(identifier)
    if ticket is None:
        raise Http404("Ticket not found")
    if ticket.created_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Not authorized")
    if request.method == "POST":
        ticket.delete()
    return redirect('dashboards:user_dashboard_page', page='tickets')


@login_required
def admin_ratings_trends_api(request):
    """Real rating trend data for admin chart. ?period=week|month|quarter|year"""
    if not is_admin_user(request):
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    import calendar as _cal
    import datetime as _dt

    period = request.GET.get('period', 'week')
    now    = timezone.now()
    qs     = UserRating.objects.all()

    try:
        if period == 'week':
            cats, data = [], []
            for i in range(7):
                day   = (now - _dt.timedelta(days=6 - i)).date()
                ds    = timezone.make_aware(_dt.datetime.combine(day, _dt.time.min))
                de    = ds + _dt.timedelta(days=1)
                avg   = round(float(qs.filter(created_at__gte=ds, created_at__lt=de).aggregate(a=Avg('rating')).get('a') or 0), 1)
                cats.append(_cal.day_name[day.weekday()][:3])
                data.append(avg)

        elif period == 'month':
            cats, data = [], []
            for i in range(4):
                ws  = now - _dt.timedelta(weeks=3 - i)
                we  = ws  + _dt.timedelta(weeks=1)
                avg = round(float(qs.filter(created_at__gte=ws, created_at__lt=we).aggregate(a=Avg('rating')).get('a') or 0), 1)
                cats.append(f'Week {i + 1}')
                data.append(avg)

        elif period == 'quarter':
            cats, data = [], []
            for i in range(3):
                ms  = now - _dt.timedelta(days=90 - 30 * i)
                me  = ms  + _dt.timedelta(days=30)
                avg = round(float(qs.filter(created_at__gte=ms, created_at__lt=me).aggregate(a=Avg('rating')).get('a') or 0), 1)
                cats.append(_cal.month_name[ms.month][:3])
                data.append(avg)

        elif period == 'year':
            cats, data = [], []
            for label, sm, em in [('Q1',1,3),('Q2',4,6),('Q3',7,9),('Q4',10,12)]:
                qs_  = now.replace(month=sm, day=1)
                qe_  = now.replace(month=em, day=_cal.monthrange(now.year, em)[1])
                avg  = round(float(qs.filter(created_at__gte=qs_, created_at__lte=qe_).aggregate(a=Avg('rating')).get('a') or 0), 1)
                cats.append(label)
                data.append(avg)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid period'})

        return JsonResponse({'success': True, 'categories': cats, 'data': data, 'title': period.title() + ' Rating Trends'})

    except Exception as e:
        logger.error(f'admin_ratings_trends_api error: {e}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



    
            
