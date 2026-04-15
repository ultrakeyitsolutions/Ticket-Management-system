from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Subscription management
    path('current/', views.get_user_subscription, name='get_user_subscription'),
    path('upgrade/<int:plan_id>/', views.upgrade_plan, name='upgrade_plan'),
    path('cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('history/', views.subscription_history, name='subscription_history'),
    path('check-status/', views.check_subscription_status, name='check_subscription_status'),
    
    # Plans list
    path('plans-list/', views.get_plans_list, name='get_plans_list'),
    
    # Razorpay payment processing
    path('create-payment-order/', views.create_payment_order, name='create_payment_order'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    
    # Payment callbacks (legacy)
    path('payment-callback/<str:payment_id>/', views.payment_callback, name='payment_callback'),
]
