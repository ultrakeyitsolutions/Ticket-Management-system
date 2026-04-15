"""
Complete Plan Management Controllers for SuperAdmin
Includes all CRUD operations, validation, and business logic
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta
import json

from .models import Plan, Company, Subscription, Payment, SubscriptionMetrics
from users.models import UserProfile


def is_admin_or_superadmin(user):
    """Check if user is admin or superadmin"""
    if not user.is_authenticated:
        return False
    try:
        profile = user.userprofile
        return profile.role in ['admin', 'superadmin']
    except:
        return user.is_superuser


@login_required(login_url='superadmin:superadmin_login')
def plan_list(request):
    """Display all plans with usage statistics and status"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    plans = Plan.objects.all().order_by('price')
    
    # Enhanced usage statistics for each plan
    plans_with_status = []
    for plan in plans:
        companies_count = Company.objects.filter(plan=plan).count()
        subscriptions_count = Subscription.objects.filter(plan=plan).count()
        active_subscriptions = Subscription.objects.filter(plan=plan, status='active').count()
        trial_subscriptions = Subscription.objects.filter(plan=plan, status='trial').count()
        
        # Calculate revenue for this plan
        total_revenue = Payment.objects.filter(subscription__plan=plan).aggregate(
            total=models.Sum('amount'))['total'] or 0
        
        # Get recent subscriptions (last 30 days)
        recent_subscriptions = Subscription.objects.filter(
            plan=plan, 
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        plans_with_status.append({
            'plan': plan,
            'companies_count': companies_count,
            'subscriptions_count': subscriptions_count,
            'active_subscriptions': active_subscriptions,
            'trial_subscriptions': trial_subscriptions,
            'total_revenue': total_revenue,
            'recent_subscriptions': recent_subscriptions,
            'is_in_use': companies_count > 0 or subscriptions_count > 0,
            'can_delete': companies_count == 0 and subscriptions_count == 0,
            'can_deactivate': companies_count > 0 or subscriptions_count > 0
        })
    
    # Get overall statistics
    total_plans = Plan.objects.count()
    active_plans = Plan.objects.filter(is_active=True).count()
    total_subscriptions = Subscription.objects.count()
    total_revenue = Payment.objects.aggregate(total=models.Sum('amount'))['total'] or 0
    
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    return render(request, 'superadmin/plans.html', {
        "plans_with_status": plans_with_status,
        "total_plans": total_plans,
        "active_plans": active_plans,
        "total_subscriptions": total_subscriptions,
        "total_revenue": total_revenue,
        "sa_page": "plans",
        "user_profile": profile
    })


@login_required(login_url='superadmin:superadmin_login')
def plan_create(request):
    """Create a new subscription plan"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract and validate form data
                name = request.POST.get('name', '').strip()
                price = request.POST.get('price', '').strip()
                billing_cycle = request.POST.get('billing_cycle', 'monthly')
                users = request.POST.get('users', '5')
                storage = request.POST.get('storage', '10GB')
                description = request.POST.get('description', '').strip()
                
                # Validate required fields
                if not name:
                    messages.error(request, 'Plan name is required.')
                    return render(request, 'superadmin/plan_create.html')
                
                if not price:
                    messages.error(request, 'Plan price is required.')
                    return render(request, 'superadmin/plan_create.html')
                
                # Validate price format
                try:
                    price = float(price)
                    if price < 0:
                        messages.error(request, 'Price cannot be negative.')
                        return render(request, 'superadmin/plan_create.html')
                except ValueError:
                    messages.error(request, 'Invalid price format.')
                    return render(request, 'superadmin/plan_create.html')
                
                # Validate users
                try:
                    users = int(users)
                    if users < 1:
                        messages.error(request, 'Number of users must be at least 1.')
                        return render(request, 'superadmin/plan_create.html')
                except ValueError:
                    messages.error(request, 'Invalid number of users.')
                    return render(request, 'superadmin/plan_create.html')
                
                # Check if plan name already exists
                if Plan.objects.filter(name__iexact=name).exists():
                    messages.error(request, f'Plan "{name}" already exists.')
                    return render(request, 'superadmin/plan_create.html')
                
                # Create the plan
                plan = Plan.objects.create(
                    name=name,
                    price=price,
                    billing_cycle=billing_cycle,
                    users=users,
                    storage=storage,
                    status='active',
                    is_active=True
                )
                
                # Create subscription metrics record
                SubscriptionMetrics.objects.create(
                    plan=plan,
                    date=timezone.now().date(),
                    new_subscriptions=0,
                    active_subscriptions=0,
                    revenue=0
                )
                
                messages.success(request, f'Plan "{name}" created successfully!')
                return redirect('superadmin:plans_list')
                
        except Exception as e:
            messages.error(request, f'Error creating plan: {str(e)}')
    
    return render(request, 'superadmin/plan_create.html', {
        'sa_page': 'plans',
        'billing_cycles': Plan.BILLING_CHOICES
    })


@login_required(login_url='superadmin:superadmin_login')
def plan_edit(request, plan_id):
    """Edit an existing subscription plan"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    plan = get_object_or_404(Plan, id=plan_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Extract and validate form data
                name = request.POST.get('name', '').strip()
                price = request.POST.get('price', '').strip()
                billing_cycle = request.POST.get('billing_cycle', 'monthly')
                users = request.POST.get('users', '5')
                storage = request.POST.get('storage', '10GB')
                description = request.POST.get('description', '').strip()
                
                # Validate required fields
                if not name:
                    messages.error(request, 'Plan name is required.')
                    return render(request, 'superadmin/plan_edit.html', {'plan': plan})
                
                if not price:
                    messages.error(request, 'Plan price is required.')
                    return render(request, 'superadmin/plan_edit.html', {'plan': plan})
                
                # Validate price format
                try:
                    price = float(price)
                    if price < 0:
                        messages.error(request, 'Price cannot be negative.')
                        return render(request, 'superadmin/plan_edit.html', {'plan': plan})
                except ValueError:
                    messages.error(request, 'Invalid price format.')
                    return render(request, 'superadmin/plan_edit.html', {'plan': plan})
                
                # Validate users
                try:
                    users = int(users)
                    if users < 1:
                        messages.error(request, 'Number of users must be at least 1.')
                        return render(request, 'superadmin/plan_edit.html', {'plan': plan})
                except ValueError:
                    messages.error(request, 'Invalid number of users.')
                    return render(request, 'superadmin/plan_edit.html', {'plan': plan})
                
                # Check if plan name conflicts with existing plan (excluding current)
                if Plan.objects.filter(name__iexact=name).exclude(id=plan_id).exists():
                    messages.error(request, f'Plan "{name}" already exists.')
                    return render(request, 'superadmin/plan_edit.html', {'plan': plan})
                
                # Track old values for audit
                old_name = plan.name
                old_price = plan.price
                
                # Update the plan
                plan.name = name
                plan.price = price
                plan.billing_cycle = billing_cycle
                plan.users = users
                plan.storage = storage
                plan.save()
                
                # Log the change (you could implement proper audit logging here)
                if old_name != name or old_price != price:
                    messages.info(request, f'Plan updated: {old_name} -> {name}')
                
                messages.success(request, f'Plan "{name}" updated successfully!')
                return redirect('superadmin:plans_list')
                
        except Exception as e:
            messages.error(request, f'Error updating plan: {str(e)}')
    
    context = {
        'plan': plan,
        'sa_page': 'plans',
        'billing_cycles': Plan.BILLING_CHOICES
    }
    return render(request, 'superadmin/plan_edit.html', context)


@login_required(login_url='superadmin:superadmin_login')
def plan_delete(request, plan_id):
    """Delete a plan (only if not in use)"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                plan = get_object_or_404(Plan, id=plan_id)
                
                # Check if plan is in use
                companies_count = Company.objects.filter(plan=plan).count()
                subscriptions_count = Subscription.objects.filter(plan=plan).count()
                
                if companies_count > 0 or subscriptions_count > 0:
                    messages.error(request, f'Cannot delete plan "{plan.name}" as it is in use by {companies_count} companies and {subscriptions_count} subscriptions.')
                    return redirect('superadmin:plans_list')
                
                # Delete related metrics
                SubscriptionMetrics.objects.filter(plan=plan).delete()
                
                # Delete the plan
                plan_name = plan.name
                plan.delete()
                
                messages.success(request, f'Plan "{plan_name}" deleted successfully!')
                return redirect('superadmin:plans_list')
                
        except Plan.DoesNotExist:
            messages.error(request, 'Plan not found.')
        except Exception as e:
            messages.error(request, f'Error deleting plan: {str(e)}')
    
    return redirect('superadmin:plans_list')


@login_required(login_url='superadmin:superadmin_login')
def plan_deactivate(request, plan_id):
    """Deactivate a plan (prevent new signups but keep existing subscriptions)"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                plan = get_object_or_404(Plan, id=plan_id)
                
                # Deactivate the plan
                plan.is_active = False
                plan.status = 'inactive'
                plan.save()
                
                # Cancel any pending trial subscriptions for this plan
                Subscription.objects.filter(
                    plan=plan, 
                    status='trial'
                ).update(status='cancelled')
                
                messages.success(request, f'Plan "{plan.name}" has been deactivated. Existing subscriptions will continue to work, but new users cannot sign up for this plan.')
                return redirect('superadmin:plans_list')
                
        except Plan.DoesNotExist:
            messages.error(request, 'Plan not found.')
        except Exception as e:
            messages.error(request, f'Error deactivating plan: {str(e)}')
    
    return redirect('superadmin:plans_list')


@login_required(login_url='superadmin:superadmin_login')
def plan_activate(request, plan_id):
    """Activate a previously deactivated plan"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                plan = get_object_or_404(Plan, id=plan_id)
                
                # Activate the plan
                plan.is_active = True
                plan.status = 'active'
                plan.save()
                
                messages.success(request, f'Plan "{plan.name}" has been activated and is now available for new signups.')
                return redirect('superadmin:plans_list')
                
        except Plan.DoesNotExist:
            messages.error(request, 'Plan not found.')
        except Exception as e:
            messages.error(request, f'Error activating plan: {str(e)}')
    
    return redirect('superadmin:plans_list')


@login_required(login_url='superadmin:superadmin_login')
def plan_subscriptions(request, plan_id):
    """View all subscriptions for a specific plan"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    plan = get_object_or_404(Plan, id=plan_id)
    subscriptions = Subscription.objects.filter(plan=plan).select_related('company').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(subscriptions, 20)
    page = request.GET.get('page')
    
    try:
        subscriptions = paginator.page(page)
    except PageNotAnInteger:
        subscriptions = paginator.page(1)
    except EmptyPage:
        subscriptions = paginator.page(paginator.num_pages)
    
    # Calculate statistics
    total_subscriptions = Subscription.objects.filter(plan=plan).count()
    active_subscriptions = Subscription.objects.filter(plan=plan, status='active').count()
    trial_subscriptions = Subscription.objects.filter(plan=plan, status='trial').count()
    expired_subscriptions = Subscription.objects.filter(plan=plan, status='expired').count()
    
    context = {
        'plan': plan,
        'subscriptions': subscriptions,
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'trial_subscriptions': trial_subscriptions,
        'expired_subscriptions': expired_subscriptions,
        'sa_page': 'plans'
    }
    
    return render(request, 'superadmin/plan_subscriptions.html', context)


@login_required(login_url='superadmin:superadmin_login')
def plan_analytics(request, plan_id):
    """View analytics and metrics for a specific plan"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    plan = get_object_or_404(Plan, id=plan_id)
    
    # Get subscription metrics for the last 30 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    metrics = SubscriptionMetrics.objects.filter(
        plan=plan,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('date')
    
    # Calculate totals
    total_revenue = Payment.objects.filter(subscription__plan=plan).aggregate(
        total=models.Sum('amount'))['total'] or 0
    
    total_subscriptions = Subscription.objects.filter(plan=plan).count()
    active_subscriptions = Subscription.objects.filter(plan=plan, status='active').count()
    
    # Monthly growth
    current_month_subscriptions = Subscription.objects.filter(
        plan=plan,
        created_at__gte=timezone.now().replace(day=1)
    ).count()
    
    last_month_subscriptions = Subscription.objects.filter(
        plan=plan,
        created_at__gte=(timezone.now().replace(day=1) - timedelta(days=30)),
        created_at__lt=timezone.now().replace(day=1)
    ).count()
    
    growth_rate = 0
    if last_month_subscriptions > 0:
        growth_rate = ((current_month_subscriptions - last_month_subscriptions) / last_month_subscriptions) * 100
    
    context = {
        'plan': plan,
        'metrics': metrics,
        'total_revenue': total_revenue,
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'current_month_subscriptions': current_month_subscriptions,
        'last_month_subscriptions': last_month_subscriptions,
        'growth_rate': growth_rate,
        'sa_page': 'plans'
    }
    
    return render(request, 'superadmin/plan_analytics.html', context)


@login_required(login_url='superadmin:superadmin_login')
def plan_duplicate(request, plan_id):
    """Duplicate an existing plan"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                original_plan = get_object_or_404(Plan, id=plan_id)
                
                # Create a copy
                new_name = request.POST.get('name', f"{original_plan.name} (Copy)")
                
                # Check if name already exists
                counter = 1
                base_name = new_name
                while Plan.objects.filter(name=new_name).exists():
                    counter += 1
                    new_name = f"{base_name} {counter}"
                
                new_plan = Plan.objects.create(
                    name=new_name,
                    price=original_plan.price,
                    billing_cycle=original_plan.billing_cycle,
                    users=original_plan.users,
                    storage=original_plan.storage,
                    status='active',
                    is_active=True
                )
                
                # Create metrics for the new plan
                SubscriptionMetrics.objects.create(
                    plan=new_plan,
                    date=timezone.now().date(),
                    new_subscriptions=0,
                    active_subscriptions=0,
                    revenue=0
                )
                
                messages.success(request, f'Plan "{new_name}" created successfully as a copy of "{original_plan.name}"!')
                return redirect('superadmin:plans_list')
                
        except Exception as e:
            messages.error(request, f'Error duplicating plan: {str(e)}')
    
    return redirect('superadmin:plans_list')


# API endpoints for AJAX requests
@login_required(login_url='superadmin:superadmin_login')
def plan_toggle_status(request, plan_id):
    """Toggle plan active/inactive status via AJAX"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        try:
            plan = get_object_or_404(Plan, id=plan_id)
            
            if plan.is_active:
                # Deactivate
                plan.is_active = False
                plan.status = 'inactive'
                message = f'Plan "{plan.name}" deactivated'
            else:
                # Activate
                plan.is_active = True
                plan.status = 'active'
                message = f'Plan "{plan.name}" activated'
            
            plan.save()
            
            return JsonResponse({
                'success': True,
                'message': message,
                'is_active': plan.is_active
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required(login_url='superadmin:superadmin_login')
def plan_stats_api(request, plan_id):
    """Get plan statistics as JSON for charts"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        plan = get_object_or_404(Plan, id=plan_id)
        
        # Get daily subscription counts for last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        subscription_data = []
        for i in range(30):
            date = start_date + timedelta(days=i)
            count = Subscription.objects.filter(
                plan=plan,
                created_at__date=date
            ).count()
            subscription_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        # Get revenue data
        revenue_data = []
        for i in range(30):
            date = start_date + timedelta(days=i)
            revenue = Payment.objects.filter(
                subscription__plan=plan,
                payment_date__date=date
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            revenue_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'revenue': float(revenue)
            })
        
        return JsonResponse({
            'success': True,
            'subscription_data': subscription_data,
            'revenue_data': revenue_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
