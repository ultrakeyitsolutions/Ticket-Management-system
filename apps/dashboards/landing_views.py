"""
Simple landing page view to avoid syntax errors in main views.py
"""
from django.shortcuts import render

def landing_page(request):
    """
    Landing page view with dynamic pricing from database
    """
    # Import models dynamically to avoid conflicts
    from superadmin.models import Plan, Company, Subscription
    
    plans = Plan.objects.all().order_by('price')
    
    # Check usage status for each plan
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
    
    return render(request, 'landingpage/index.html', {
        'plans_with_status': plans_with_status,
    })
