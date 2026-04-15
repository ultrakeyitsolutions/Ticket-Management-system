from django.contrib import admin
from .models import UserSubscription, SubscriptionHistory, PaymentTransaction


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'company', 'plan', 'status', 'start_date', 'end_date', 'is_active']
    list_filter = ['status', 'plan', 'is_active', 'start_date']
    search_fields = ['user__username', 'company__name', 'plan__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'company', 'plan', 'status', 'is_active')
        }),
        ('Dates', {
            'fields': ('start_date', 'end_date', 'trial_end_date')
        }),
        ('Payment Information', {
            'fields': ('payment_id', 'payment_amount', 'payment_method', 'paid_at', 'auto_renew')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'action', 'old_plan', 'new_plan', 'payment_amount', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['subscription__user__username', 'action']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'subscription__user', 'old_plan', 'new_plan'
        )


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription', 'plan', 'payment_id', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'gateway', 'created_at']
    search_fields = ['user__username', 'payment_id']
    readonly_fields = ['created_at', 'completed_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('user', 'subscription', 'plan', 'payment_id', 'amount', 'currency', 'status')
        }),
        ('Payment Gateway', {
            'fields': ('gateway', 'gateway_response')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
