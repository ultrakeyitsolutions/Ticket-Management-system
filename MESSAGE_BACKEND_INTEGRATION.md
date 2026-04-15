# Message Backend Integration

## Overview
The agent dashboard profile page message functionality has been successfully connected to the backend system. Messages are now stored in the database and can be viewed by recipients.

## Implementation Details

### 1. Backend Components

#### URL Endpoint
- **Path**: `/dashboard/agent-dashboard/send-message/`
- **Method**: POST
- **Authentication**: Required (login_required)
- **View Function**: `send_message()` in `apps/dashboards/views.py`

#### Database Model
Uses the existing `ChatMessage` model from `apps/tickets/models.py`:
```python
class ChatMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    ticket_id = models.CharField(max_length=50, blank=True, null=True)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### View Function Logic
1. **Validation**: Checks for required fields (recipient, message)
2. **Recipient Resolution**: Finds appropriate user based on type:
   - `admin`: Any superuser or staff user
   - `user`: Any non-admin, non-staff user (customer)
   - `agent`: Any other agent (excluding current user)
3. **Message Creation**: Creates `ChatMessage` record in database
4. **Response**: Returns JSON with success status and message details

### 2. Frontend Components

#### Message Modal
- **Trigger**: Click "Message" button in profile card
- **Recipient Selection**: Dropdown with options:
  - System Administrator
  - Customer Support  
  - Another Agent
- **Message Input**: Textarea for message content
- **Actions**: Send Message and Cancel buttons

#### JavaScript Integration
```javascript
function sendMessage() {
    // Validation
    // CSRF token retrieval
    // API call to /dashboard/agent-dashboard/send-message/
    // Success/error handling
    // Modal cleanup
}
```

### 3. API Endpoint Details

#### Request Format
```json
POST /dashboard/agent-dashboard/send-message/
Content-Type: application/json
X-CSRFToken: [csrf_token]

{
    "recipient": "admin|user|agent",
    "message": "Message content here"
}
```

#### Response Format
**Success (200)**:
```json
{
    "success": true,
    "message": "Message sent successfully",
    "message_id": 123,
    "recipient_name": "John Doe"
}
```

**Error (4xx/5xx)**:
```json
{
    "success": false,
    "message": "Error description"
}
```

### 4. Security Features

#### CSRF Protection
- Uses Django's built-in CSRF protection
- Token retrieved from existing form on page
- Validated on backend

#### Authentication
- `@login_required` decorator ensures only authenticated users can send messages
- User permissions verified through Django auth system

#### Input Validation
- Recipient type validation
- Message content validation (non-empty)
- JSON parsing error handling

### 5. Message Flow

1. **User Action**: Click "Message" button
2. **Modal Opens**: User selects recipient and types message
3. **Validation**: Frontend checks for required fields
4. **API Call**: POST request to backend with message data
5. **Backend Processing**: 
   - Validate request
   - Find recipient user
   - Create ChatMessage record
   - Return response
6. **Frontend Response**: 
   - Show success/error message
   - Close modal
   - Clear form

### 6. Integration Points

#### Existing Systems
- **ChatMessage Model**: Reuses existing chat infrastructure
- **User Management**: Integrates with Django auth system
- **Notifications**: Messages appear in recipient's notification system

#### Future Enhancements
- Real-time message delivery (WebSocket)
- Message threading
- File attachments
- Message history view
- Read receipts

### 7. Testing

#### Test Files Created
- `test_message_backend.html`: Standalone test page for API testing
- Tests all recipient types and error scenarios

#### Manual Testing Steps
1. Navigate to agent profile page
2. Click "Message" button
3. Select recipient type
4. Type message content
5. Click "Send Message"
6. Verify success message
7. Check database for message record

### 8. Troubleshooting

#### Common Issues
- **CSRF Token Error**: Refresh page to get new token
- **Recipient Not Found**: Ensure appropriate users exist in database
- **Permission Denied**: Verify user is logged in and has agent role

#### Debug Information
- Browser console for JavaScript errors
- Django logs for backend errors
- Network tab for API request/response details

## Current Status
- **Backend**: Complete and functional
- **Frontend**: Complete and functional  
- **Database**: Messages stored successfully
- **Security**: CSRF and authentication implemented
- **Testing**: Test files created and verified

The message functionality is now fully integrated with the backend and ready for production use.
