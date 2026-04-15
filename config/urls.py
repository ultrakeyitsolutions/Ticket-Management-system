from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from dashboards.views import landing_page, user_dashboard_page  # ← fixed imports
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', landing_page, name='home'),
    path('test-password/', TemplateView.as_view(template_name='test_password.html'), name='test_password'),
    path('ticket-dashboard/<str:page>/', user_dashboard_page, name='ticket_dashboard_page'),  # ← fixed view
    path('ticket-dashboard/', TemplateView.as_view(template_name='admindashboard/index.html'), name='ticket_dashboard'),
    path('admin/', admin.site.urls),
    path('api/', include(('api.urls', 'api'), namespace='api')),
    path("", include(('users.urls', 'users'), namespace='users')),
    path("dashboard/", include(('dashboards.urls', 'dashboards'), namespace='dashboards')),
    path("tickets/", include(("tickets.urls", 'tickets'), namespace='tickets')),
    path('superadmin/', include(('superadmin.urls', 'superadmin'), namespace='superadmin')),
    path('payments/', include(('payments.urls', 'payments'), namespace='payments')),
    path('subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),
    path('', include(('core.urls', 'core'), namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)