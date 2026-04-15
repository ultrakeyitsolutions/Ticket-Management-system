from django.urls import path
from . import views

app_name = "dashboards"

urlpatterns = [
    # Admin API
    path('admin-dashboard/api/notifications/', views.admin_notifications_api, name='admin_notifications_api'),
    path('admin-dashboard/api/notifications/mark-all-read/', views.admin_notifications_mark_all_read_api, name='admin_notifications_mark_all_read_api'),
    path('admin-dashboard/api/notifications/<uuid:notification_id>/delete/', views.admin_notification_delete_api, name='admin_notification_delete_api'),
    path('admin-dashboard/api/notifications/clear-all/', views.admin_notifications_clear_all_api, name='admin_notifications_clear_all_api'),
    path('admin-dashboard/api/ticket-volume/', views.admin_ticket_volume_api, name='admin_ticket_volume_api'),
    path('admin-dashboard/api/ratings-trends/', views.admin_ratings_trends_api, name='admin_ratings_trends_api'),
    path('admin-dashboard/api/agents-by-department/', views.get_agents_by_department, name='get_agents_by_department'),
    path('admin-dashboard/reports/export/<str:export_format>/', views.admin_reports_export, name='admin_reports_export'),

    # Agent API
    path('agent-dashboard/api/notifications/', views.agent_notifications_api, name='agent_notifications_api'),
    path('agent-dashboard/api/notifications/mark-all-read/', views.agent_mark_all_notifications_read, name='agent_mark_all_notifications_read'),
    path('agent-dashboard/api/mark-chat-read/<str:message_id>/', views.mark_chat_message_read, name='mark_chat_message_read'),
    path('agent-dashboard/api/export-reports/', views.agent_export_reports_api, name='agent_export_reports_api'),

    # User API
    path('user-dashboard/api/notifications/', views.user_notifications_api, name='user_notifications_api'),
    path('user-dashboard/api/notifications/<uuid:notification_id>/mark-read/', views.user_notification_mark_read_api, name='user_notification_mark_read_api'),
    path('user-dashboard/api/notifications/mark-all-read/', views.user_notifications_mark_all_read_api, name='user_notifications_mark_all_read_api'),
    path('user-dashboard/api/notifications/<uuid:notification_id>/delete/', views.user_notification_delete_api, name='user_notification_delete_api'),
    path('user-dashboard/api/notifications/clear-all/', views.user_notifications_clear_all_api, name='user_notifications_clear_all_api'),
    path('user-dashboard/faq/search/', views.faq_search_api, name='faq_search_api'),

    # Site Settings API
    path('api/site-settings/', views.SiteSettingsAPIView.as_view(), name='site_settings_api'),
    
    # Admin Settings (dedicated view)
    path('admin-dashboard/settings/', views.admin_settings_view, name='admin_settings'),

    # Dashboard home
    path('', views.dashboard_home, name='dashboard_home'),

    # Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/payment/', views.admin_payment_page, name='admin_payment_page'),
    path('admin-dashboard/ticket/<str:identifier>/', views.admin_ticket_detail, name='admin_ticket_detail'),
    path('admin-dashboard/ticket/<str:identifier>/edit/', views.admin_ticket_edit, name='admin_ticket_edit'),
    path('admin-dashboard/<path:page>/', views.admin_dashboard_page, name='admin_dashboard_page'),

    # Agent Dashboard
    path('agent-dashboard/', views.agent_dashboard, name='agent_dashboard'),
    path('agent-dashboard/index.html', views.agent_dashboard, name='agent_dashboard_index'),
    path('agent-dashboard/ticket/<str:identifier>/', views.agent_ticket_detail, name='agent_ticket_detail'),
    path('agent-dashboard/ticket/<str:identifier>/json/', views.agent_ticket_detail_json, name='agent_ticket_detail_json'),

    # Agent Ratings export (standalone view)
    path('agent-dashboard/export-ratings/', views.export_ratings, name='export_ratings'),

    # Agent rating trends API
    path('agent-dashboard/get-rating-trends/', views.get_rating_trends, name='get_rating_trends'),

    # Agent skills
    path('agent-dashboard/save-skills/', views.save_skills, name='save_skills'),
    path('agent-dashboard/get-skills/', views.get_skills, name='get_skills'),
    
    # Agent messaging
    path('agent-dashboard/send-message/', views.send_message, name='send_message'),

    # Agent dashboard pages — ratings page gets its own dedicated view
    path('agent-dashboard/ratings.html', views.agent_ratings_page, name='agent_ratings_page'),
    path('agent-dashboard/ratings', views.agent_ratings_page, name='agent_ratings_page_no_ext'),

    # Agent dashboard pages (generic)
    path('agent-dashboard/<path:page>.html', views.agent_dashboard_page, name='agent_dashboard_page'),
    path('agent-dashboard/<path:page>', views.agent_dashboard_page, name='agent_dashboard_page_partial'),

    # User Dashboard
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('user-dashboard/ticket/<str:identifier>/', views.user_ticket_detail, name='user_ticket_detail'),
    path('user-dashboard/ticket/<str:identifier>/edit/', views.user_ticket_edit, name='user_ticket_edit'),
    path('user-dashboard/ticket/<str:identifier>/rate/', views.user_ticket_rate, name='user_ticket_rate'),
    path('user-dashboard/ticket/<str:identifier>/delete/', views.user_ticket_delete, name='user_ticket_delete'),
    path('user-dashboard/clear-payment-modal/', views.clear_payment_modal, name='clear_payment_modal'),
    path('user-dashboard/record-payment-transaction/', views.record_payment_transaction, name='record_payment_transaction'),
    path('user-dashboard/<str:page>/', views.user_dashboard_page, name='user_dashboard_page'),

    # Test
    path('test-edit/', views.test_edit_page, name='test_edit_page'),
]
