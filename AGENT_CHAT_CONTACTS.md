# Agent Chat Contact Selection

## Overview
As an **Agent**, when you access the chat page (`/dashboard/agent-dashboard/chat.html`), you have **specific contacts** available based on your role and ticket assignments.

---

## Available Contacts for Agents

### **1. Assigned Admin Support Staff**

**How they appear**: Based on your ticket assignments
**Who they are**: Admin users who are assigned to your tickets
**Selection logic**:
```python
# Get tickets assigned to you
user_tickets = Ticket.objects.filter(created_by=request.user).order_by('-created_at')

# For each ticket, find the assigned admin
for ticket in user_tickets:
    if ticket.assigned_to:
        # This admin becomes available as a contact
        contact = ticket.assigned_to
```

**Example contacts**:
```
Support Contacts:
John Admin (Assigned to ticket #123)
Sarah Manager (Assigned to ticket #456) 
Mike Supervisor (Assigned to ticket #789)
```

### **2. Fallback Admin (if no assignment)**

**How they appear**: When tickets have no assigned admin
**Who they are**: First available admin in the system
**Selection logic**:
```python
# If no admin assigned to ticket
fallback_admin = User.objects.filter(is_staff=True, is_active=True).order_by('id').first()
```

**Example**:
```
Default Contact:
System Administrator (Fallback support)
```

---

## Contact Selection Process

### **Automatic Selection**
The system **automatically selects** the most appropriate contact:

1. **Primary**: Admin assigned to your most recent ticket
2. **Fallback**: First available admin if no assignments exist

### **Manual Selection**
You can switch between available contacts:
- **Contact list** shows all assigned admins
- **Click any contact** to start/continue conversation
- **See unread counts** for each contact

---

## Real-World Example

### **Your Ticket Assignments**:
```
Ticket #123: "Payment issue" -> Assigned to: John Admin
Ticket #456: "Login problem" -> Assigned to: Sarah Manager  
Ticket #789: "Bug report" -> No assignment -> Fallback: Mike Supervisor
```

### **Your Chat Contacts**:
```
Available Contacts:
John Admin (Ticket #123) [2 unread]
Sarah Manager (Ticket #456) [1 unread]
Mike Supervisor (Default support) [0 unread]
```

### **Chat Interface**:
```
Contacts Sidebar:
John Admin (Online)
  Ticket: #123 - Payment issue
  Last message: 2 hours ago
  
Sarah Manager (Online)  
  Ticket: #456 - Login problem
  Last message: 1 day ago

Mike Supervisor (Online)
  Default support contact
  No recent messages
```

---

## Contact Information Display

### **What you see for each contact**:
```
Contact Name: John Admin
Role: System Administrator
Status: Online/Offline
Ticket Association: #123 - Payment issue
Unread Count: 2 messages
Last Activity: 2 hours ago
```

### **Conversation Context**:
```
Chat with John Admin (Ticket #123)
---------------------------------
John Admin: I've reviewed your payment issue
You: Thanks, what's the status?
John Admin: It's been resolved
[2:30 PM]
```

---

## Different from Other User Types

### **Admin Chat Contacts**:
- **All users** who have tickets or sent messages
- **Customers, agents, other admins**
- **Full system access**

### **Agent Chat Contacts**:
- **Only assigned admins** for your tickets
- **Limited to your support team**
- **Ticket-specific conversations**

### **User Chat Contacts**:
- **Only assigned support staff**
- **Single admin per ticket**
- **Customer-focused support**

---

## How Contacts Are Determined

### **Database Query**:
```python
# Your tickets
user_tickets = Ticket.objects.filter(created_by=request.user)

# Contact extraction
for ticket in user_tickets:
    if ticket.assigned_to:
        contacts.append(ticket.assigned_to)
    else:
        contacts.append(fallback_admin)
```

### **Contact Filtering**:
- **Only active staff users** (`is_staff=True`, `is_active=True`)
- **Unique contacts only** (no duplicates)
- **Sorted by ticket recency**

---

## Chat Context

### **Ticket-Specific Conversations**:
Each chat is tied to a specific ticket:
```
Chat with John Admin
Context: Ticket #123 - Payment issue
Messages: Related to this ticket only
```

### **Admin Assignment**:
```
If you're assigned a new admin:
- New contact appears in list
- Conversation history transfers
- Ticket context updates
```

---

## Summary

**As an Agent, your chat contacts are:**

1. **Primary**: Admins assigned to your tickets
2. **Fallback**: Default admin if no assignment
3. **Limited**: Only your support team members
4. **Contextual**: Each tied to specific tickets

**You CANNOT chat with:**
- Other agents (unless admin-assigned)
- Customers directly
- Random system users
- Users outside your ticket assignments

**Your chat is focused on ticket-specific support with your assigned admin team!**
