from django.urls import path
from . import views
from .views import (
    DashboardStatsView,
    RecentTicketsView,
    TicketListCreateView,
    TicketStatusUpdateView,
    MutedChatView,
    TicketCommentListCreateView,
    TicketCommentDetailView,
    ChatAttachmentView,
    ChatAttachmentDeleteView,
)

urlpatterns = [
    # -----------------------------------------------------------------
    # Ticket CRUD  –  ticket_id is a string like "TCKT-DF01E584"
    # -----------------------------------------------------------------
    path("", views.ticket_list, name="ticket_list"),
    path("create/", views.ticket_create, name="ticket_create"),
    path("<str:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("<str:ticket_id>/edit/", views.ticket_edit, name="ticket_edit"),
    path("<str:ticket_id>/delete/", views.ticket_delete, name="ticket_delete"),

    # -----------------------------------------------------------------
    # Comment API  –  ticket_id is the same string slug
    # -----------------------------------------------------------------
    path("<str:ticket_id>/comments/", TicketCommentListCreateView.as_view(), name="api-ticket-comments"),
    path("<str:ticket_id>/comments/<int:comment_id>/", TicketCommentDetailView.as_view(), name="api-ticket-comment-detail"),

    # -----------------------------------------------------------------
    # Dashboard & general API endpoints
    # -----------------------------------------------------------------
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("dashboard/recent-tickets/", RecentTicketsView.as_view(), name="recent-tickets"),
    path("api/tickets/", TicketListCreateView.as_view(), name="api-tickets"),
    path("api/tickets/<int:pk>/status/", TicketStatusUpdateView.as_view(), name="api-ticket-status"),
    path("api/chat/mute/", MutedChatView.as_view(), name="api-chat-mute"),

    # -----------------------------------------------------------------
    # Chat attachments
    # -----------------------------------------------------------------
    path("chat/attachment/<int:attachment_id>/", ChatAttachmentView.as_view(), name="chat-attachment"),
    path("chat/attachment/<int:attachment_id>/delete/", ChatAttachmentDeleteView.as_view(), name="chat-attachment-delete"),
]