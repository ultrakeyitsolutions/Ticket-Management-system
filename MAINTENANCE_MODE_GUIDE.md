# Maintenance Mode Guide

## 🔧 What Maintenance Mode Does

When maintenance mode is enabled, the system blocks access for regular users while allowing administrators and staff to continue working.

## 👥 Who Can Access During Maintenance

### ✅ **Can Access (Admin Users):**
- **Superusers** (`is_superuser = True`)
- **Staff users** (`is_staff = True`)  
- **Admin role users** (`userprofile.role.name = 'Admin'`)
- **Agent role users** (`userprofile.role.name = 'Agent'`)

### ❌ **Cannot Access (Regular Users):**
- **Customer role users**
- **User role users**
- **Unauthenticated users**

## 🚫 What Regular Users See

When regular users try to access the system during maintenance mode, they see:

```
🔧 Under Maintenance

We're currently performing scheduled maintenance.

Please try again later. Thank you for your patience!

Admin users can still access the system.
```

- **HTTP Status**: 503 (Service Unavailable)
- **Page**: Simple maintenance page with message

## 🛠️ What Admin Users Can Do During Maintenance

### ✅ **Full System Access:**
- Access all dashboard pages
- View and manage tickets
- Manage users and settings
- Access all admin functions
- Use chat system
- Generate reports

### ✅ **System Settings:**
- Toggle maintenance mode on/off
- Modify system configuration
- Update company information
- Manage user registration settings

### ✅ **Ticket Management:**
- Create, edit, resolve tickets
- Assign tickets to agents
- Update ticket status
- Manage ticket priorities

### ✅ **User Management:**
- Create and manage user accounts
- Assign user roles and permissions
- Manage user profiles
- Handle user registration

## 🎯 How to Test Maintenance Mode

### Step 1: Try as Regular User
1. **Log out** if you're logged in as admin/agent
2. **Try to access**: `http://127.0.0.1:8000/dashboard/agent-dashboard/`
3. **Expected**: See maintenance page with 503 error

### Step 2: Test as Admin User
1. **Log in** as admin/agent user
2. **Access**: `http://127.0.0.1:8000/dashboard/agent-dashboard/`
3. **Expected**: Full access to dashboard

### Step 3: Test Different Pages
- **Dashboard**: `http://127.0.0.1:8000/dashboard/agent-dashboard/`
- **Tickets**: `http://127.0.0.1:8000/dashboard/agent-dashboard/tickets.html`
- **Settings**: `http://127.0.0.1:8000/dashboard/agent-dashboard/settings.html`
- **Profile**: `http://127.0.0.1:8000/dashboard/agent-dashboard/profile.html`

## ⚙️ Enabling/Disabling Maintenance Mode

### Method 1: Via Settings Page (Recommended)
1. Go to: `http://127.0.0.1:8000/dashboard/agent-dashboard/settings.html`
2. Click **System** tab
3. Toggle **Maintenance Mode** switch
4. Click **Save Changes**

### Method 2: Via Python (Already Done)
```python
from dashboards.models import SiteSettings
settings = SiteSettings.get_solo()
settings.maintenance_mode = True
settings.save()
```

### Method 3: Via Admin Panel
1. Go to: `http://127.0.0.1:8000/superadmin/`
2. Navigate to Settings
3. Toggle maintenance mode

## 🔍 What to Check During Maintenance

### ✅ **Admin Access Verification:**
- Admin users can access all pages
- Navigation works correctly
- All functions operate normally

### ✅ **User Blocking Verification:**
- Regular users see maintenance page
- HTTP 503 status returned
- No access to system functions

### ✅ **System Functionality:**
- Database operations work
- API endpoints function
- Real-time updates work

## 🚨 Important Notes

### **Security:**
- Maintenance mode is enforced at the middleware level
- Cannot be bypassed by URL manipulation
- Role-based access control is strict

### **Performance:**
- Maintenance mode has minimal performance impact
- System remains fully functional for admins
- No database locks or restrictions

### **User Experience:**
- Clear messaging for blocked users
- Admins can work without interruption
- System state is preserved

## 🎛️ When to Use Maintenance Mode

### ✅ **Appropriate Times:**
- System updates and patches
- Database migrations
- Major configuration changes
- Emergency fixes
- Scheduled maintenance windows

### ❌ **Avoid When:**
- During normal business hours (unless emergency)
- For extended periods without communication
- When regular users need access

## 🔧 Troubleshooting

### If Admins Are Blocked:
1. Check user role in UserProfile
2. Verify is_staff/is_superuser flags
3. Check middleware configuration

### If Users Still Access:
1. Verify maintenance mode is enabled
2. Check middleware is properly loaded
3. Clear browser cache

### If Settings Don't Save:
1. Check database connection
2. Verify form submission
3. Check for JavaScript errors

## 📱 Current Status

**Maintenance mode is currently ENABLED** ✅

### What You Can Do:
1. **Test admin access** - Try accessing the dashboard as admin/agent
2. **Test user blocking** - Try accessing as regular user (should see maintenance page)
3. **Explore admin functions** - Use all admin features during maintenance
4. **Toggle back off** - Disable when maintenance is complete

## 🎯 Testing Instructions

1. **Test Admin Access**: 
   - Log in as admin/agent user
   - Navigate to: `http://127.0.0.1:8000/dashboard/agent-dashboard/`
   - Verify full access

2. **Test User Blocking**:
   - Log out or use incognito window
   - Try accessing: `http://127.0.0.1:8000/dashboard/agent-dashboard/`
   - Verify maintenance page appears

3. **Test Settings Toggle**:
   - Go to settings page
   - Toggle maintenance mode off
   - Verify regular users can access again

**Maintenance mode is ready for testing!** 🔧
