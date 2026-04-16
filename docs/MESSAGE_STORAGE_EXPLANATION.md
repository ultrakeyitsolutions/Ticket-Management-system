# Message Storage Explanation

## Overview
When you send a message from the agent dashboard profile page, the message is stored in the **database** using Django's ORM (Object-Relational Mapping).

## Storage Location

### **Database Table: `tickets_chatmessage`**

The message is stored as a record in the `ChatMessage` model, which creates a database table named `tickets_chatmessage`.

### **Model Structure**
```python
class ChatMessage(models.Model):
    """Simple direct message between two users (used for user/admin chat)."""
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    ticket_id = models.CharField(max_length=50, blank=True, null=True)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Message Flow

### **1. User Action**
- You click "Message" button on agent profile
- Select recipient type (Admin, Customer, or Agent)
- Type message content
- Click "Send Message"

### **2. Frontend Processing**
```javascript
// JavaScript sends POST request to:
fetch('/dashboard/agent-dashboard/send-message/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
        recipient: 'admin|user|agent',  // Selected recipient type
        message: 'Your message content'  // Message text
    })
})
```

### **3. Backend Processing**
```python
# In apps/dashboards/views.py - send_message() function:
@login_required
def send_message(request):
    # 1. Parse request data
    data = json.loads(request.body)
    recipient_type = data.get('recipient', '').lower()
    message_content = data.get('message', '').strip()
    
    # 2. Find recipient user based on type
    if recipient_type == 'admin':
        recipient = User.objects.filter(
            Q(is_superuser=True) | Q(is_staff=True)
        ).first()
    elif recipient_type == 'user':
        recipient = User.objects.filter(
            Q(is_superuser=False) & Q(is_staff=False)
        ).first()
    elif recipient_type == 'agent':
        recipient = User.objects.filter(
            Q(is_staff=True) & ~Q(id=request.user.id)
        ).first()
    
    # 3. Create message record in database
    chat_message = ChatMessage.objects.create(
        sender=request.user,           # Current logged-in agent
        recipient=recipient,           # Found recipient user
        text=message_content,          # Message text
        ticket_id=None,               # No ticket for profile messages
    )
```

## Database Record Details

### **What Gets Stored:**

| Field | Value | Description |
|-------|-------|-------------|
| `id` | Auto-generated | Unique message ID (e.g., 123) |
| `sender_id` | Current user's ID | The agent who sent the message |
| `recipient_id` | Found recipient's ID | The user who receives the message |
| `ticket_id` | `NULL` | No associated ticket for profile messages |
| `text` | Your message content | The actual message text |
| `is_read` | `False` | Message starts as unread |
| `created_at` | Current timestamp | When the message was sent |

### **Example Database Record:**
```sql
INSERT INTO tickets_chatmessage (
    sender_id, recipient_id, ticket_id, text, is_read, created_at
) VALUES (
    5,           -- agent_id (sender)
    1,           -- admin_id (recipient) 
    NULL,        -- no ticket
    "Hello, I need assistance with a customer issue.",  -- message text
    FALSE,       -- unread
    "2026-04-09 16:55:00"  -- timestamp
);
```

## Message Retrieval

### **How Recipients See Messages:**

1. **Notification System**: Messages appear in recipient's notification panel
2. **Chat Interface**: Messages can be viewed in the chat system
3. **Database Queries**: Recipients can query their received messages

```python
# Recipient can retrieve their messages:
received_messages = ChatMessage.objects.filter(
    recipient=request.user,
    is_read=False
).order_by('-created_at')
```

## Recipient Resolution

### **How Recipients Are Determined:**

| Selection | Database Query | Result |
|-----------|----------------|--------|
| "System Administrator" | `User.objects.filter(Q(is_superuser=True) \| Q(is_staff=True)).first()` | First admin/superuser |
| "Customer Support" | `User.objects.filter(Q(is_superuser=False) & Q(is_staff=False)).first()` | First regular user |
| "Another Agent" | `User.objects.filter(Q(is_staff=True) & ~Q(id=current_user_id)).first()` | First other agent |

## Message Persistence

### **Storage Duration:**
- **Permanent**: Messages are stored permanently in the database
- **No Expiration**: Messages don't auto-delete
- **Backup**: Included in database backups

### **Access Control:**
- **Sender**: Can see their own sent messages
- **Recipient**: Can see messages sent to them
- **Admin**: Can see all messages (with proper permissions)

## Technical Details

### **Database Table Name:** `tickets_chatmessage`
### **App:** `tickets`
### **Model:** `ChatMessage`
### **View:** `send_message()` in `apps/dashboards/views.py`
### **URL:** `/dashboard/agent-dashboard/send-message/`

## Summary

When you send a message:
1. **Frontend** sends data to backend API
2. **Backend** finds appropriate recipient user
3. **Database** creates new `ChatMessage` record
4. **Recipient** can access message through notifications/chat
5. **Message** persists permanently in database

The message is **real** and **persistent** - it's stored in the database and can be retrieved by the recipient at any time.
