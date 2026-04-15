// User Dashboard Notifications JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize notifications
    loadNotifications();
    updateUnreadBadge();
    
    // Set up filter tabs
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filter = this.dataset.filter;
            setActiveFilter(filter);
            loadNotifications(filter);
        });
    });
    
    // Set up action buttons
    const markAllReadBtn = document.getElementById('markAllRead');
    const clearAllBtn = document.getElementById('clearAll');
    
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', markAllAsRead);
    }
    
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', clearAllNotifications);
    }
});

// ── Helper Functions ──

function setActiveFilter(filter) {
    document.querySelectorAll('.filter-btn').forEach(t => t.classList.remove('active'));
    const clickedTab = document.querySelector(`[data-filter="${filter}"]`);
    if (clickedTab) clickedTab.classList.add('active');
}

/* ── Load notifications from backend ── */
async function loadNotifications(type = 'all', page = 1) {
    try {
        const response = await fetch(`/dashboard/user-dashboard/api/notifications/?type=${type}&page=${page}&per_page=20`);
        const data = await response.json();
        if (data.success) {
            renderNotifications(data.notifications);
            updatePagination(data.pagination);
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
        showToast('Error loading notifications', 'error');
    }
}

/* ── Render notifications in template ── */
function renderNotifications(notifications) {
    const container = document.getElementById('notificationList');
    const emptyState = document.getElementById('notificationEmptyState');
    
    if (!container) return;
    
    if (notifications.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }
    
    emptyState.classList.add('hidden');
    
    // Group notifications by date
    const groupedNotifications = groupNotificationsByDate(notifications);
    
    let html = '';
    for (const [date, group] of Object.entries(groupedNotifications)) {
        html += `
            <div class="notification-group">
                <h3 class="notification-date">${date}</h3>
                ${group.map(n => createNotificationHTML(n)).join('')}
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    // Add event listeners to new notification elements
    container.querySelectorAll('.notification-item').forEach(item => {
        const markReadBtn = item.querySelector('.mark-read-btn');
        if (markReadBtn) {
            markReadBtn.addEventListener('click', function() {
                const notificationId = this.dataset.notificationId;
                markAsRead(notificationId, this);
            });
        }
    });
}

/* ── Create notification HTML ── */
function createNotificationHTML(notification) {
    const categoryClass = notification.notification_type || 'system';
    const iconClass = getIconClass(notification.notification_type);
    const unreadClass = notification.is_read ? '' : 'unread';
    
    return `
        <div class="notification-item ${unreadClass}" data-type="${categoryClass}">
            <div class="notification-icon">
                <i class="${iconClass}"></i>
            </div>
            <div class="notification-content">
                <p class="notification-text">
                    ${notification.message}
                    <span class="notification-time">${formatTimeAgo(notification.created_at)}</span>
                </p>
                ${notification.action_url ? `
                    <div class="notification-actions">
                        <a href="${notification.action_url}" class="action-btn">${notification.action_text || 'View'}</a>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

/* ── Group notifications by date ── */
function groupNotificationsByDate(notifications) {
    const grouped = {};
    
    notifications.forEach(notification => {
        const date = formatDate(notification.created_at);
        if (!grouped[date]) {
            grouped[date] = [];
        }
        grouped[date].push(notification);
    });
    
    return grouped;
}

/* ── Format date ── */
function formatDate(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) {
        return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Yesterday';
    } else {
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
    }
}

/* ── Format time ago ── */
function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 1) {
        return 'Just now';
    } else if (diffMins < 60) {
        return `${diffMins} min ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hours ago`;
    } else {
        return `${diffDays} days ago`;
    }
}

/* ── Get icon class ── */
function getIconClass(type) {
    const iconMap = {
        'ticket': 'fas fa-ticket-alt',
        'system': 'fas fa-bell',
        'alert': 'fas fa-exclamation-triangle',
        'user': 'fas fa-user',
        'performance': 'fas fa-chart-line'
    };
    return iconMap[type] || 'fas fa-bell';
}

/* ── Mark single item as read ── */
async function markAsRead(notificationId, button) {
    try {
        const response = await fetch(`/dashboard/user-dashboard/api/notifications/${notificationId}/mark-read/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();
        if (data.success) {
            const item = button.closest('.notification-item');
            item.classList.remove('unread');
            updateUnreadBadge();
            showToast('Notification marked as read', 'success');
        }
    } catch (error) {
        console.error('Error marking notification as read:', error);
        showToast('Error marking notification as read', 'error');
    }
}

/* ── Mark all as read ── */
async function markAllAsRead() {
    try {
        const response = await fetch('/dashboard/user-dashboard/api/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();
        if (data.success) {
            // Reload notifications to show updated state
            loadNotifications();
            showToast('All notifications marked as read', 'success');
        }
    } catch (error) {
        console.error('Error marking all as read:', error);
        showToast('Error marking all as read', 'error');
    }
}

/* ── Clear all notifications ── */
async function clearAllNotifications() {
    if (!confirm('Are you sure you want to clear all notifications?')) return;
    
    try {
        const response = await fetch('/dashboard/user-dashboard/api/notifications/clear-all/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json',
            }
        });
        const data = await response.json();
        if (data.success) {
            const list = document.getElementById('notificationList');
            list.innerHTML = `
                <div class="notification-empty" id="notificationEmptyState">
                    <div class="notification-empty__icon"><i class="fa-regular fa-bell"></i></div>
                    <div class="notification-empty__text">No notifications</div>
                </div>
            `;
            updateUnreadBadge();
            showToast('All notifications cleared', 'success');
        }
    } catch (error) {
        console.error('Error clearing notifications:', error);
        showToast('Error clearing notifications', 'error');
    }
}

/* ── Update unread badge ── */
async function updateUnreadBadge() {
    try {
        const response = await fetch('/dashboard/user-dashboard/api/notifications/?type=unread');
        const data = await response.json();
        if (data.success) {
            const count = data.counts.unread;
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'inline-block' : 'none';
            }
        }
    } catch (error) {
        console.error('Error updating badge:', error);
    }
}

/* ── Update pagination ── */
function updatePagination(pagination) {
    // User dashboard currently doesn't have pagination UI
    // This can be added later if needed
}

/* ── Toast notification ── */
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast-message');
    existingToasts.forEach(toast => toast.remove());
    
    // Create new toast
    const toast = document.createElement('div');
    toast.className = `toast-message ${type}`;
    toast.textContent = message;
    
    // Add to page
    document.body.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/* ── Get CSRF token ── */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}
