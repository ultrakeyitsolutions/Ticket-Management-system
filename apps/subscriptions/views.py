import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from superadmin.models import Plan, Company
from users.models import UserProfile
from .models import UserSubscription, SubscriptionHistory, PaymentTransaction
import uuid
import hashlib


@login_required
def get_user_subscription(request):
    """Get current user's subscription details"""
    try:
        user_profile = request.user.userprofile
        if not user_profile.company:
            return JsonResponse({'error': 'No company found'}, status=404)
        
        subscription = UserSubscription.objects.filter(
            user=request.user,
            company=user_profile.company,
            is_active=True
        ).first()
        
        if not subscription:
            return JsonResponse({'error': 'No subscription found'}, status=404)
        
        response_data = {
            'subscription_id': subscription.id,
            'plan_name': subscription.plan.name,
            'plan_price': float(subscription.plan.price),
            'billing_cycle': subscription.plan.billing_cycle,
            'status': subscription.status,
            'start_date': subscription.start_date.isoformat(),
            'end_date': subscription.end_date.isoformat(),
            'is_trial_active': subscription.is_trial_active(),
            'trial_days_remaining': subscription.trial_days_remaining(),
            'days_until_expiry': subscription.days_until_expiry(),
            'tickets_limit': subscription.plan.tickets,
            'storage_limit': subscription.plan.storage,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def upgrade_plan(request, plan_id):
    """Upgrade user's plan"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get plan
        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
        
        # Get user profile and company
        user_profile = request.user.userprofile
        if not user_profile.company:
            return JsonResponse({'error': 'No company found'}, status=404)
        
        company = user_profile.company
        
        # Get current subscription
        current_subscription = UserSubscription.objects.filter(
            user=request.user,
            company=company,
            is_active=True
        ).first()
        
        # Check if user is trying to upgrade to same plan
        if current_subscription and current_subscription.plan.id == plan.id:
            return JsonResponse({'error': 'You are already subscribed to this plan'}, status=400)
        
        # Create payment transaction
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            subscription=current_subscription or Subscription.objects.create(
                user=request.user,
                company=company,
                plan=plan,
                start_date=timezone.now(),
                end_date=timezone.now(),
                status='pending'
            ),
            plan=plan,
            payment_id=payment_id,
            amount=plan.price,
            currency='INR',
            status='pending'
        )
        
        # For now, simulate payment completion (in real app, integrate with Razorpay)
        # Return payment details for frontend
        response_data = {
            'payment_id': payment_id,
            'amount': float(plan.price),
            'currency': 'INR',
            'plan_name': plan.name,
            'billing_cycle': plan.billing_cycle,
            'redirect_url': f'/dashboard/user-dashboard/subscription-plans/',
            'callback_url': f'/subscriptions/payment-callback/{payment_id}/'
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def payment_callback(request, payment_id):
    """Handle payment callback from payment gateway"""
    try:
        transaction = get_object_or_404(PaymentTransaction, payment_id=payment_id)
        
        # In real implementation, verify payment with Razorpay
        # For now, simulate successful payment
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.gateway_response = {
            'status': 'success',
            'payment_id': payment_id,
            'amount': float(transaction.amount),
        }
        transaction.save()
        
        # Activate subscription
        subscription = transaction.subscription
        old_plan = subscription.plan
        subscription.plan = transaction.plan
        subscription.activate_subscription(
            payment_id=payment_id,
            payment_amount=transaction.amount
        )
        
        # Update company
        company = subscription.company
        company.plan = transaction.plan
        company.subscription_status = 'active'
        company.plan_expiry_date = subscription.end_date.date()
        company.save()
        
        # Create subscription history
        SubscriptionHistory.objects.create(
            subscription=subscription,
            action='payment_received',
            old_plan=old_plan if old_plan.id != transaction.plan.id else None,
            new_plan=transaction.plan,
            payment_amount=transaction.amount,
            payment_id=payment_id,
            description=f'Plan upgraded to {transaction.plan.name}'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Payment successful! Your plan has been upgraded.',
            'redirect_url': '/dashboard/user-dashboard/subscription-plans/'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def cancel_subscription(request):
    """Cancel user's subscription"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        user_profile = request.user.userprofile
        if not user_profile.company:
            return JsonResponse({'error': 'No company found'}, status=404)
        
        subscription = UserSubscription.objects.filter(
            user=request.user,
            company=user_profile.company,
            is_active=True
        ).first()
        
        if not subscription:
            return JsonResponse({'error': 'No active subscription found'}, status=404)
        
        # Cancel subscription
        subscription.cancel_subscription()
        
        # Update company
        company = subscription.company
        company.subscription_status = 'cancelled'
        company.save()
        
        # Create subscription history
        SubscriptionHistory.objects.create(
            subscription=subscription,
            action='cancelled',
            old_plan=subscription.plan,
            description=f'Subscription cancelled by {request.user.username}'
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Subscription cancelled successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def subscription_history(request):
    """Get user's subscription history"""
    try:
        user_profile = request.user.userprofile
        if not user_profile.company:
            return JsonResponse({'error': 'No company found'}, status=404)
        
        history = SubscriptionHistory.objects.filter(
            subscription__user=request.user,
            subscription__company=user_profile.company
        ).order_by('-created_at')
        
        history_data = []
        for item in history:
            history_data.append({
                'action': item.action,
                'old_plan': item.old_plan.name if item.old_plan else None,
                'new_plan': item.new_plan.name if item.new_plan else None,
                'payment_amount': float(item.payment_amount) if item.payment_amount else None,
                'description': item.description,
                'created_at': item.created_at.isoformat(),
            })
        
        return JsonResponse({'history': history_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_plans_list(request):
    """Get list of available plans for payment modal"""
    try:
        from superadmin.models import Plan
        
        plans = Plan.objects.filter(is_active=True).order_by('price')
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                'id': plan.id,
                'name': plan.name,
                'price': float(plan.price),
                'billing_cycle': plan.billing_cycle,
                'tickets': plan.tickets,
                'storage': plan.storage,
                'is_active': plan.is_active
            })
        
        return JsonResponse({'plans': plans_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def create_payment_order(request):
    """Create Razorpay payment order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        import razorpay
        from django.conf import settings
        
        # Get form data
        plan_id = request.POST.get('plan_id')
        amount = request.POST.get('amount')
        
        if not plan_id or not amount:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Get plan details
        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
        
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Create order
        order_data = {
            'amount': int(amount),  # Amount in paise
            'currency': 'INR',
            'receipt': f'receipt_{plan_id}_{request.user.id}',
            'notes': {
                'user_id': request.user.id,
                'plan_id': plan_id,
                'plan_name': plan.name,
                'billing_cycle': plan.billing_cycle
            }
        }
        
        order = client.order.create(data=order_data)
        
        return JsonResponse({
            'key_id': settings.RAZORPAY_KEY_ID,
            'amount': order['amount'],
            'currency': order['currency'],
            'order_id': order['id'],
            'company_name': 'Ticket Management System',
            'description': f'{plan.name} - {plan.billing_cycle}',
            'plan_id': plan_id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def verify_payment(request):
    """Verify Razorpay payment and activate subscription"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        import razorpay
        from django.conf import settings
        
        # Get payment data
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        plan_id = request.POST.get('plan_id')
        
        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, plan_id]):
            return JsonResponse({'error': 'Missing payment details'}, status=400)
        
        # Verify payment signature
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return JsonResponse({'success': False, 'error': 'Payment verification failed'}, status=400)
        
        # Get plan details
        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
        
        # Get user profile and company
        user_profile = request.user.userprofile
        if not user_profile.company:
            return JsonResponse({'error': 'No company found'}, status=404)
        
        company = user_profile.company
        
        # Get or create subscription
        subscription = UserSubscription.objects.filter(
            user=request.user,
            company=company,
            is_active=True
        ).first()
        
        if not subscription:
            subscription = UserSubscription.objects.create(
                user=request.user,
                company=company,
                plan=plan,
                start_date=timezone.now(),
                end_date=timezone.now(),
                status='pending'
            )
        
        # Activate subscription
        old_plan = subscription.plan
        subscription.plan = plan
        subscription.activate_subscription(
            payment_id=razorpay_payment_id,
            payment_amount=float(plan.price)
        )
        
        # Update company
        company.plan = plan
        company.subscription_status = 'active'
        company.plan_expiry_date = subscription.end_date.date()
        company.save()
        
        # Create payment transaction
        PaymentTransaction.objects.create(
            user=request.user,
            subscription=subscription,
            plan=plan,
            payment_id=razorpay_payment_id,
            amount=plan.price,
            currency='INR',
            status='completed',
            gateway='razorpay',
            gateway_response={
                'order_id': razorpay_order_id,
                'payment_id': razorpay_payment_id,
                'signature': razorpay_signature
            },
            completed_at=timezone.now()
        )
        
        # Create subscription history
        SubscriptionHistory.objects.create(
            subscription=subscription,
            action='payment_received',
            old_plan=old_plan if old_plan.id != plan.id else None,
            new_plan=plan,
            payment_amount=plan.price,
            payment_id=razorpay_payment_id,
            description=f'Plan upgraded to {plan.name} via Razorpay'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Payment successful! Your subscription has been activated.',
            'plan_name': plan.name,
            'plan_price': float(plan.price)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def check_subscription_status(request):
    """Check if user has active subscription (for middleware)"""
    try:
        user_profile = request.user.userprofile
        if not user_profile.company:
            return JsonResponse({'has_subscription': False})
        
        subscription = UserSubscription.objects.filter(
            user=request.user,
            company=user_profile.company,
            is_active=True
        ).first()
        
        if not subscription:
            return JsonResponse({'has_subscription': False})
        
        # Check if subscription is expired
        if subscription.status == 'active' and subscription.end_date < timezone.now():
            subscription.expire_subscription()
            return JsonResponse({'has_subscription': False})
        
        # Check if trial is expired
        if subscription.status == 'trial' and subscription.trial_end_date < timezone.now():
            subscription.expire_subscription()
            return JsonResponse({'has_subscription': False})
        
        return JsonResponse({
            'has_subscription': True,
            'status': subscription.status,
            'plan_name': subscription.plan.name,
            'days_remaining': subscription.days_until_expiry(),
            'is_trial': subscription.status == 'trial'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
