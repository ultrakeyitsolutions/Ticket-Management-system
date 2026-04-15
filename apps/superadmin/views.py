from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from users.models import UserProfile, Role



from django.contrib.auth.decorators import login_required



from django.views.decorators.http import require_POST



from django.views.decorators.csrf import csrf_exempt



from django.contrib.auth.models import User
from django.db import IntegrityError

from django.contrib import messages



from django.db import models
from django.db.models import Q



from django.http import JsonResponse



from django.utils.decorators import method_decorator



from django.views import View



from datetime import datetime



from users.models import Role, UserProfile



from django.utils import timezone



from .models import Company, SuperAdminSettings, NotificationTemplate, Subscription, Payment, SubscriptionMetrics, Notification
from django.apps import apps
Plan = apps.get_model('superadmin', 'Plan')



from tickets.models import TicketComment, Ticket











# Helper functions for subscription expiry checking



def check_subscription_expiry(user):
    """Check if user's subscription has expired or is inactive"""
    try:
        from django.utils import timezone
        from users.models import UserProfile
        
        # Get user's company using the same logic as should_show_payment_modal
        profile = getattr(user, 'userprofile', None)
        user_company = None
        
        if profile:
            from superadmin.models import Company
            user_company = Company.objects.filter(users=profile).first()
        
        if not user_company:
            return True  # No company found, show payment modal
        
        # Get most recent subscription for this company
        subscription = user_company.subscriptions.order_by('-created_at').first()
        
        if subscription:
            # If subscription is active or trial, check if it's expired
            if subscription.status in ['active', 'trial']:
                if subscription.end_date and subscription.end_date < timezone.now().date():
                    return True  # Subscription expired
                return False  # Active/Trial subscription not expired
            # If subscription is expired, cancelled, or suspended, show payment modal
            elif subscription.status in ['expired', 'cancelled', 'suspended']:
                return True  # Inactive subscription
            else:
                return False  # Unknown status, don't show modal
        else:
            # No subscription found - show payment modal
            return True
        
    except Exception as e:
        print(f"ERROR: Error checking subscription expiry: {e}")
        import traceback
        traceback.print_exc()
        return False







def should_show_payment_modal(user):
    """
    Comprehensive check to determine if payment modal should be shown
    
    UPDATED: Show payment modal for ADMIN users when subscription is expired/expiring
    UPDATED: Show payment modal for NEW regular users who don't have subscriptions
    UPDATED: Check core subscriptions to avoid showing modal during valid trials
    """
    try:
        # Check user role to determine modal behavior
        from users.models import UserProfile
        user_role = None
        if hasattr(user, 'userprofile') and getattr(user.userprofile, 'role', None):
            user_role = getattr(user.userprofile.role, 'name', '').lower()
        
        # LOGIC: Show payment modal for:
        # 1. Admin users with expired subscriptions
        # 2. Regular users without any subscription (new users)
        # 3. BUT NOT if user has valid core trial subscription
        
        is_admin_or_staff = user.is_staff or user.is_superuser
        is_regular_user = user_role in ['user', 'customer']
        
        # Skip for agents - they shouldn't see payment modal
        if user_role == 'agent':
            return False
        
        # FIRST: Check if user has valid core subscription (our new trial system)
        from core.models import Subscription as CoreSubscription
        try:
            core_subscription = CoreSubscription.objects.filter(user=user).first()
            if core_subscription and core_subscription.is_active():
                # User has valid core subscription (trial or paid), don't show modal
                return False
        except Exception as e:
            print(f"Error checking core subscription: {e}")
        
        # SECOND: Check superadmin subscription system (legacy)
        # Check if user has active subscription or recent completed payment
        from superadmin.models import Payment, Subscription
        
        # Get user's company and check for active subscription
        try:
            profile = getattr(user, 'userprofile', None)
            
            # Find user's company
            user_company = None
            if profile:
                from superadmin.models import Company
                user_company = Company.objects.filter(users=profile).first()
            
            # Check if user has an active subscription OR trial
            has_active_subscription = False
            has_expired_trial = False
            
            if user_company:
                # Check for active subscription
                active_subscription = Subscription.objects.filter(
                    company=user_company,
                    status='active'
                ).first()
                
                if active_subscription:
                    has_active_subscription = True
                
                # Check for active trial subscription
                trial_subscription = Subscription.objects.filter(
                    company=user_company,
                    status='trial'
                ).first()
                
                if trial_subscription:
                    # Check if trial is still valid using trial_end_date (not end_date)
                    from django.utils import timezone
                    if trial_subscription.trial_end_date and trial_subscription.trial_end_date > timezone.now():
                        has_active_subscription = True  # Trial is active, treat as active
                    else:
                        has_expired_trial = True  # Trial has expired
                
                # Check if user has recent completed payment (within last 30 days)
                recent_payment = Payment.objects.filter(
                    company=user_company,
                    status='completed'
                ).order_by('-created_at').first()
                
                if recent_payment:
                    # Check if payment is within subscription period
                    from django.utils import timezone
                    days_since_payment = (timezone.now().date() - recent_payment.created_at.date()).days
                    if days_since_payment <= 30:  # Grace period of 30 days
                        has_active_subscription = True
                        
        except Exception as e:
            print(f"Error checking user subscription: {e}")
            # Continue to other checks if there's an error

        # DECISION LOGIC:
        # 1. User has active core subscription: Don't show modal (checked above)
        # 2. User has active superadmin subscription (including active trial): Show modal for upgrade option
        # 3. User has expired trial: Show modal
        # 4. Admin/Regular users without any subscription: Show modal
        
        # NEW: Show modal for trial users so they can upgrade during active trial
        if has_active_subscription and not has_expired_trial:
            # User has active subscription or trial - show modal for upgrade option
            return True  # Allow trial users to see upgrade option
        
        # Show modal if trial has expired OR user has no subscription
        if has_expired_trial or (is_admin_or_staff or is_regular_user):
            return True
            
        return False  # Default: don't show modal
        
    except Exception as e:
        print(f"ERROR: Error in should_show_payment_modal: {e}")
        import traceback
        traceback.print_exc()
        return False







def is_admin_or_superadmin(user):
    """Check if user is Admin or SuperAdmin"""
    try:
        if not user or not user.is_authenticated:
            return False
        
        # Check if user is SuperAdmin (Django superuser)
        if user.is_superuser:
            return True
        
        # Check if user is Admin (Django staff)
        if user.is_staff:
            return True
        
        # Check if user has Admin or SuperAdmin role (fallback)
        try:
            profile = user.userprofile
            if profile and profile.role:
                return profile.role.name in ['Admin', 'SuperAdmin']
        except:
            pass
        
        return False



    except:



        return False







def _is_superadmin_user(user):



    if not user or not user.is_authenticated:



        return False







    if user.is_superuser:



        return True







    try:



        profile = UserProfile.objects.get(user=user)



        return profile.role and profile.role.name.lower() == 'superadmin'



    except UserProfile.DoesNotExist:



        return False







def get_role_based_redirect(user):



    """Get appropriate redirect URL based on user role"""



    if _is_superadmin_user(user):



        return 'superadmin:superadmin_dashboard'



    elif is_admin_or_superadmin(user):



        return 'dashboards:admin_dashboard'



    else:



        return 'superadmin:superadmin_login'











def get_user_plan_name(user):



    """Get user's current plan name"""



    try:



        companies = Company.objects.all()



        for company in companies:



            if company.name == f'{user.username} Company':



                subscription = company.subscriptions.filter(status='trial').first()



                if subscription and subscription.plan:



                    return subscription.plan.name



        return "Trial"



    except:



        return "Trial"











def get_expiry_date(user):



    """Get subscription expiry date"""



    try:



        companies = Company.objects.all()



        for company in companies:



            if company.name == f'{user.username} Company':



                subscription = company.subscriptions.filter(status='trial').first()



                if subscription:



                    return subscription.end_date.strftime('%B %d, %Y')



        return None



    except:



        return None











def get_days_expired(user):



    """Get days since expiry"""



    try:



        companies = Company.objects.all()



        for company in companies:



            if company.name == f'{user.username} Company':



                subscription = company.subscriptions.filter(status='trial').first()



                if subscription:



                    today = timezone.now().date()



                    if subscription.end_date < today:



                        return (today - subscription.end_date).days



        return 0



    except:



        return 0











# Notification management functions



def create_system_notification(title, message, priority='medium', user=None, expires_in_hours=24):



    """Create a system notification"""



    return Notification.create_notification(



        title=title,



        message=message,



        notification_type='system',



        priority=priority,



        user=user,



        expires_in_hours=expires_in_hours



    )











def create_payment_notification(title, message, priority='medium', user=None, action_url=None):



    """Create a payment-related notification"""



    return Notification.create_notification(



        title=title,



        message=message,



        notification_type='payment',



        priority=priority,



        user=user,



        action_url=action_url,



        action_text='View Payment',



        expires_in_hours=48



    )











def create_subscription_notification(title, message, priority='medium', user=None, action_url=None):



    """Create a subscription-related notification"""



    return Notification.create_notification(



        title=title,



        message=message,



        notification_type='subscription',



        priority=priority,



        user=user,



        action_url=action_url,



        action_text='View Subscription',



        expires_in_hours=72



    )











def create_user_management_notification(title, message, priority='medium', user=None, action_url=None):



    """Create a user management notification"""



    return Notification.create_notification(



        title=title,



        message=message,



        notification_type='user',



        priority=priority,



        user=user,



        action_url=action_url,



        action_text='View User',



        expires_in_hours=24



    )











def get_notifications_context(user):



    """Get notifications context for templates"""



    notifications = Notification.get_user_notifications(user)[:10]  # Latest 10



    unread_count = Notification.get_unread_count(user)



    



    return {



        'notifications': notifications,



        'unread_count': unread_count,



        'has_notifications': notifications.exists(),



    }











def check_and_create_system_notifications():



    """Check system conditions and create appropriate notifications"""



    try:



        # Check for expiring trials (next 7 days)



        from datetime import timedelta



        upcoming_expiry = timezone.now().date() + timedelta(days=7)



        



        expiring_trials = Subscription.objects.filter(



            status='trial',



            end_date__lte=upcoming_expiry,



            end_date__gte=timezone.now().date()



        )



        



        for subscription in expiring_trials:



            days_left = (subscription.end_date - timezone.now().date()).days



            if days_left <= 3:



                priority = 'urgent'



            elif days_left <= 7:



                priority = 'high'



            else:



                priority = 'medium'



                



            # Check if notification already exists for this subscription



            existing_notification = Notification.objects.filter(



                title__contains=f"Trial expiring for {subscription.company.name}",



                created_at__gte=timezone.now() - timedelta(hours=24)



            ).exists()



            



            if not existing_notification:



                create_subscription_notification(



                    title=f"Trial expiring for {subscription.company.name}",



                    message=f"The trial subscription for {subscription.company.name} will expire in {days_left} days.",



                    priority=priority,



                    action_url=f"/superadmin/companies/{subscription.company.id}/"



                )



        



        # Check for failed payments (last 24 hours)



        recent_failed_payments = Payment.objects.filter(



            status='failed',



            created_at__gte=timezone.now() - timedelta(hours=24)



        )



        



        for payment in recent_failed_payments:



            existing_notification = Notification.objects.filter(



                title__contains=f"Payment failed for {payment.company.name}",



                created_at__gte=timezone.now() - timedelta(hours=12)



            ).exists()



            



            if not existing_notification:



                create_payment_notification(



                    title=f"Payment failed for {payment.company.name}",



                    message=f"A payment of ${payment.amount} for {payment.company.name} has failed.",



                    priority='high',



                    action_url=f"/superadmin/transactions/"



                )



        



        # Check for new user registrations (last 24 hours)



        recent_users = User.objects.filter(



            date_joined__gte=timezone.now() - timedelta(hours=24),



            is_active=True



        )



        



        if recent_users.count() > 0:



            existing_notification = Notification.objects.filter(



                title__contains="New user registrations",



                created_at__gte=timezone.now() - timedelta(hours=12)



            ).exists()



            



            if not existing_notification:



                create_user_management_notification(



                    title="New user registrations",



                    message=f"{recent_users.count()} new users have registered in the last 24 hours.",



                    priority='low',



                    action_url="/superadmin/users/"



                )



    



    except Exception as e:



        print(f"Error creating system notifications: {e}")



@login_required(login_url='superadmin:superadmin_login')
def plan_add(request):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '').strip()
        setup_fee = request.POST.get('setup_fee', '').strip()
        max_tickets = request.POST.get('max_tickets', '').strip()
        max_projects = request.POST.get('max_projects', '').strip()
        storage_limit = request.POST.get('storage_limit', '').strip()
        bandwidth_limit = request.POST.get('bandwidth_limit', '').strip()
        is_active = request.POST.get('is_active') == 'true'
        
        # Get selected features
        features = request.POST.getlist('features')
        
        # Validate required fields
        if not name or not description or not price or not setup_fee or not max_tickets or not max_projects or not storage_limit or not bandwidth_limit:
            messages.error(request, 'All required fields must be filled.')
            return redirect('superadmin:plan_add')
        
        try:
            # Create the plan
            plan = Plan.objects.create(
                name=name,
                price=float(price),
                billing_cycle='monthly',  # Default to monthly
                tickets=int(max_tickets),
                storage=f"{storage_limit}GB",
                status='active' if is_active else 'inactive',
                is_active=is_active
            )
            
            messages.success(request, f'Plan "{name}" created successfully!')
            return redirect('superadmin:plans_list')
            
        except Exception as e:
            messages.error(request, f'Error creating plan: {str(e)}')
            return redirect('superadmin:plan_add')
    
    context = {
        'sa_page': 'plans'
    }
    return render(request, 'superadmin/plan_add.html', context)

@login_required(login_url='superadmin:superadmin_login')
def plan_delete(request, plan_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            plan = get_object_or_404(Plan, id=plan_id)
            
            # Check if plan is being used by any companies or subscriptions
            companies_using_plan = Company.objects.filter(plan=plan).count()
            subscriptions_using_plan = Subscription.objects.filter(plan=plan).count()
            
            if companies_using_plan > 0 or subscriptions_using_plan > 0:
                messages.error(request, f'Cannot delete plan "{plan.name}" because it is being used by {companies_using_plan} companies and {subscriptions_using_plan} subscriptions.')
                return redirect('superadmin:plans_list')
            
            plan_name = plan.name
            plan.delete()
            
            messages.success(request, f'Plan "{plan_name}" has been deleted successfully.')
            return redirect('superadmin:plans_list')
            
        except Plan.DoesNotExist:
            messages.error(request, 'Plan not found.')
            return redirect('superadmin:plans_list')
        except Exception as e:
            messages.error(request, f'Error deleting plan: {str(e)}')
            return redirect('superadmin:plans_list')
    
    # If not POST, redirect to plans list
    return redirect('superadmin:plans_list')

@login_required(login_url='superadmin:superadmin_login')
def plan_edit(request, plan_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    plan = get_object_or_404(Plan, id=plan_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        price = request.POST.get('price', '').strip()
        billing_cycle = request.POST.get('billing_cycle', 'monthly')
        tickets = request.POST.get('tickets', '5')
        storage = request.POST.get('storage', '10GB')
        features = request.POST.getlist('features', [])
        
        if not name or not price:
            messages.error(request, 'Plan name and price are required.')
        else:
            try:
                plan.name = name
                plan.price = price
                plan.billing_cycle = billing_cycle
                plan.tickets = int(tickets) if tickets != '999' else 999
                plan.storage = storage
                plan.features = features
                plan.save()
                messages.success(request, f'Plan "{name}" updated successfully!')
                return redirect('superadmin:plans_list')
            except Exception as e:
                messages.error(request, f'Error updating plan: {str(e)}')
    
    context = {
        'plan': plan,
        'sa_page': 'plans'
    }
    return render(request, 'superadmin/plan_edit.html', context)

@login_required(login_url='superadmin:superadmin_login')
def plan_deactivate(request, plan_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            plan = get_object_or_404(Plan, id=plan_id)
            
            # Deactivate the plan instead of deleting
            plan.is_active = False
            plan.status = 'inactive'
            plan.save()
            
            messages.success(request, f'Plan "{plan.name}" has been deactivated. Existing subscriptions will continue to work, but new users cannot sign up for this plan.')
            return redirect('superadmin:plans_list')
            
        except Plan.DoesNotExist:
            messages.error(request, 'Plan not found.')
            return redirect('superadmin:plans_list')
        except Exception as e:
            messages.error(request, f'Error deactivating plan: {str(e)}')
            return redirect('superadmin:plans_list')
    
    # If not POST, redirect to plans list
    return redirect('superadmin:plans_list')

@login_required(login_url='superadmin:superadmin_login')
def plan_activate(request, plan_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
        try:
            plan = get_object_or_404(Plan, id=plan_id)
            
            # Activate the plan
            plan.is_active = True
            plan.status = 'active'
            plan.save()
            
            messages.success(request, f'Plan "{plan.name}" has been activated and is now available for new subscriptions.')
            return redirect('superadmin:plans_list')
            
        except Plan.DoesNotExist:
            messages.error(request, 'Plan not found.')
            return redirect('superadmin:plans_list')
        except Exception as e:
            messages.error(request, f'Error activating plan: {str(e)}')
            return redirect('superadmin:plans_list')
    
    # If not POST, redirect to plans list
    return redirect('superadmin:plans_list')

@login_required(login_url='superadmin:superadmin_login')
def plan_list(request):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    plans = Plan.objects.all().order_by('price')
    
    # Check usage status for each plan
    plans_with_status = []
    for plan in plans:
        companies_count = Company.objects.filter(plan=plan).count()
        # Use UserSubscription instead of Subscription
        from subscriptions.models import UserSubscription
        subscriptions_count = UserSubscription.objects.filter(plan=plan).count()
        tickets_count = plan.ticket_set.count()
        
        # Calculate revenue from this plan
        revenue = 0
        if subscriptions_count > 0:
            from subscriptions.models import PaymentTransaction
            completed_payments = PaymentTransaction.objects.filter(
                plan=plan, 
                status='completed'
            )
            revenue = sum(payment.amount for payment in completed_payments)
        
        plans_with_status.append({
            'plan': plan,
            'companies_count': companies_count,
            'subscriptions_count': subscriptions_count,
            'tickets_count': tickets_count,
            'revenue': revenue,
            'is_in_use': companies_count > 0 or subscriptions_count > 0 or tickets_count > 0
        })
    
    # Add user profile to context for header display
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    return render(request, 'superadmin/plans.html', {
        "plans_with_status": plans_with_status, 
        "sa_page": "plans",
        "user_profile": profile
    })

@login_required(login_url='superadmin:superadmin_login')
def companies_list(request):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    companies = Company.objects.all().order_by('-created_at')
    
    # Pagination: 7 companies per page
    paginator = Paginator(companies, 7)
    page = request.GET.get('page')
    
    try:
        companies = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        companies = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        companies = paginator.page(paginator.num_pages)
    
    # Add user profile to context for header display
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    context = {
        'companies': companies,
        'sa_page': 'companies',
        'user_profile': profile,  # Add user profile for header display
        'plans': Plan.objects.all()  # Add all available plans for the dropdown
    }
    
    # Handle AJAX request for partial refresh
    if request.GET.get('ajax') == '1':
        return render(request, 'superadmin/companies_list_partial.html', context)
    
    return render(request, 'superadmin/companies.html', context)

@login_required(login_url='superadmin:superadmin_login')
def company_create(request):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # DEBUG: Track if this function is called multiple times
        import time
        timestamp = time.time()
        print(f"\n=== COMPANY CREATE CALLED at {timestamp} ===")
        print(f"Email: {request.POST.get('email', '')}")
        print(f"Is AJAX: {is_ajax}")
        print(f"User: {request.user.username}")

        # Collect form data
        name                = request.POST.get('name', '').strip()
        email               = request.POST.get('email', '').strip()
        phone               = request.POST.get('phone', '').strip()
        address             = request.POST.get('address', '').strip()
        password            = request.POST.get('password', '').strip()
        plan_id             = request.POST.get('plan', '')
        subscription_status = request.POST.get('subscription_status', '')

        def fail(msg):
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return redirect('superadmin:companies_list')

        # Validation
        if not name or not email or not password:
            return fail('Company name, email, and password are required.')

        if len(password) < 8:
            return fail('Password must be at least 8 characters long.')

        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return fail('Please enter a valid email address.')

        if phone and (not phone.isdigit() or len(phone) != 10):
            return fail('Phone number must be exactly 10 digits.')

        if Company.objects.filter(email=email).exists():
            return fail(f'A company with email "{email}" already exists.')

        valid_statuses = ['trial', 'active', 'expired', 'cancelled']
        if subscription_status not in valid_statuses:
            return fail('Please select a valid subscription status.')

        # Resolve plan
        selected_plan = None
        if plan_id:
            try:
                selected_plan = Plan.objects.get(id=plan_id)
            except Plan.DoesNotExist:
                return fail('Selected plan does not exist.')

        # Build a unique username that won't clash
        # Use a short random suffix so the auto-created User doesn't
        # trigger any "create company for <username>" signals with a
        # mangled name like "hello_gmail_com's Company".
        import uuid as _uuid
        base_username = email.lower().replace('@', '_at_').replace('.', '_')[:40]
        username = base_username
        counter  = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        try:
            # Create Django User
            parts = name.split()
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=parts[0] if parts else '',
                last_name=' '.join(parts[1:]) if len(parts) > 1 else '',
            )

            # Update / create UserProfile
            user_profile = getattr(user, 'userprofile', None)
            if user_profile:
                user_profile.phone   = phone
                user_profile.address = address
                user_profile.save()
            else:
                user_role    = Role.objects.get_or_create(name='User')[0]
                user_profile = UserProfile.objects.create(
                    user=user, role=user_role, phone=phone, address=address
                )

            # Create Company (this is the REAL company record)
            print(f"DEBUG: About to create company with email: {email}")
            company = Company.objects.create(
                name=name,
                email=email,
                phone=phone,
                address=address,
                password=make_password(password),
                subscription_status=subscription_status,
                plan=selected_plan,
                is_active=True,
            )
            print(f"DEBUG: Company created successfully with ID: {company.id}")
            company.users.add(user_profile)

            # Delete any auto-generated ghost company for this user
            # Some signals create "<username> Company" or "<username>@company.com"
            # ghost companies when a User is created. Remove them now.
            ghost_name  = f'{username} Company'
            ghost_email = f'{username}@company.com'
            Company.objects.filter(
                name=ghost_name,
                email=ghost_email,
            ).exclude(id=company.id).delete()

        except Exception as e:
            return fail(f'Error creating company: {str(e)}')

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f'Company "{name}" created successfully!',
                'company_id': company.id,
            })

        messages.success(request, f'Company "{name}" created successfully!')
        return redirect('superadmin:companies_list')

    # GET request
    return render(request, 'superadmin/company_add.html', {
        'sa_page': 'companies',
        'plans': Plan.objects.filter(is_active=True),
    })

@login_required(login_url='superadmin:superadmin_login')
def company_detail(request, company_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    company = get_object_or_404(Company, id=company_id)
    
    # Get company subscriptions
    subscriptions = company.subscriptions.select_related('plan').order_by('-created_at')
    
    # Get company users
    users = company.users.select_related('user', 'role').all()
    
    context = {
        'company': company,
        'subscriptions': subscriptions,
        'users': users,
        'currency_symbol': '₹',  # Add currency symbol
        'sa_page': 'companies'
    }
    
    return render(request, 'superadmin/company_detail.html', context)

@login_required(login_url='superadmin:superadmin_login')
def company_edit(request, company_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        plan_id = request.POST.get('plan', '')
        subscription_status = request.POST.get('subscription_status', 'trial')
        is_active = request.POST.get('is_active') == 'on'
        
        # Validate required fields
        if not name or not email:
            messages.error(request, 'Name and email are required.')
        elif not phone or not phone.isdigit() or len(phone) != 10:
            messages.error(request, 'Phone number must be exactly 10 digits.')
        else:
            # Update company
            company.name = name
            company.email = email
            company.phone = phone
            company.address = address
            company.subscription_status = subscription_status
            company.is_active = is_active
            
            # Update plan if provided
            if plan_id:
                try:
                    plan = Plan.objects.get(id=plan_id)
                    company.plan = plan
                except Plan.DoesNotExist:
                    pass
            
            company.save()
            messages.success(request, 'Company updated successfully.')
            return redirect('superadmin:companies_list')
    
    context = {
        'company': company,
        'plans': Plan.objects.filter(is_active=True),
        'sa_page': 'companies'
    }
    
    return render(request, 'superadmin/company_edit.html', context)

@login_required(login_url='superadmin:superadmin_login')
def company_delete(request, company_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        company_name = company.name
        company.delete()
        messages.success(request, f'Company "{company_name}" has been deleted successfully.')
        return redirect('superadmin:companies_list')
    
    # For GET requests, show confirmation page
    context = {
        'company': company,
        'sa_page': 'companies'
    }
    return render(request, 'superadmin/company_delete.html', context)

def _is_more_relevant_subscription(sub1, sub2):
    """
    Determine if subscription 1 is more relevant than subscription 2
    Priority: active > trial > suspended > expired > cancelled
    For same status, newer subscription is more relevant
    """
    status_priority = {
        'active': 5,
        'trial': 4,
        'suspended': 3,
        'expired': 2,
        'cancelled': 1
    }
    
    priority1 = status_priority.get(sub1.status, 0)
    priority2 = status_priority.get(sub2.status, 0)
    
    if priority1 != priority2:
        return priority1 > priority2
    
    # Same status, use newer one
    return sub1.created_at > sub2.created_at


@login_required(login_url='superadmin:superadmin_login')
def subscriptions_list(request):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    from .models import Payment
    from django.utils import timezone
    from datetime import timedelta, date
    from decimal import Decimal
    from django.db import models
    
    # Auto-update expired subscriptions
    expired_count = Subscription.update_expired_subscriptions()
    if expired_count > 0:
        print(f"Auto-updated {expired_count} expired subscriptions")
    
    # Get subscriptions and handle multiple subscriptions per company
    # Show the most relevant subscription per company (active > trial > expired > cancelled)
    all_subscriptions = Subscription.objects.select_related('company', 'plan').order_by('-created_at')
    payments = Payment.objects.select_related('subscription__plan', 'company').order_by('-payment_date')
    
    # Group subscriptions by company and get the most relevant one
    company_subscriptions = {}
    for subscription in all_subscriptions:
        company_id = subscription.company.id
        if company_id not in company_subscriptions:
            company_subscriptions[company_id] = subscription
        else:
            # Replace if current subscription is more relevant
            current = company_subscriptions[company_id]
            if _is_more_relevant_subscription(subscription, current):
                company_subscriptions[company_id] = subscription
    
    # Convert to list and calculate total paid for each subscription
    subscription_data = []
    for subscription in company_subscriptions.values():
        total_paid = Payment.objects.filter(
            subscription=subscription,
            status='completed'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        subscription.total_paid = total_paid
        subscription_data.append(subscription)
    
    # Sort by creation date (newest first)
    subscription_data.sort(key=lambda x: x.created_at, reverse=True)
    
    # Calculate subscription statistics from the displayed data (grouped by company)
    total_subscriptions = len(subscription_data)
    active_subscriptions = sum(1 for sub in subscription_data if sub.status == 'active')
    
    # Calculate monthly revenue (current month) - only subscription payments
    current_month_start = timezone.now().date().replace(day=1)
    current_month_end = timezone.now().date()
    
    current_month_payments = payments.filter(
        payment_date__gte=current_month_start,
        payment_date__lte=current_month_end,
        status='completed',
        payment_type='subscription'  # Only count subscription payments, not setup fees or other types
    )
    monthly_revenue = current_month_payments.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Calculate MRR (Monthly Recurring Revenue) more accurately
    # For monthly subscriptions: total_amount
    # For yearly subscriptions: total_amount / 12
    mrr_total = Decimal('0.00')
    active_subs = all_subscriptions.filter(status='active')
    
    for sub in active_subs:
        if sub.billing_cycle == 'monthly':
            mrr_total += sub.total_amount
        elif sub.billing_cycle == 'yearly':
            mrr_total += sub.total_amount / Decimal('12')
    
    mrr = mrr_total
    
    # Calculate churn rate more accurately
    # Churn = (cancellations this month / total subscriptions at start of month) * 100
    subscriptions_at_start = all_subscriptions.filter(
        created_at__lt=current_month_start
    ).count()
    
    current_month_cancellations = all_subscriptions.filter(
        status='cancelled',
        cancelled_at__gte=current_month_start,
        cancelled_at__lte=timezone.now()
    ).count()
    
    churn_rate = (current_month_cancellations / subscriptions_at_start * 100) if subscriptions_at_start > 0 else 0
    
    # Get recent payments (last 10)
    recent_payments = payments[:10]
    
    # Get all companies for the dropdown
    from .models import Company
    companies = Company.objects.all().order_by('name')
    
    # Get all plans for modals
    plans = Plan.objects.all().order_by('price')
    
    # Add user profile to context for header display
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    context = {
        'subscriptions': subscription_data,
        'all_subscriptions_list': subscription_data,  # Template expects this variable name
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'monthly_revenue': monthly_revenue,
        'mrr': mrr,
        'churn_rate': round(churn_rate, 1),
        'recent_payments': recent_payments,
        'companies': companies,  # Add companies for the dropdown
        'plans': plans,  # Add plans for modals
        'currency_symbol': '₹',  # Default currency symbol
        'sa_page': 'subscriptions',
        'user_profile': profile  # Add user profile for header display
    }
    
    return render(request, 'superadmin/subscriptions.html', context)

@login_required(login_url='superadmin:superadmin_login')
def subscription_change_plan(request, subscription_id):
    """Handle subscription upgrade/downgrade"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        from .models import Subscription, Plan
        
        # Get subscription
        subscription = get_object_or_404(Subscription, id=subscription_id)
        
        # Allow plan changes during trial period - users can upgrade anytime!
        # This enables users to convert to paid plans during their 7-day trial
        if subscription.status == 'trial':
            from django.utils import timezone
            if subscription.trial_end_date and timezone.now() < subscription.trial_end_date:
                # User is in trial period - allow upgrade to paid plans
                pass  # Continue with plan change process
        
        # Get form data
        new_plan_code = request.POST.get('new_plan')
        new_billing_cycle = request.POST.get('new_billing_cycle')
        effective_date_str = request.POST.get('effective_date')
        
        # Validate required fields
        if not all([new_plan_code, new_billing_cycle, effective_date_str]):
            return JsonResponse({'error': 'All required fields must be filled'}, status=400)
        
        # Parse effective date
        from datetime import datetime
        try:
            effective_date = datetime.strptime(effective_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid effective date format'}, status=400)
        
        # Map plan codes to actual plans
        plan_mapping = {
            'basic': 'Basic',
            'standard': 'Standard', 
            'premium': 'Premium',
            'enterprise': 'Enterprise'
        }
        
        plan_name = plan_mapping.get(new_plan_code)
        if not plan_name:
            return JsonResponse({'error': 'Invalid plan selected'}, status=400)
        
        # Get the new plan
        new_plan = get_object_or_404(Plan, name=plan_name)
        
        # Calculate new amount based on billing cycle
        base_price = new_plan.price
        if new_billing_cycle == 'quarterly':
            new_amount = base_price * 3
        elif new_billing_cycle == 'yearly':
            new_amount = base_price * 12
        else:  # monthly
            new_amount = base_price
        
        # Store old values for history
        old_plan = subscription.plan
        old_amount = subscription.total_amount
        old_billing_cycle = subscription.billing_cycle
        
        # Update subscription
        subscription.plan = new_plan
        subscription.billing_cycle = new_billing_cycle
        subscription.total_amount = new_amount
        subscription.next_billing_date = effective_date
        
        # Save changes
        subscription.save()
        
        # Create a payment record for the plan change
        from .models import Payment
        import uuid
        from django.utils import timezone
        
        Payment.objects.create(
            company=subscription.company,
            subscription=subscription,
            amount=new_amount - old_amount if new_amount != old_amount else 0,
            payment_method='manual',
            payment_type='upgrade' if new_amount > old_amount else 'refund' if new_amount < old_amount else 'subscription',
            status='completed',
            payment_date=timezone.now(),
            transaction_id=f'PLAN-CHANGE-{uuid.uuid4().hex[:8].upper()}',
            notes=f'Plan changed from {old_plan.name} ({old_billing_cycle}) to {new_plan.name} ({new_billing_cycle})'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully changed plan to {new_plan.name}',
            'new_plan': new_plan.name,
            'new_amount': f'${new_amount:.2f}',
            'new_billing_cycle': new_billing_cycle
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='superadmin:superadmin_login')
def subscription_view(request, subscription_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    from .models import Payment
    from django.utils import timezone
    
    # Get subscription with related data
    subscription = get_object_or_404(Subscription.objects.select_related('company', 'plan'), id=subscription_id)
    
    # Get payment history for this subscription
    payments = Payment.objects.filter(subscription=subscription).order_by('-payment_date')
    
    # Calculate subscription metrics
    total_paid = payments.filter(status='completed').aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    # Get days remaining
    if subscription.end_date and subscription.status == 'active':
        days_remaining = (subscription.end_date - timezone.now().date()).days
    else:
        days_remaining = 0
    
    context = {
        'subscription': subscription,
        'payments': payments,
        'total_paid': total_paid,
        'days_remaining': days_remaining,
        'currency_symbol': '₹',  # Add currency symbol
        'sa_page': 'subscriptions'
    }
    
    return render(request, 'superadmin/subscription_view.html', context)


@login_required(login_url='superadmin:superadmin_login')
def subscription_edit(request, subscription_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    from django.http import JsonResponse
    from django.utils import timezone
    from decimal import Decimal
    from datetime import datetime
    
    # Get subscription with related data
    subscription = get_object_or_404(Subscription.objects.select_related('company', 'plan'), id=subscription_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            status = request.POST.get('status')
            billing_cycle = request.POST.get('billing_cycle')
            total_amount = request.POST.get('total_amount')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            next_billing_date = request.POST.get('next_billing_date')
            
            # Update subscription
            if status:
                subscription.status = status
            if billing_cycle:
                subscription.billing_cycle = billing_cycle
            if total_amount:
                subscription.total_amount = Decimal(total_amount)
            if start_date:
                try:
                    subscription.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass  # Keep existing value if parsing fails
            if end_date:
                try:
                    subscription.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass  # Keep existing value if parsing fails
            if next_billing_date:
                try:
                    subscription.next_billing_date = datetime.strptime(next_billing_date, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    pass  # Keep existing value if parsing fails
            
            # Set timestamps based on status changes
            if status == 'cancelled' and subscription.status != 'cancelled':
                subscription.cancelled_at = timezone.now()
            elif status == 'active' and subscription.status != 'active':
                subscription.activated_at = timezone.now()
            
            subscription.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Subscription updated successfully!'
                })
            else:
                return redirect('superadmin:subscriptions_list')
                
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=400)
            else:
                # Handle non-Ajax POST
                pass
    
    context = {
        'subscription': subscription,
        'sa_page': 'subscriptions'
    }
    
    return render(request, 'superadmin/subscription_edit.html', context)


@login_required(login_url='superadmin:superadmin_login')
def transaction_details(request, payment_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    from .models import Payment
    from django.http import JsonResponse
    
    try:
        # Get payment with related data
        payment = get_object_or_404(Payment.objects.select_related('subscription__plan', 'subscription__company', 'company'), id=payment_id)
        
        # Prepare transaction data
        transaction_data = {
            'id': payment.id,
            'amount': str(payment.amount),
            'status': payment.status,
            'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else None,
            'payment_method': payment.payment_method or 'N/A',
            'transaction_id': payment.transaction_id or 'N/A',
            'company': {
                'name': payment.company.name if payment.company else (payment.subscription.company.name if payment.subscription else 'N/A'),
                'email': payment.company.email if payment.company else (payment.subscription.company.email if payment.subscription else 'N/A')
            },
            'subscription': {
                'plan': payment.subscription.plan.name if payment.subscription else 'N/A',
                'status': payment.subscription.status if payment.subscription else 'N/A'
            },
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': payment.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return JsonResponse({
            'success': True,
            'transaction': transaction_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@login_required(login_url='superadmin:superadmin_login')
# Function to view all agents
def agents_list(request):
    """View all agents in the system"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    # Get all users with Agent role
    agents = User.objects.filter(
        userprofile__role__name='Agent'
    ).select_related('userprofile__role').order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(agents, 5)  # Show 5 agents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get subscription data for each agent in current page
    agent_data = []
    active_agents = 0
    agents_with_subscription = 0
    
    for agent in page_obj:
        # Get agent's company
        company = getattr(agent, 'company', None)
        # Get agent's subscription
        subscription = Subscription.objects.filter(company=company).first() if company else None
        
        # Count active agents
        if agent.is_active:
            active_agents += 1
            
        # Count agents with subscription
        if subscription:
            agents_with_subscription += 1
        
        agent_info = {
            'id': agent.id,
            'name': agent.get_full_name() or agent.username,
            'email': agent.email,
            'company': company.name if company else 'No Company',
            'company_id': company.id if company else None,
            'role': agent.userprofile.role.name if hasattr(agent, 'userprofile') and agent.userprofile.role else 'No Role',
            'status': 'Active' if agent.is_active else 'Inactive',
            'joined_date': agent.date_joined.strftime('%Y-%m-%d') if agent.date_joined else 'N/A',
            'subscription_plan': subscription.plan.name if subscription else 'No Subscription',
            'subscription_status': subscription.status if subscription else 'No Subscription',
            'subscription_end_date': subscription.end_date.strftime('%Y-%m-%d') if subscription and subscription.end_date else 'N/A'
        }
        agent_data.append(agent_info)
    
    # Calculate statistics for all agents (not just current page)
    total_agents_count = agents.count()
    total_active_agents = agents.filter(is_active=True).count()
    agents_with_subscription_count = 0
    
    for agent in agents:
        company = getattr(agent, 'company', None)
        if company:
            subscription = Subscription.objects.filter(company=company).first()
            if subscription:
                agents_with_subscription_count += 1
    
    # Add user profile to context for header display
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    context = {
        'agents': agent_data,
        'page_obj': page_obj,
        'paginator': paginator,
        'total_agents': total_agents_count,
        'active_agents': total_active_agents,
        'inactive_agents': total_agents_count - total_active_agents,
        'agents_with_subscription': agents_with_subscription_count,
        'sa_page': 'agents',
        'user_profile': profile  # Add user profile for header display
    }
    
    return render(request, 'superadmin/agents_list.html', context)

def agents_add(request):
    """Add a new agent"""
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    if request.method == 'POST':
            from .models import User, Company
            from django.contrib import messages
            from django.core.exceptions import ValidationError
            
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            role_id = request.POST.get('role', '')
            company_id = request.POST.get('company', '')
            is_active = request.POST.get('is_active', 'true') == 'true'
            
            # Validate required fields
            if not all([first_name, email, password, role_id, company_id]):
                messages.error(request, 'All fields are required')
                return JsonResponse({'success': False, 'message': 'All fields are required'})
            
            try:
                # Create user
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=first_name,
                    role_id=role_id,
                    is_active=is_active
                )
                
                # Assign company if provided
                if company_id:
                    try:
                        company = Company.objects.get(id=company_id)
                        user.company = company
                        user.save()
                    except Company.DoesNotExist:
                        messages.error(request, 'Selected company does not exist')
                        return JsonResponse({'success': False, 'message': 'Selected company does not exist'})
                
                # Assign role if provided
                if role_id:
                    try:
                        role = Role.objects.get(id=role_id)
                        user.role = role
                        user.save()
                    except Role.DoesNotExist:
                        messages.error(request, 'Selected role does not exist')
                        return JsonResponse({'success': False, 'message': 'Selected role does not exist'})
                
                messages.success(request, f'Agent {first_name} {email} has been created successfully!')
                return JsonResponse({'success': True, 'message': f'Agent {first_name} {email} has been created successfully!'})
                
            except ValidationError as e:
                return JsonResponse({'success': False, 'message': str(e)})
            except Exception as e:
                return JsonResponse({'success': False, 'message': f'Error creating agent: {str(e)}'})
    
    # Get all users for context
    companies = Company.objects.all()
    roles = Role.objects.all()
    
    context = {
        'companies': companies,
        'roles': roles,
        'sa_page': 'agents_add'
    }
    
    return render(request, 'superadmin/agents_add.html', context)

def users_list(request):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    # Get only users with "User" role (excluding Admin, Agent, SuperAdmin)
    users_queryset = User.objects.filter(
        userprofile__role__name='User'
    ).order_by('-date_joined')
    
    # Debug: Print the count
    print(f"DEBUG: Total users with 'User' role: {users_queryset.count()}")
    
    # Pagination: 7 users per page
    paginator = Paginator(users_queryset, 7)
    page = request.GET.get('page')
    
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        users = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        users = paginator.page(paginator.num_pages)
    
    # Debug: Print pagination info
    print(f"DEBUG: Page {page}, showing {users.start_index}-{users.end_index} of {paginator.count} total users")
    
    # Get all companies for the dropdown
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    # Calculate total users count
    total_users_queryset = User.objects.filter(
        userprofile__role__name='User'
    ).order_by('-date_joined')
    total_users = total_users_queryset.count()
    
    # Add user profile to context for header display
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    context = {
        'users': users,
        'all_companies': companies,
        'total_users': total_users,
        'sa_page': 'users',
        'user_profile': profile  # Add user profile for header display
    }
    
    return render(request, 'superadmin/users.html', context)


@login_required(login_url='superadmin:superadmin_login')
def admin_management(request):
    """Admin management page to view and manage admin users"""
    try:
        from users.models import Role, UserProfile
    except ImportError:
        messages.error(request, 'User models not available. Please check app configuration.')
        return redirect('superadmin:superadmin_dashboard')
    
    # Get admin users (including both Admin and SuperAdmin roles)
    admin_users = User.objects.filter(
        Q(userprofile__role__name='Admin') | 
        Q(is_superuser=True)
    ).distinct().order_by('-date_joined')
    
    # Calculate statistics for all admin-level users
    total_admins = admin_users.count()
    active_admins = admin_users.filter(is_active=True).count()
    inactive_admins = total_admins - active_admins
    
    # Separate counts by role for better distinction
    regular_admins = admin_users.filter(userprofile__role__name='Admin', is_superuser=False)
    superadmins = admin_users.filter(is_superuser=True)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(admin_users, 10)  # Show 10 admin users per page
    
    try:
        admins = paginator.page(page)
    except PageNotAnInteger:
        admins = paginator.page(1)
    except EmptyPage:
        admins = paginator.page(paginator.num_pages)
    
    # Add user profile to context for header display
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    context = {
        'admins': admins,
        'total_admins': total_admins,
        'active_admins': active_admins,
        'inactive_admins': inactive_admins,
        'regular_admins_count': regular_admins.count(),
        'superadmins_count': superadmins.count(),
        'sa_page': 'admin_management',
        'user_profile': profile  # Add user profile for header display
    }
    
    return render(request, 'superadmin/admin_management.html', context)


@login_required(login_url='superadmin:superadmin_login')
@require_POST
def admin_add(request):
    """Add a new admin user via AJAX"""
    try:
        from users.models import Role, UserProfile
        from django.contrib.auth.models import User
        
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        role_name = request.POST.get('role', '')
        is_staff = request.POST.get('is_staff') == 'true'
        is_superuser = request.POST.get('is_superuser') == 'true'
        
        print(f"DEBUG: Received data - username: {username}, email: {email}, role: {role_name}")
        
        # Validate required fields
        if not username or not email or not role_name:
            return JsonResponse({
                'success': False,
                'message': 'Username, email, and role are required.'
            })
        
        # Get the role
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': f'Role "{role_name}" does not exist.'
            })
        
        # Try to find existing user
        user = None
        try:
            user = User.objects.get(username=username)
            print(f"DEBUG: Found existing user by username: {user.username}")
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=email)
                print(f"DEBUG: Found existing user by email: {user.username}")
            except User.DoesNotExist:
                print("DEBUG: User not found, will create new user")
                pass
        
        # If user exists, update them
        if user:
            try:
                # Update user details
                user.first_name = first_name
                user.last_name = last_name
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save()
                
                # Update or create profile
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.role = role
                profile.save()
                
                print(f"DEBUG: Updated user {user.username} successfully")
                
                return JsonResponse({
                    'success': True,
                    'message': f'User "{user.username}" has been updated with admin role successfully!'
                })
                
            except Exception as e:
                print(f"DEBUG: Error updating user: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'Error updating user: {str(e)}'
                })
        
        # Create new user
        if not password:
            return JsonResponse({
                'success': False,
                'message': 'Password is required for new users.'
            })
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=is_staff,
                is_superuser=is_superuser
            )
            
            # Create profile
            try:
                # Check if user already has a profile
                if hasattr(user, 'userprofile'):
                    # Update existing profile
                    profile = user.userprofile
                    profile.role = role
                    profile.save()
                    print(f"DEBUG: Updated existing UserProfile for user {user.username}")
                else:
                    # Create new profile
                    UserProfile.objects.create(user=user, role=role)
                    print(f"DEBUG: Created new UserProfile for user {user.username}")
            except Exception as e:
                print(f"DEBUG: Profile creation error: {str(e)}")
                # If profile creation fails, delete the user
                user.delete()
                return JsonResponse({
                    'success': False,
                    'message': f'Error creating user profile: {str(e)}'
                })
            
            print(f"DEBUG: Created new user {user.username} successfully")
            
            return JsonResponse({
                'success': True,
                'message': 'Admin user created successfully!'
            })
            
        except Exception as e:
            print(f"DEBUG: Error creating user: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error creating user: {str(e)}'
            })
        
    except Exception as e:
        print(f"DEBUG: General error: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


def superadmin_login(request):



    # Already authenticated and authorized -> go to appropriate dashboard



    if is_admin_or_superadmin(request.user):



        return redirect(get_role_based_redirect(request.user))







    if request.method == 'POST':



        username_or_email = (request.POST.get('username') or '').strip()



        password = request.POST.get('password') or ''







        # Allow login via username OR email



        lookup_username = username_or_email



        if '@' in username_or_email:



            from django.contrib.auth.models import User as DjangoUser



            email_user = DjangoUser.objects.filter(email=username_or_email).first()



            if email_user:



                lookup_username = email_user.username







        user = authenticate(request, username=lookup_username, password=password)







        if user and is_admin_or_superadmin(user):



            login(request, user)



            



            # Redirect based on user role



            return redirect(get_role_based_redirect(user))







        messages.error(request, 'Invalid credentials or not authorized')







    return render(request, 'superadmin/login.html')


def superadmin_forgot_password(request):
    """Handle forgot password request for superadmin"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Email address is required')
            return render(request, 'superadmin/forgot_password.html')
        
        # Check if email exists and belongs to a superadmin
        from django.contrib.auth.models import User as DjangoUser
        from users.models import UserProfile
        
        user = DjangoUser.objects.filter(email=email).first()
        
        if user:
            if _is_superadmin_user(user):
                # Generate 6-digit verification code
                import random
                verification_code = f"{random.randint(100000, 999999)}"
                
                # Store code in session (valid for 15 minutes)
                request.session[f'reset_code_{email}'] = {
                    'code': verification_code,
                    'timestamp': str(timezone.now().timestamp()),
                    'email': email
                }
                request.session.modified = True
                
                # Send email with verification code
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    subject = 'SuperAdmin Password Reset Code - TicketHub'
                    message = f'''
Hello SuperAdmin,

You requested to reset your password for TicketHub.

Your verification code is: {verification_code}

This code will expire in 15 minutes.

If you didn't request this password reset, please ignore this email.

Best regards,
TicketHub Team
                    '''
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    
                    messages.success(request, f'Verification code sent to {email}. Please check your email.')
                    return redirect(f'/superadmin/reset-password/?email={email}')
                    
                except Exception as e:
                    print(f"Error sending email: {e}")
                    messages.error(request, 'Failed to send verification code. Please try again.')
            else:
                # User exists but is not a superadmin
                messages.error(request, 'Your email is not registered as a SuperAdmin')
                return render(request, 'superadmin/forgot_password.html')
        else:
            # Show specific message if email is not registered
            messages.error(request, 'Your email is not registered')
            return render(request, 'superadmin/forgot_password.html')
    
    return render(request, 'superadmin/forgot_password.html')


def superadmin_reset_password(request):
    """Handle password reset with verification code"""
    # Get email from POST, GET, or session
    email = request.POST.get('email') or request.GET.get('email')
    
    # If no email in POST/GET, try to get it from session
    if not email:
        # Find any reset code in session to get the email
        for key, value in request.session.items():
            if key.startswith('reset_code_') and isinstance(value, dict):
                email = value.get('email')
                break
    
    if not email:
        messages.error(request, 'Email is required. Please start the forgot password process again.')
        return redirect('superadmin:forgot_password')
    
    if request.method == 'POST':
        # Get verification code from form inputs
        code = ''.join([
            request.POST.get('code1', ''),
            request.POST.get('code2', ''),
            request.POST.get('code3', ''),
            request.POST.get('code4', ''),
            request.POST.get('code5', ''),
            request.POST.get('code6', '')
        ])
        
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        # Validate inputs
        if len(code) != 6:
            messages.error(request, 'Invalid verification code')
            return render(request, 'superadmin/reset_password.html', {'email': email})
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'superadmin/reset_password.html', {'email': email})
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'superadmin/reset_password.html', {'email': email})
        
        # Check verification code
        session_data = request.session.get(f'reset_code_{email}')
        
        if not session_data:
            messages.error(request, 'Verification code expired or invalid. Please request a new one.')
            return redirect('superadmin:forgot_password')
        
        # Check if code is valid (15 minutes expiry)
        import time
        timestamp = float(session_data['timestamp'])
        current_time = timezone.now().timestamp()
        
        if current_time - timestamp > 900:  # 15 minutes = 900 seconds
            del request.session[f'reset_code_{email}']
            request.session.modified = True
            messages.error(request, 'Verification code expired. Please request a new one.')
            return redirect('superadmin:forgot_password')
        
        if session_data['code'] != code:
            messages.error(request, 'Invalid verification code')
            return render(request, 'superadmin/reset_password.html', {'email': email})
        
        # Code is valid, reset password
        try:
            from django.contrib.auth.models import User as DjangoUser
            
            user = DjangoUser.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            
            # Clear the session data
            del request.session[f'reset_code_{email}']
            request.session.modified = True
            
            messages.success(request, 'Password reset successfully! Please login with your new password.')
            return redirect('superadmin:superadmin_login')
            
        except DjangoUser.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('superadmin:forgot_password')
        except Exception as e:
            print(f"Error resetting password: {e}")
            messages.error(request, 'Failed to reset password. Please try again.')
            return render(request, 'superadmin/reset_password.html', {'email': email})
    
    return render(request, 'superadmin/reset_password.html', {'email': email})


def admin_login(request):



    # Already authenticated and authorized -> go to appropriate dashboard



    if is_admin_or_superadmin(request.user):



        return redirect(get_role_based_redirect(request.user))







    if request.method == 'POST':



        username_or_email = (request.POST.get('username') or '').strip()



        password = request.POST.get('password') or ''







        # Allow login via username OR email



        lookup_username = username_or_email



        if '@' in username_or_email:



            from django.contrib.auth.models import User as DjangoUser



            email_user = DjangoUser.objects.filter(email=username_or_email).first()



            if email_user:



                lookup_username = email_user.username







        user = authenticate(request, username=lookup_username, password=password)







        if user and is_admin_or_superadmin(user):



            login(request, user)



            



            # Redirect based on user role



            return redirect(get_role_based_redirect(user))







        messages.error(request, 'Invalid credentials or not authorized')







    return render(request, 'superadmin/admin_login.html')















def get_recent_comments():
    """Get recent comments with ticket information"""
    return TicketComment.objects.select_related(
        'author', 'ticket'
    ).order_by('-created_at')[:10]


def get_latest_tickets():
    """Get latest tickets with assigned user information"""
    return Ticket.objects.select_related(
        'assigned_to', 'created_by'
    ).order_by('-created_at')[:10]









@login_required(login_url='superadmin:superadmin_login')



def recent_comments_api(request):



    """API endpoint to get recent comments for the dashboard widget"""



    if not _is_superadmin_user(request.user):



        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)



    



    if request.method != 'GET':



        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)



    



    try:



        comments = get_recent_comments()



        comments_data = []



        



        for comment in comments:



            comments_data.append({



                'id': comment.id,



                'content': comment.content,



                'created_at': comment.created_at.strftime('%b %d, %Y %H:%M'),



                'author_name': comment.author.get_full_name() or comment.author.username,



                'author_username': comment.author.username,



                'ticket_id': comment.ticket.id,



                'ticket_title': comment.ticket.title,



                'ticket_ticket_id': comment.ticket.ticket_id,



                'is_internal': comment.is_internal,



                'ticket_url': f'/tickets/{comment.ticket.id}/'



            })



        



        return JsonResponse({



            'success': True,



            'comments': comments_data,



            'count': len(comments_data)



        })



        



    except Exception as e:



        return JsonResponse({'success': False, 'message': str(e)}, status=500)











@login_required(login_url='superadmin:superadmin_login')



def ticket_search_api(request):



    """API endpoint to search tickets for SuperAdmin dashboard"""



    if not _is_superadmin_user(request.user):



        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)



    



    if request.method != 'GET':



        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)



    



    try:



        search_query = request.GET.get('q', '').strip()



        search_type = request.GET.get('type', 'all')  # all, id, title, status, priority, category, assigned, user



        



        if not search_query:



            return JsonResponse({



                'success': True,



                'tickets': [],



                'count': 0,



                'message': 'Please enter a search term'



            })



        



        # Start with base queryset



        tickets = Ticket.objects.select_related('created_by', 'assigned_to')



        



        # Apply search based on type



        if search_type == 'id':



            # Search by ticket ID



            tickets = tickets.filter(ticket_id__icontains=search_query)



        elif search_type == 'title':



            # Search by title



            tickets = tickets.filter(title__icontains=search_query)



        elif search_type == 'status':



            # Search by status



            tickets = tickets.filter(status__icontains=search_query)



        elif search_type == 'assigned':
            # Search by assigned user (comprehensive)
            tickets = tickets.filter(
                models.Q(assigned_to__username__icontains=search_query) |
                models.Q(assigned_to__first_name__icontains=search_query) |
                models.Q(assigned_to__last_name__icontains=search_query) |
                models.Q(assigned_to__email__icontains=search_query)
            )
        elif search_type == 'priority':
            # Search by priority
            tickets = tickets.filter(priority__icontains=search_query)
        elif search_type == 'category':
            # Search by category
            tickets = tickets.filter(category__icontains=search_query)
        elif search_type == 'user':
            # Search by user details (created by)
            tickets = tickets.filter(
                models.Q(created_by__username__icontains=search_query) |
                models.Q(created_by__first_name__icontains=search_query) |
                models.Q(created_by__last_name__icontains=search_query) |
                models.Q(created_by__email__icontains=search_query)
            )
        else:
            # Search across multiple fields (default)
            tickets = tickets.filter(
                models.Q(ticket_id__icontains=search_query) |
                models.Q(title__icontains=search_query) |
                models.Q(status__icontains=search_query) |
                models.Q(priority__icontains=search_query) |
                models.Q(category__icontains=search_query) |
                models.Q(description__icontains=search_query) |
                models.Q(created_by__username__icontains=search_query) |
                models.Q(created_by__first_name__icontains=search_query) |
                models.Q(created_by__last_name__icontains=search_query) |
                models.Q(created_by__email__icontains=search_query) |
                models.Q(assigned_to__username__icontains=search_query) |
                models.Q(assigned_to__first_name__icontains=search_query) |
                models.Q(assigned_to__last_name__icontains=search_query) |
                models.Q(assigned_to__email__icontains=search_query)
            )



        # Order by most recent first and limit results



        tickets = tickets.order_by('-created_at')[:20]



        



        # Prepare ticket data



        tickets_data = []



        for ticket in tickets:



            tickets_data.append({



                'id': ticket.id,



                'ticket_id': ticket.ticket_id,



                'title': ticket.title,



                'status': ticket.status,



                'priority': ticket.priority,



                'category': ticket.category or 'General',



                'created_at': ticket.created_at.strftime('%b %d, %Y %H:%M'),



                'created_by': ticket.created_by.get_full_name() or ticket.created_by.username,



                'assigned_to': ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unassigned',



                'url': f'/tickets/{ticket.id}/',



                'status_class': get_status_class(ticket.status),



                'priority_class': get_priority_class(ticket.priority)



            })



        



        return JsonResponse({



            'success': True,



            'tickets': tickets_data,



            'count': len(tickets_data),



            'query': search_query,



            'type': search_type



        })



        



    except Exception as e:



        return JsonResponse({'success': False, 'message': str(e)}, status=500)











@login_required(login_url='superadmin:superadmin_login')
def tickets_api(request):
    """API endpoint to load tickets for SuperAdmin tickets page"""
    if not _is_superadmin_user(request.user):
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    try:
        # Get query parameters
        search = request.GET.get('search', '').strip()
        status = request.GET.get('status', '').strip()
        priority = request.GET.get('priority', '').strip()
        
        # Start with base queryset
        tickets = Ticket.objects.select_related('created_by', 'assigned_to').order_by('-created_at')
        
        # Apply filters
        if search:
            tickets = tickets.filter(
                models.Q(ticket_id__icontains=search) |
                models.Q(title__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(created_by__username__icontains=search) |
                models.Q(created_by__first_name__icontains=search) |
                models.Q(created_by__last_name__icontains=search) |
                models.Q(assigned_to__username__icontains=search) |
                models.Q(assigned_to__first_name__icontains=search) |
                models.Q(assigned_to__last_name__icontains=search)
            )
        
        if status:
            tickets = tickets.filter(status=status)
        
        if priority:
            tickets = tickets.filter(priority=priority)
        
        # Limit to 100 results for performance
        tickets = tickets[:100]
        
        # Prepare ticket data
        tickets_data = []
        for ticket in tickets:
            tickets_data.append({
                'id': ticket.id,
                'ticket_id': ticket.ticket_id,
                'title': ticket.title,
                'status': ticket.status,
                'priority': ticket.priority,
                'category': ticket.category or 'General',
                'created_at': ticket.created_at.isoformat(),
                'created_by': ticket.created_by.get_full_name() or ticket.created_by.username,
                'assigned_to': ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unassigned',
            })
        
        return JsonResponse({
            'success': True,
            'tickets': tickets_data,
            'count': len(tickets_data)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def get_status_class(status):
    """Get CSS class for ticket status"""

    status_classes = {



        'Open': 'badge-open',



        'In Progress': 'badge-progress',



        'Resolved': 'badge-resolved',



        'Closed': 'badge-closed'



    }



    return status_classes.get(status, 'badge-closed')











def get_priority_class(priority):



    """Get CSS class for ticket priority"""



    priority_classes = {



        'Low': 'badge-low',



        'Medium': 'badge-medium',



        'High': 'badge-high',



        'Critical': 'badge-critical'



    }



    return priority_classes.get(priority, 'badge-low')











@login_required(login_url='superadmin:superadmin_login')



def superadmin_dashboard(request):



    if not _is_superadmin_user(request.user):



        return redirect('superadmin:superadmin_login')







    # Check and create system notifications



    check_and_create_system_notifications()







    # Get or create user settings for currency



    settings, created = SuperAdminSettings.objects.get_or_create(



        user=request.user,



        defaults={



            'profile_name': request.user.get_full_name(),



            'profile_email': request.user.email,



        }



    )



    



    # Calculate real-time statistics



    from django.db.models import Sum, Count



    



    # Total companies



    total_companies = Company.objects.filter(is_active=True).count()



    



    # Total users by role
    try:
        from users.models import Role, UserProfile
        total_users = User.objects.filter(
            userprofile__role__name='User',
            is_active=True
        ).count()
        total_admins = User.objects.filter(
            userprofile__role__name='Admin',
            is_active=True
        ).count()
        total_superadmins = User.objects.filter(
            is_superuser=True,
            is_active=True
        ).count()
    except ImportError:
        # Fallback if user models not available
        total_users = User.objects.filter(is_active=True).count()
        total_admins = 0
        total_superadmins = 0



    



    # Total active plans (should always be 3 - Basic, Standard, Premium)
    total_plans = Plan.objects.filter(is_active=True, status='active').count()
    
    # Total active subscriptions
    active_subscriptions = Subscription.objects.filter(status='active').count()
    
    # Total revenue from successful payments (convert USD to INR)
    usd_revenue = Payment.objects.filter(
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Convert USD to INR (1 USD = 83 INR approximately)
    conversion_rate = 83
    total_revenue = usd_revenue * conversion_rate



    
    



    # Chart data preparation



    from django.db.models import Sum, Count



    from datetime import datetime, timedelta



    import calendar



    



    # Tickets Over Time Chart Data (default: all time)
    tickets_chart_data = []
    tickets_chart_labels = []
    
    tickets_chart_data_7days = []
    tickets_chart_labels_7days = []
    
    tickets_chart_data_3months = []
    tickets_chart_labels_3months = []
    
    tickets_chart_data_alltime = []
    tickets_chart_labels_alltime = []



    
    # Last 30 days data

    for i in range(30):

        date = timezone.now() - timedelta(days=i)

        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)

        end_date = start_date + timedelta(days=1)

        day_tickets = Ticket.objects.filter(

            created_at__gte=start_date,

            created_at__lt=end_date

        ).count()

        tickets_chart_data.insert(0, float(day_tickets))

        tickets_chart_labels.insert(0, date.strftime('%m/%d'))






    # Last 7 days data



    for i in range(7):



        date = timezone.now() - timedelta(days=i)



        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)



        end_date = start_date + timedelta(days=1)



        day_tickets = Ticket.objects.filter(



            created_at__gte=start_date,



            created_at__lt=end_date



        ).count()



        tickets_chart_data_7days.insert(0, float(day_tickets))



        tickets_chart_labels_7days.insert(0, date.strftime('%m/%d'))



    



    # Last 3 months data



    for i in range(3):



        month_date = timezone.now() - timedelta(days=30*i)



        month_start = month_date.replace(day=1)



        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)



        



        month_tickets = Ticket.objects.filter(



            created_at__gte=month_start,



            created_at__lte=month_end



        ).count()


        tickets_chart_data_3months.insert(0, float(month_tickets))
        tickets_chart_labels_3months.insert(0, calendar.month_abbr[month_start.month])

    # All time data - monthly aggregation (simplified approach)
    from django.db.models import Count
    import datetime
    
    # Get all tickets and group by month manually
    all_tickets = Ticket.objects.all().order_by('created_at')
    monthly_data = {}
    
    for ticket in all_tickets:
        month_key = ticket.created_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = 0
        monthly_data[month_key] += 1
    
    # Convert to sorted lists
    for month_key in sorted(monthly_data.keys()):
        month_date = datetime.datetime.strptime(month_key + '-01', '%Y-%m-%d')
        tickets_chart_data_alltime.append(float(monthly_data[month_key]))
        tickets_chart_labels_alltime.append(month_date.strftime('%b %Y'))

    # Plan Distribution Chart Data (Revenue by Plan)
    plan_distribution_data = []
    plan_distribution_labels = []
    
    active_plans = Plan.objects.filter(is_active=True, status='active')
    
    for plan in active_plans:
        # Calculate actual revenue for this plan from completed payments
        plan_revenue = Payment.objects.filter(
            subscription__plan=plan,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Convert USD to INR
        plan_revenue_inr = plan_revenue * 83
        
        plan_distribution_data.append(float(plan_revenue_inr))
        plan_distribution_labels.append(plan.name)


    



    # Recent transactions (last 10)



    recent_transactions = Payment.objects.select_related('company', 'subscription__plan').order_by('-payment_date')[:10]



    



    # Total tickets
    total_tickets = Ticket.objects.count()
    
    # Latest tickets (last 10)
    latest_tickets = get_latest_tickets()

    # Get notifications context
    notifications_context = get_notifications_context(request.user)
    
    # Add user profile to context
    user = request.user
    profile = getattr(user, 'userprofile', None)
    
    context = {
        'total_companies': total_companies,
        'total_users': total_users,
        'total_admins': total_admins,
        'total_superadmins': total_superadmins,
        'total_plans': total_plans,
        'active_subscriptions': active_subscriptions,
        'total_tickets': total_tickets,
        'total_revenue': total_revenue,
        'recent_transactions': recent_transactions,
        'recent_comments': latest_tickets,
        'user_profile': profile,  # Add user profile to context

        'currency_code': settings.currency,

        'currency_symbol': settings.get_currency_symbol_display(),

        # Chart data



        'tickets_chart_data': tickets_chart_data,



        'tickets_chart_labels': tickets_chart_labels,



        'tickets_chart_data_7days': tickets_chart_data_7days,



        'tickets_chart_labels_7days': tickets_chart_labels_7days,



        'tickets_chart_data_3months': tickets_chart_data_3months,

        'tickets_chart_labels_3months': tickets_chart_labels_3months,

        'tickets_chart_data_alltime': tickets_chart_data_alltime,

        'tickets_chart_labels_alltime': tickets_chart_labels_alltime,



        'plan_distribution_data': plan_distribution_data,



        'plan_distribution_labels': plan_distribution_labels,



        **notifications_context  # Add notifications context



    }



    



    return render(request, 'superadmin/dashboard.html', context)











def superadmin_logout(request):



    logout(request)



    return redirect('superadmin:superadmin_login')











def _has_superadmin_any():



    # Check if there is any Django superuser or any profile with SuperAdmin role



    try:



        has_django_su = User.objects.filter(is_superuser=True).exists()



    except Exception:



        has_django_su = False



    try:



        has_role_su = User.objects.filter(userprofile__role__name='SuperAdmin').exists()



    except Exception:



        has_role_su = False



    return has_django_su or has_role_su











@login_required(login_url='superadmin:superadmin_login')
def user_detail(request, user_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    try:
        user = User.objects.get(id=user_id)
        context = {
            'user': user,
            'sa_page': 'users'
        }
        return render(request, 'superadmin/user_detail.html', context)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('superadmin:users_list')

@login_required(login_url='superadmin:superadmin_login')
def user_edit(request, user_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    # Store the referring page in session when first accessing the edit page
    if request.method == 'GET':
        referer = request.META.get('HTTP_REFERER', '')
        if 'admin-management' in referer:
            request.session['edit_user_redirect'] = 'admin-management'
        elif 'users' in referer:
            request.session['edit_user_redirect'] = 'users'
        else:
            request.session['edit_user_redirect'] = 'users'  # default
    
    # Import models at the top to avoid import issues
    try:
        from users.models import Role, UserProfile
    except ImportError:
        messages.error(request, 'User models not available. Please check app configuration.')
        return redirect('superadmin:users_list')
    
    try:
        user = User.objects.get(id=user_id)
        if request.method == 'POST':
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            role = request.POST.get('role', '').strip()
            is_active_str = request.POST.get('is_active', '').strip()
            
            # Validate required fields
            if not all([first_name, last_name, username, email, role]):
                messages.error(request, 'All required fields must be filled.')
                return redirect('superadmin:user_edit', user_id=user_id)
            
            # Check if username is already taken by another user
            if User.objects.exclude(id=user_id).filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('superadmin:user_edit', user_id=user_id)
            
            # Check if email is already taken by another user
            if User.objects.exclude(id=user_id).filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('superadmin:user_edit', user_id=user_id)
            
            # Convert is_active to boolean
            is_active = is_active_str.lower() == 'true'
            
            # Update user basic information
            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.email = email
            user.is_active = is_active
            
            # Set Django permissions based on role
            if role == 'SuperAdmin':
                user.is_staff = True
                user.is_superuser = True
            elif role == 'Admin':
                user.is_staff = True
                user.is_superuser = False
            else:
                user.is_staff = False
                user.is_superuser = False
            
            user.save()
            
            # Update user role
            try:
                role_obj = Role.objects.get(name=role)
                if hasattr(user, 'userprofile'):
                    user_profile = user.userprofile
                    user_profile.role = role_obj
                    user_profile.save()
                else:
                    # Create user profile if it doesn't exist
                    UserProfile.objects.create(user=user, role=role_obj)
            except Role.DoesNotExist:
                messages.error(request, f'Role "{role}" not found.')
                return redirect('superadmin:user_edit', user_id=user_id)
            except Exception as e:
                messages.error(request, f'Error updating user role: {str(e)}')
                return redirect('superadmin:user_edit', user_id=user_id)
            
            messages.success(request, f'User "{username}" updated successfully.')
            
            # Use session to determine where to redirect
            redirect_target = request.session.get('edit_user_redirect', 'users')
            if redirect_target == 'admin-management':
                return redirect('superadmin:admin_management')
            else:
                return redirect('superadmin:users_list')
        
        context = {
            'user': user,
            'sa_page': 'users',
            'from_admin_management': request.session.get('edit_user_redirect') == 'admin-management'
        }
        return render(request, 'superadmin/user_edit.html', context)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('superadmin:users_list')

@login_required(login_url='superadmin:superadmin_login')
@require_POST
def toggle_user_status(request, user_id):
    """Toggle user active/inactive status"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent user from deactivating themselves
        if user.id == request.user.id:
            return JsonResponse({'success': False, 'message': 'Cannot deactivate your own account'})
        
        # Prevent regular admins from deactivating superadmins
        if user.is_superuser and not request.user.is_superuser:
            return JsonResponse({'success': False, 'message': 'Cannot deactivate SuperAdmin accounts'})
        
        # Toggle the user's active status
        user.is_active = not user.is_active
        user.save()
        
        status = "activated" if user.is_active else "deactivated"
        return JsonResponse({
            'success': True, 
            'message': f'User "{user.username}" has been {status}'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required(login_url='superadmin:superadmin_login')
def superadmin_profile(request):
    """Superadmin profile page with dynamic statistics"""
    
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    try:
        # Get dynamic statistics from backend
        from tickets.models import Ticket
        from superadmin.models import Company
        from users.models import Role, UserProfile
        from .models import SuperAdminSettings
        
        # Count tickets
        total_tickets = Ticket.objects.count()
        
        # Count companies (only active ones to match dashboard)
        total_companies = Company.objects.filter(is_active=True).count()
        
        # Count users by role (only active ones to match dashboard)
        total_users = User.objects.filter(
            userprofile__role__name='User',
            is_active=True
        ).count()
        
        # Get additional statistics (only active users for consistency)
        total_agents = User.objects.filter(
            userprofile__role__name='Agent',
            is_active=True
        ).count()
        
        total_admins = User.objects.filter(
            Q(userprofile__role__name='Admin', is_active=True) | Q(is_superuser=True, is_active=True)
        ).distinct().count()
        
        # Get or create profile settings for the current user
        profile_settings, created = SuperAdminSettings.objects.get_or_create(
            user=request.user,
            defaults={
                'profile_phone': '',
                'profile_address': '',
                'department': 'System Administration',
                'role': 'Super Administrator',
                'employee_id': 'SA-001',
                'join_date': timezone.now().date(),
                'skills': 'System Administration, Database Management, Network Security, Project Management'
            }
        )
        
        context = {
            'total_tickets': total_tickets,
            'total_companies': total_companies, 
            'total_users': total_users,
            'total_agents': total_agents,
            'total_admins': total_admins,
            'profile_settings': profile_settings,
            'sa_page': 'profile'
        }
        
        return render(request, 'superadmin/profile.html', context)
        
    except Exception as e:
        
        # Fallback to default values if there's an error
        from .models import SuperAdminSettings
        profile_settings = SuperAdminSettings(
            profile_phone='',
            profile_address='',
            department='System Administration',
            role='Super Administrator',
            employee_id='SA-001',
            join_date=timezone.now().date(),
            skills='System Administration, Database Management, Network Security, Project Management'
        )
        
        context = {
            'total_tickets': 0,
            'total_companies': 0,
            'total_users': 0,
            'total_agents': 0,
            'total_admins': 0,
            'profile_settings': profile_settings,
            'sa_page': 'profile'
        }
        return render(request, 'superadmin/profile.html', context)

@login_required(login_url='superadmin:superadmin_login')
@require_POST
def profile_upload(request):
    """Handle profile picture uploads and other profile AJAX requests"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    action = request.POST.get('action')
    
    if action == 'upload_profile_picture':
        try:
            from users.models import UserProfile
            
            # Get or create UserProfile
            profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={}
            )
            
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
                
                # Return the picture URL in the response
                picture_url = profile.profile_picture.url if profile.profile_picture else None
                return JsonResponse({
                    'success': True, 
                    'message': 'Profile picture updated',
                    'picture_url': picture_url
                })
            else:
                return JsonResponse({'success': False, 'message': 'No file uploaded'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error uploading picture: {str(e)}'})
    
    elif action == 'remove_profile_picture':
        try:
            from users.models import UserProfile
            
            # Get UserProfile
            try:
                profile = UserProfile.objects.get(user=request.user)
                
                if profile.profile_picture:
                    # Delete the file from storage
                    try:
                        import os
                        from django.conf import settings
                        if profile.profile_picture and hasattr(profile.profile_picture, 'path'):
                            file_path = profile.profile_picture.path
                            if os.path.exists(file_path):
                                os.remove(file_path)
                    except Exception:
                        pass  # Ignore file deletion errors
                    
                    # Clear the profile picture field
                    profile.profile_picture = None
                    profile.save()
                    return JsonResponse({'success': True, 'message': 'Profile picture removed successfully'})
                else:
                    return JsonResponse({'success': False, 'message': 'No profile picture to remove'})
                    
            except UserProfile.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'No profile found'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error removing picture: {str(e)}'})
    
    elif action == 'delete_account':
        try:
            password = request.POST.get('password', '')
            
            if not password:
                return JsonResponse({'success': False, 'message': 'Password is required'})
            
            # Verify password
            user = authenticate(request, username=request.user.username, password=password)
            if not user:
                return JsonResponse({'success': False, 'message': 'Invalid password'})
            
            # Prevent deletion of the last superadmin
            superadmin_count = User.objects.filter(is_superuser=True).count()
            if request.user.is_superuser and superadmin_count <= 1:
                return JsonResponse({'success': False, 'message': 'Cannot delete the last SuperAdmin account'})
            
            # Delete user's profile picture file if exists
            try:
                from users.models import UserProfile
                profile = UserProfile.objects.filter(user=request.user).first()
                if profile and profile.profile_picture:
                    import os
                    from django.conf import settings
                    if profile.profile_picture and hasattr(profile.profile_picture, 'path'):
                        file_path = profile.profile_picture.path
                        if os.path.exists(file_path):
                            os.remove(file_path)
            except Exception:
                pass
            
            # Delete user
            request.user.delete()
            
            return JsonResponse({'success': True, 'message': 'Account deleted successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error deleting account: {str(e)}'})
    
    elif action == 'change_password':
        try:
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            if not current_password or not new_password or not confirm_password:
                return JsonResponse({'success': False, 'message': 'All password fields are required'})
            
            if new_password != confirm_password:
                return JsonResponse({'success': False, 'message': 'New password and confirmation do not match'})
            
            if len(new_password) < 8:
                return JsonResponse({'success': False, 'message': 'Password must be at least 8 characters long'})
            
            # Verify current password
            user = authenticate(request, username=request.user.username, password=current_password)
            if not user:
                return JsonResponse({'success': False, 'message': 'Current password is incorrect'})
            
            # Change password
            user.set_password(new_password)
            user.save()
            
            # Update session to keep user logged in
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            return JsonResponse({'success': True, 'message': 'Password changed successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error changing password: {str(e)}'})
    
    elif action == 'save_personal_info':
        try:
            from users.models import UserProfile
            
            # Update user fields
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.save()
            
            # Get or create UserProfile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={}
            )
            
            # Get or create SuperAdminSettings for additional fields
            from .models import SuperAdminSettings
            settings_obj, created = SuperAdminSettings.objects.get_or_create(
                user=user,
                defaults={}
            )
            
            # Update profile settings
            settings_obj.profile_phone = request.POST.get('phone', '').strip()
            settings_obj.profile_address = request.POST.get('address', '').strip()
            settings_obj.save()
            
            return JsonResponse({'success': True, 'message': 'Personal information saved successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error saving personal information: {str(e)}'})
    
    else:
        return JsonResponse({'success': False, 'message': 'Invalid action'})

@login_required(login_url='superadmin:superadmin_login')
def delete_user(request, user_id):
    if not is_admin_or_superadmin(request.user):
        return redirect('superadmin:superadmin_login')
    
    try:
        user = User.objects.get(id=user_id)
        if request.method == 'POST':
            user.delete()
            messages.success(request, f'User "{user.get_full_name() or user.username}" deleted successfully.')
            return redirect('superadmin:users_list')
        
        context = {
            'user': user,
            'sa_page': 'users'
        }
        return render(request, 'superadmin/user_delete.html', context)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('superadmin:users_list')

def _is_superadmin_user(u):



    if not u or not getattr(u, 'is_authenticated', False):



        return False



    if u.is_superuser:



        return True



    try:



        role_name = getattr(getattr(getattr(u, 'userprofile', None), 'role', None), 'name', '')



        return (role_name.lower() == 'superadmin')



    except Exception:



        return False











def admin_signup(request):



    """Allow users to sign up as Admin (not SuperAdmin)"""



    if request.method == 'POST':



        username = (request.POST.get('username') or '').strip()



        email = (request.POST.get('email') or '').strip()



        password = (request.POST.get('password') or '')



        confirm = (request.POST.get('confirm_password') or '')







        if not username:



            messages.error(request, 'Username is required.')



            return render(request, 'superadmin/admin_signup.html')



        if User.objects.filter(username=username).exists():



            messages.error(request, 'Username already taken.')



            return render(request, 'superadmin/admin_signup.html')



        if email and User.objects.filter(email=email).exists():



            messages.error(request, 'Email already in use.')



            return render(request, 'superadmin/admin_signup.html')



        if not password or password != confirm:



            messages.error(request, 'Passwords do not match.')



            return render(request, 'superadmin/admin_signup.html')







        user = User.objects.create_user(username=username, email=email, password=password)



        # Staff flag helps with admin features



        user.is_staff = True



        user.save()







        # Assign Admin role (not SuperAdmin)



        role, _ = Role.objects.get_or_create(name='Admin')



        profile, created = UserProfile.objects.get_or_create(user=user)



        profile.role = role



        profile.save()







        # Create trial subscription for admin user



        try:



            # Create a company for the admin user



            company, company_created = Company.objects.get_or_create(



                name=f'{username} Company',



                defaults={



                    'email': f'{username}@company.com',



                    'phone': '0000000000',



                    'subscription_status': 'trial',



                    'subscription_start_date': timezone.now().date(),



                    'plan_expiry_date': timezone.now().date() + timezone.timedelta(days=getattr(settings, 'FREE_TRIAL_DURATION_DAYS', 7)),



                }



            )



            



            # Get the Basic plan (fixed plan)



            basic_plan = Plan.objects.filter(name='Basic').first()



            if not basic_plan:



                # If Basic plan doesn't exist, create it as a fallback



                basic_plan = Plan.objects.create(



                    name='Basic',



                    price=199,



                    billing_cycle='monthly',



                    users=5,



                    storage='10GB',



                    status='active',



                    is_active=True



                )



            



            # Create trial subscription



            subscription, sub_created = Subscription.objects.get_or_create(



                company=company,



                defaults={



                    'plan': basic_plan,



                    'status': 'trial',



                    'start_date': timezone.now().date(),



                    'end_date': timezone.now().date() + timezone.timedelta(days=getattr(settings, 'FREE_TRIAL_DURATION_DAYS', 7)),



                    'next_billing_date': timezone.now().date() + timezone.timedelta(days=getattr(settings, 'FREE_TRIAL_DURATION_DAYS', 7)),



                    'base_price': basic_plan.price,



                    'discount_amount': 0.00,



                    'tax_amount': 0.00,



                    'total_amount': basic_plan.price,



                    'auto_renew': True,



                }



            )



            



            if sub_created:



                print(f'Trial subscription created for admin {username} with Basic plan')



            



        except Exception as e:



            print(f'Error creating trial subscription: {e}')







        messages.success(request, 'Admin account created. You can now log in.')



        return redirect('superadmin:admin_login')







    return render(request, 'superadmin/admin_signup.html')











def superadmin_signup(request):



    # Allow creating the FIRST Super Admin if none exist yet.



    # If one exists, only a logged-in Super Admin may create more.



    any_su = _has_superadmin_any()



    if any_su and not _is_superadmin_user(request.user):



        messages.error(request, 'Super Admin already exists. Only a Super Admin can create another.')



        return redirect('superadmin:superadmin_login')







    if request.method == 'POST':



        username = (request.POST.get('username') or '').strip()



        email = (request.POST.get('email') or '').strip()



        password = (request.POST.get('password') or '')



        confirm = (request.POST.get('confirm_password') or '')







        if not username:



            messages.error(request, 'Username is required.')



            return render(request, 'superadmin/signup.html')



        if User.objects.filter(username=username).exists():



            messages.error(request, 'Username already taken.')



            return render(request, 'superadmin/signup.html')



        if email and User.objects.filter(email=email).exists():



            messages.error(request, 'Email already in use.')



            return render(request, 'superadmin/signup.html')



        if not password or password != confirm:



            messages.error(request, 'Passwords do not match.')



            return render(request, 'superadmin/signup.html')







        user = User.objects.create_user(username=username, email=email, password=password)



        # Staff flag helps with admin features; not strictly required for our checks



        user.is_staff = True



        user.save()







        # Assign SuperAdmin role



        role, _ = Role.objects.get_or_create(name='SuperAdmin')



        profile, created = UserProfile.objects.get_or_create(user=user)



        profile.role = role



        profile.save()







        # Create company and trial subscription for SuperAdmin



        try:



            # Create a company for the SuperAdmin



            company, company_created = Company.objects.get_or_create(



                name=f'{username} Company',



                defaults={



                    'email': f'{username}@company.com',



                    'phone': '0000000000',



                    'subscription_status': 'trial',



                    'subscription_start_date': timezone.now().date(),



                    'plan_expiry_date': timezone.now().date() + timezone.timedelta(days=getattr(settings, 'FREE_TRIAL_DURATION_DAYS', 7)),



                }



            )



            



            # Get the Basic plan (fixed plan)



            basic_plan = Plan.objects.filter(name='Basic').first()



            if not basic_plan:



                # If Basic plan doesn't exist, create it as a fallback



                basic_plan = Plan.objects.create(



                    name='Basic',



                    price=199,



                    billing_cycle='monthly',



                    users=5,



                    storage='10GB',



                    status='active',



                    is_active=True



                )



            



            # Create trial subscription



            subscription, sub_created = Subscription.objects.get_or_create(



                company=company,



                defaults={



                    'plan': basic_plan,



                    'status': 'trial',



                    'start_date': timezone.now().date(),



                    'end_date': timezone.now().date() + timezone.timedelta(days=getattr(settings, 'FREE_TRIAL_DURATION_DAYS', 7)),



                    'next_billing_date': timezone.now().date() + timezone.timedelta(days=getattr(settings, 'FREE_TRIAL_DURATION_DAYS', 7)),



                    'base_price': basic_plan.price,



                    'discount_amount': 0.00,



                    'tax_amount': 0.00,



                    'total_amount': basic_plan.price,



                    'auto_renew': True,



                }



            )



            



            if sub_created:
                print(f'Trial subscription created for SuperAdmin {username} with Basic plan')

            
        except Exception as e:
            print(f'Error creating trial subscription for SuperAdmin: {e}')

        messages.success(request, 'Super Admin account created. You can now log in.')
        return redirect('superadmin:superadmin_login')

    return render(request, 'superadmin/signup.html')


@login_required(login_url='superadmin:superadmin_login')
def superadmin_page(request, page: str):

# ... (rest of the code remains the same)


    print(f'[DEBUG] superadmin_page called with method={request.method}, page={page}')



    



    if not is_admin_or_superadmin(request.user):



        return redirect('superadmin:superadmin_login')







    # Normalize page name (remove .html extension if present)



    page_normalized = page.replace('.html', '')
    # Handle settings page
    if page_normalized == 'settings':
        from .models import SuperAdminSettings
        from django.contrib import messages
        
        if request.method == 'POST':
            # Handle form submission
            try:
                # Get or create user settings
                user_settings, created = SuperAdminSettings.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'profile_name': request.user.get_full_name(),
                        'profile_email': request.user.email,
                        'language': 'en',
                        'timezone': 'UTC',
                        'currency': 'USD',
                    }
                )
                
                # Update settings from form data
                user_settings.profile_name = request.POST.get('profile_name', '')
                user_settings.profile_email = request.POST.get('profile_email', '')
                user_settings.profile_phone = request.POST.get('profile_phone', '')
                user_settings.profile_address = request.POST.get('profile_address', '')
                user_settings.department = request.POST.get('department', '')
                user_settings.role = request.POST.get('role', '')
                user_settings.employee_id = request.POST.get('employee_id', '')
                
                # Notification settings
                user_settings.email_notifications = request.POST.get('email_notifications') == 'on'
                user_settings.in_app_notifications = request.POST.get('in_app_notifications') == 'on'
                user_settings.push_notifications = request.POST.get('push_notifications') == 'on'
                
                # Security settings
                user_settings.two_factor_enabled = request.POST.get('two_factor_enabled') == 'on'
                user_settings.profile_visibility = request.POST.get('profile_visibility', 'public')
                
                # App settings
                user_settings.dark_mode = request.POST.get('dark_mode') == 'on'
                user_settings.language = request.POST.get('language', 'en')
                user_settings.timezone = request.POST.get('timezone', 'UTC')
                user_settings.currency = request.POST.get('currency', 'USD')
                
                # Company settings
                if request.POST.get('remove_logo') == 'true':
                    # Remove existing logo
                    user_settings.company_logo = None
                elif 'company_logo' in request.FILES:
                    # Upload new logo
                    user_settings.company_logo = request.FILES['company_logo']
                
                user_settings.company_name = request.POST.get('company_name', '')
                user_settings.website_url = request.POST.get('website_url', '')
                user_settings.contact_email = request.POST.get('contact_email', '')
                user_settings.contact_phone = request.POST.get('contact_phone', '')
                user_settings.address = request.POST.get('address', '')
                user_settings.collapsed_logo = request.POST.get('collapsed_logo') == 'on'
                
                # System settings
                user_settings.maintenance_mode = request.POST.get('maintenance_mode') == 'on'
                user_settings.user_registration = request.POST.get('user_registration') == 'on'
                user_settings.email_verification = request.POST.get('email_verification') == 'on'
                user_settings.remember_me = request.POST.get('remember_me') == 'on'
                user_settings.show_tutorial = request.POST.get('show_tutorial') == 'on'
                
                # Ticket settings
                user_settings.default_ticket_status = request.POST.get('default_ticket_status', 'Open')
                user_settings.default_ticket_priority = request.POST.get('default_ticket_priority', 'Medium')
                user_settings.auto_ticket_assignment = request.POST.get('auto_ticket_assignment') == 'on'
                user_settings.allow_ticket_reopen = request.POST.get('allow_ticket_reopen') == 'on'
                user_settings.first_response_hours = request.POST.get('first_response_hours', 24)
                user_settings.resolution_time_hours = request.POST.get('resolution_time_hours', 72)
                user_settings.sla_business_hours = request.POST.get('sla_business_hours', 'Business Hours (9 AM - 5 PM, Mon-Fri)')
                
                # UI settings
                # user_settings.theme = request.POST.get('theme', 'light')
                # user_settings.primary_color = request.POST.get('primary_color', '#0d6efd')
                # user_settings.fixed_header = request.POST.get('fixed_header') == 'on'
                # user_settings.fixed_sidebar = request.POST.get('fixed_sidebar') == 'on'
                # user_settings.collapsed_sidebar = request.POST.get('collapsed_sidebar') == 'on'
                
                user_settings.save()
                messages.success(request, 'Settings saved successfully!')
                
            except Exception as e:
                messages.error(request, f'Error saving settings: {str(e)}')
            
            # Redirect back to settings page
            return redirect('superadmin:superadmin_page', page='settings')
        
        # Handle GET request
        user_settings, created = SuperAdminSettings.objects.get_or_create(
            user=request.user,
            defaults={
                'profile_name': request.user.get_full_name(),
                'profile_email': request.user.email,
                'language': 'en',
                'timezone': 'UTC',
                'currency': 'USD',
            }
        )
        
        # Add settings to context for form population
        ctx = {}
        ctx.update({
            'site_settings': user_settings,  # Template expects site_settings
            'LANGUAGE_CHOICES': [  # Template expects LANGUAGE_CHOICES
                ('en', 'English'),
                ('es', 'Spanish'),
                ('fr', 'French'),
                ('de', 'German'),
                ('zh', 'Chinese'),
                ('ja', 'Japanese'),
            ],
            'TIMEZONE_CHOICES': [  # Template expects TIMEZONE_CHOICES
                ('UTC', 'UTC'),
                ('America/New_York', 'Eastern Time'),
                ('America/Chicago', 'Central Time'),
                ('America/Denver', 'Mountain Time'),
                ('America/Los_Angeles', 'Pacific Time'),
                ('Europe/London', 'London'),
                ('Europe/Paris', 'Paris'),
                ('Asia/Tokyo', 'Tokyo'),
                ('Asia/Shanghai', 'Shanghai'),
            ],
            'CURRENCY_CHOICES': [  # Template expects CURRENCY_CHOICES
                ('USD', 'US Dollar'),
                ('EUR', 'Euro'),
                ('GBP', 'British Pound'),
                ('JPY', 'Japanese Yen'),
                ('CNY', 'Chinese Yuan'),
                ('INR', 'Indian Rupee'),
            ],
        })
        
        # Add user profile to context for header display
        user = request.user
        profile = getattr(user, 'userprofile', None)
        ctx['user_profile'] = profile  # Add user profile for header display
        
        return render(request, 'superadmin/settings.html', ctx)
    
    # Handle all_transactions page
    elif page_normalized == 'all_transactions':
        from .models import Payment
        from django.core.paginator import Paginator
        
        payments = Payment.objects.select_related('subscription__plan', 'company').order_by('-payment_date')
        
        # Calculate transaction statistics
        total_transactions = payments.count()
        completed_transactions = payments.filter(status='completed').count()
        pending_transactions = payments.filter(status='pending').count()
        failed_transactions = payments.filter(status='failed').count()
        
        # Implement pagination with 5 records per page
        paginator = Paginator(payments, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Add user profile to context for header display
        user = request.user
        profile = getattr(user, 'userprofile', None)
        
        context = {
            'payments': page_obj,
            'all_transactions_list': page_obj,  # Template expects this variable name
            'total_transactions': total_transactions,
            'completed_transactions': completed_transactions,
            'pending_transactions': pending_transactions,
            'failed_transactions': failed_transactions,
            'sa_page': 'all_transactions',
            'user_profile': profile  # Add user profile for header display
        }
        
        return render(request, 'superadmin/all_transactions.html', context)
    
    # Handle all_subscriptions page
    elif page_normalized == 'all_subscriptions':
        from .models import Payment
        from django.utils import timezone
        from datetime import timedelta, date
        from decimal import Decimal
        from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
        
        # Auto-update expired subscriptions
        expired_count = Subscription.update_expired_subscriptions()
        if expired_count > 0:
            print(f"Auto-updated {expired_count} expired subscriptions")
        
        subscriptions = Subscription.objects.select_related('company', 'plan').order_by('-created_at')
        
        # Calculate total paid for each subscription
        subscription_list = []
        for subscription in subscriptions:
            total_paid = Payment.objects.filter(
                subscription=subscription,
                status='completed'
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            subscription.total_paid = total_paid
            subscription_list.append(subscription)
        
        # Pagination: 7 subscriptions per page
        paginator = Paginator(subscription_list, 7)
        page = request.GET.get('page')
        
        try:
            subscriptions = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page
            subscriptions = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page
            subscriptions = paginator.page(paginator.num_pages)
        
        # Calculate subscription statistics (use all subscriptions for stats, not just current page)
        all_subscriptions_query = Subscription.objects.select_related('company', 'plan').order_by('-created_at')
        total_subscriptions = all_subscriptions_query.count()
        active_subscriptions = all_subscriptions_query.filter(status='active').count()
        trial_subscriptions = all_subscriptions_query.filter(status='trial').count()
        expired_subscriptions = all_subscriptions_query.filter(status='expired').count()
        
        # Calculate monthly revenue (current month)
        current_month_start = timezone.now().date().replace(day=1)
        current_month_payments = Payment.objects.filter(
            payment_date__gte=current_month_start,
            status='completed'
        )
        monthly_revenue = current_month_payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Calculate MRR (Monthly Recurring Revenue) - sum of active subscription monthly amounts
        mrr = all_subscriptions_query.filter(status='active').aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        # Calculate churn rate (simplified - cancelled subscriptions this month / total subscriptions)
        current_month_cancellations = all_subscriptions_query.filter(
            status='cancelled',
            cancelled_at__gte=current_month_start
        ).count()
        churn_rate = (current_month_cancellations / total_subscriptions * 100) if total_subscriptions > 0 else 0
        
        # Get recent payments
        recent_payments = Payment.objects.select_related('subscription__plan', 'company').order_by('-payment_date')[:5]
        
        # Add user profile to context for header display
        user = request.user
        profile = getattr(user, 'userprofile', None)
        
        context = {
            'subscriptions': subscriptions,
            'all_subscriptions_list': subscriptions,  # Template expects this variable name
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'trial_subscriptions': trial_subscriptions,
            'expired_subscriptions': expired_subscriptions,
            'monthly_revenue': monthly_revenue,
            'mrr': mrr,
            'churn_rate': round(churn_rate, 1),
            'recent_payments': recent_payments,
            'currency_symbol': '₹',  # Default currency symbol
            'sa_page': 'all_subscriptions',
            'user_profile': profile  # Add user profile for header display
        }
        
        return render(request, 'superadmin/all_subscriptions.html', context)
    
    # Handle profile page
    elif page_normalized == 'profile':
        from .models import SuperAdminSettings
        from django.http import JsonResponse
        
        # Handle POST requests for AJAX calls
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'save_personal_info':
                # Update user profile information
                request.user.first_name = request.POST.get('first_name', '')
                request.user.last_name = request.POST.get('last_name', '')
                request.user.email = request.POST.get('email', '')
                request.user.save()
                
                # Refresh the user object to get updated data
                request.user.refresh_from_db()
                
                # Update SuperAdminSettings
                user_settings, created = SuperAdminSettings.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'profile_name': request.user.get_full_name(),
                        'profile_email': request.user.email,
                        'language': 'en',
                        'timezone': 'UTC',
                        'currency': 'USD',
                    }
                )
                
                user_settings.profile_phone = request.POST.get('phone', '')
                user_settings.profile_address = request.POST.get('address', '')
                user_settings.save()
                
                return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
            
            elif action == 'upload_profile_picture':
                # Handle profile picture upload
                if 'profile_picture' in request.FILES:
                    user_settings.profile_picture = request.FILES['profile_picture']
                    user_settings.save()
                    return JsonResponse({'success': True, 'message': 'Profile picture updated'})
                else:
                    return JsonResponse({'success': False, 'message': 'No file uploaded'})
            
            elif action == 'remove_profile_picture':
                # Handle profile picture removal
                if user_settings.profile_picture:
                    # Delete the file from storage
                    try:
                        import os
                        from django.conf import settings
                        if user_settings.profile_picture and hasattr(user_settings.profile_picture, 'path'):
                            file_path = user_settings.profile_picture.path
                            if os.path.exists(file_path):
                                os.remove(file_path)
                    except Exception:
                        pass  # Ignore file deletion errors
                    
                    # Clear the profile picture field
                    user_settings.profile_picture = None
                    user_settings.save()
                    return JsonResponse({'success': True, 'message': 'Profile picture removed successfully'})
                else:
                    return JsonResponse({'success': False, 'message': 'No profile picture to remove'})
            
            elif action == 'save_professional_info':
                # Update professional information
                user_settings, created = SuperAdminSettings.objects.get_or_create(
                    user=request.user,
                    defaults={
                        'profile_name': request.user.get_full_name(),
                        'profile_email': request.user.email,
                        'language': 'en',
                        'timezone': 'UTC',
                        'currency': 'USD',
                    }
                )
                
                user_settings.department = request.POST.get('department', '')
                user_settings.role = request.POST.get('role', '')
                user_settings.employee_id = request.POST.get('employee_id', '')
                
                # Handle join_date
                join_date = request.POST.get('join_date', '')
                if join_date:
                    from datetime import datetime
                    try:
                        user_settings.join_date = datetime.strptime(join_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass  # Keep existing value if date is invalid
                
                user_settings.skills = request.POST.get('skills', '')
                user_settings.save()
                
                return JsonResponse({'success': True, 'message': 'Professional information updated successfully'})
            
            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'})
        
        # Handle GET requests
        user_settings, created = SuperAdminSettings.objects.get_or_create(
            user=request.user,
            defaults={
                'profile_name': request.user.get_full_name(),
                'profile_email': request.user.email,
                'language': 'en',
                'timezone': 'UTC',
                'currency': 'USD',
            }
        )
        
        # Get dynamic statistics from backend
        try:
            from tickets.models import Ticket
            from superadmin.models import Company
            from users.models import Role, UserProfile
            
            # Count tickets
            total_tickets = Ticket.objects.count()
            print(f"DEBUG: Total tickets count: {total_tickets}")
            
            # Count companies  
            total_companies = Company.objects.count()
            print(f"DEBUG: Total companies count: {total_companies}")
            
            # Count users by role
            total_users = User.objects.filter(
                userprofile__role__name='User'
            ).count()
            print(f"DEBUG: Total users count: {total_users}")
            
            # Get additional statistics
            total_agents = User.objects.filter(
                userprofile__role__name='Agent'
            ).count()
            print(f"DEBUG: Total agents count: {total_agents}")
            
            total_admins = User.objects.filter(
                Q(userprofile__role__name='Admin') | Q(is_superuser=True)
            ).distinct().count()
            print(f"DEBUG: Total admins count: {total_admins}")
            
        except Exception as e:
            print(f"ERROR: Error loading profile data: {str(e)}")
            # Fallback to default values if there's an error
            total_tickets = 0
            total_companies = 0
            total_users = 0
            total_agents = 0
            total_admins = 0
        
        context = {
            'user': request.user,
            'profile_settings': user_settings,
            'total_tickets': total_tickets,
            'total_companies': total_companies, 
            'total_users': total_users,
            'total_agents': total_agents,
            'total_admins': total_admins,
            'sa_page': 'profile'
        }
        
        # Add user profile to context
        user = request.user
        profile = getattr(user, 'userprofile', None)
        context['user_profile'] = profile
        
        print(f"DEBUG: Profile context prepared: {context}")
        return render(request, 'superadmin/profile.html', context)
    
    # Handle tickets page
    elif page_normalized == 'tickets':
        # Add user profile to context
        user = request.user
        profile = getattr(user, 'userprofile', None)
        context = {
            'sa_page': 'tickets',
            'user_profile': profile
        }
        return render(request, 'superadmin/tickets.html', context)
    
    # Handle notifications page
    elif page_normalized == 'notifications':
        # Get notifications context
        notifications_context = get_notifications_context(request.user)
        
        # Add user profile to context
        user = request.user
        profile = getattr(user, 'userprofile', None)
        context = {
            'sa_page': 'notifications',
            'user_profile': profile,
            **notifications_context  # Add notifications context
        }
        return render(request, 'superadmin/notifications.html', context)
    
    # Default case - return 404 or redirect
    else:
        return render(request, 'superadmin/404.html', status=404)


@login_required(login_url='superadmin:superadmin_login')
def get_notifications_api(request):
    """API endpoint to get notifications for the current user"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        # Get notifications for the user
        notifications = Notification.get_user_notifications(request.user)
        
        # Format notifications for frontend
        formatted_notifications = []
        for notification in notifications:
            # Calculate time ago
            time_diff = timezone.now() - notification.created_at
            if time_diff.total_seconds() < 60:
                time_ago = f"{int(time_diff.total_seconds())} seconds ago"
            elif time_diff.total_seconds() < 3600:
                time_ago = f"{int(time_diff.total_seconds() / 60)} minutes ago"
            elif time_diff.total_seconds() < 86400:
                time_ago = f"{int(time_diff.total_seconds() / 3600)} hours ago"
            else:
                time_ago = f"{int(time_diff.total_seconds() / 86400)} days ago"
            
            # Map notification type to icon and color
            icon_map = {
                'info': 'bi-info-circle',
                'success': 'bi-check-circle',
                'warning': 'bi-exclamation-triangle',
                'error': 'bi-x-circle',
                'system': 'bi-gear',
                'payment': 'bi-credit-card',
                'subscription': 'bi-box-arrow-in-right',
                'user': 'bi-person'
            }
            
            color_map = {
                'info': '#3b82f6',
                'success': '#10b981',
                'warning': '#f59e0b',
                'error': '#ef4444',
                'system': '#6b7280',
                'payment': '#f59e0b',
                'subscription': '#8b5cf6',
                'user': '#10b981'
            }
            
            formatted_notifications.append({
                'id': notification.id,
                'type': notification.notification_type,
                'title': notification.title,
                'message': notification.message,
                'time': time_ago,
                'timestamp': notification.created_at.isoformat(),
                'unread': not notification.is_read,
                'priority': notification.priority in ['high', 'urgent'],
                'icon': icon_map.get(notification.notification_type, 'bi-bell'),
                'color': color_map.get(notification.notification_type, '#6b7280'),
                'action_url': notification.action_url,
                'action_text': notification.action_text
            })
        
        # Get unread count
        unread_count = Notification.get_user_notifications(request.user, unread_only=True).count()
        
        return JsonResponse({
            'success': True,
            'notifications': formatted_notifications,
            'unread_count': unread_count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required(login_url='superadmin:superadmin_login')
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id,
            is_active=True
        )
        
        # Check if notification belongs to user or is broadcast
        if notification.user and notification.user != request.user:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        
        notification.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required(login_url='superadmin:superadmin_login')
@require_POST
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        notification = get_object_or_404(
            Notification, 
            id=notification_id,
            is_active=True
        )
        
        # Check if notification belongs to user or is broadcast
        if notification.user and notification.user != request.user:
            return JsonResponse({'error': 'Forbidden'}, status=403)
        
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required(login_url='superadmin:superadmin_login')
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    if not is_admin_or_superadmin(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        # Get all unread notifications for user
        unread_notifications = Notification.get_user_notifications(request.user, unread_only=True)
        
        # Mark all as read
        count = 0
        for notification in unread_notifications:
            notification.mark_as_read()
            count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Marked {count} notifications as read',
            'count': count
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required(login_url='superadmin:superadmin_login')
def transaction_receipt(request, payment_id):
    """Generate and download transaction receipt"""
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Get user settings for currency
        from .models import SuperAdminSettings
        user_settings, _ = SuperAdminSettings.objects.get_or_create(
            user=request.user,
            defaults={'currency': 'INR'}
        )
        currency_symbol = user_settings.get_currency_symbol_display()
        
        # For now, return a simple response. In production, generate PDF
        from django.http import HttpResponse
        import datetime
        
        receipt_content = f"""
        Receipt for Transaction {payment.transaction_id or payment.id}
        
        Company: {payment.company.name}
        Amount: {currency_symbol}{payment.amount}
        Payment Method: {payment.get_payment_method_display()}
        Payment Type: {payment.get_payment_type_display()}
        Status: {payment.get_status_display()}
        Date: {payment.payment_date.strftime('%Y-%m-%d %H:%M:%S')}
        Invoice Number: {payment.invoice_number or 'N/A'}
        """
        
        response = HttpResponse(receipt_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="receipt_{payment.transaction_id or payment.id}.txt"'
        return response
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
