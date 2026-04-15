# Login System Guide

## Overview
The system supports multiple user types with role-based authentication and dashboard redirection.

## User Types and Roles

### 1. SuperAdmin
- **Role**: SuperAdmin
- **Login URL**: `/users/admin-login/` or `/users/login/`
- **Dashboard**: `/dashboards/admin-dashboard/`
- **Permissions**: Full system access, company management, user management

### 2. Admin
- **Role**: Admin
- **Login URL**: `/users/admin-login/` or `/users/login/`
- **Dashboard**: `/dashboards/admin-dashboard/`
- **Permissions**: Company management, ticket management, reporting

### 3. Agent
- **Role**: Agent
- **Login URL**: `/users/agent-login/` or `/users/login/`
- **Dashboard**: `/dashboards/agent-dashboard/`
- **Permissions**: Ticket handling, chat with users, ratings

### 4. User/Customer
- **Role**: User or Customer
- **Login URL**: `/users/user-login/` or `/users/login/`
- **Dashboard**: `/dashboards/user-dashboard/`
- **Permissions**: Create tickets, view tickets, chat with agents

## Company Creation with User Accounts

When a SuperAdmin creates a new company, the system automatically:

1. **Creates User Account**
   - Username: Generated from email (e.g., `company_name_gmail_com`)
   - Email: Company email
   - Password: Provided password
   - First Name: First word of company name
   - Last Name: Remaining words of company name

2. **Creates UserProfile**
   - Links to User account
   - Assigned "User" role by default
   - Stores phone and address information

3. **Associates with Company**
   - UserProfile is linked to the Company
   - User can login and access their dashboard

## Login Flow

### Automatic Role-Based Redirection
The login system automatically redirects users based on their role:

```python
if _is_admin(user):
    return redirect('dashboards:admin_dashboard')
if _is_agent(user):
    return redirect('dashboards:agent_dashboard')
return redirect('dashboards:user_dashboard')
```

### Authentication Methods
- **Username/Email**: Users can login with username or email
- **Password**: Secure password authentication
- **Role Validation**: System checks user role and permissions

## Password Features

### Password Requirements
- Minimum 8 characters
- Maximum 50 characters
- Stored securely using Django's password hashing

### Password Visibility Toggle
- Eye icon in login forms to show/hide password
- Improves user experience during login

## Forgot Password System

Each user type has dedicated forgot password functionality:

- **Admin**: `/users/admin-forgot-password/`
- **Agent**: `/users/agent-forgot-password/`
- **User**: `/users/user-forgot-password/`

Features:
- 6-digit verification code
- 15-minute expiry
- Email verification
- Role-based validation

## Security Features

### Password Security
- Passwords hashed using Django's PBKDF2 algorithm
- No plain text storage
- Secure password validation

### Role-Based Access
- Users can only access their designated dashboards
- Admin users cannot access agent dashboards
- Role validation on every request

### Session Management
- Secure session handling
- Automatic logout on inactivity
- CSRF protection

## Testing the System

### Test Company Creation
1. Login as SuperAdmin
2. Go to Companies page
3. Click "Add Company"
4. Fill form with company details and password
5. Submit form

### Test User Login
1. Use the company email to login
2. Enter the password set during company creation
3. Should be redirected to User dashboard

### Verify User Account
1. Check User model for new account
2. Check UserProfile for role assignment
3. Check Company-User association

## URL Structure

### Login Pages
- Main Login: `/users/login/`
- Admin Login: `/users/admin-login/`
- Agent Login: `/users/agent-login/`
- User Login: `/users/user-login/`

### Dashboards
- Admin Dashboard: `/dashboards/admin-dashboard/`
- Agent Dashboard: `/dashboards/agent-dashboard/`
- User Dashboard: `/dashboards/user-dashboard/`

### Forgot Password
- Admin: `/users/admin-forgot-password/`
- Agent: `/users/agent-forgot-password/`
- User: `/users/user-forgot-password/`

## Database Relationships

### Models Involved
1. **User**: Django's built-in User model
2. **UserProfile**: Extended user information with role
3. **Company**: Company information with user associations
4. **Role**: User roles (SuperAdmin, Admin, Agent, User)

### Relationships
- User -> UserProfile (OneToOne)
- UserProfile -> Role (ForeignKey)
- Company -> UserProfile (ManyToMany)

## Troubleshooting

### Common Issues
1. **Login Fails**: Check if User account exists and is active
2. **Wrong Dashboard**: Verify user role assignment
3. **Password Issues**: Check password requirements and hashing
4. **Company Access**: Verify Company-User association

### Debug Steps
1. Check User model for account existence
2. Verify UserProfile role assignment
3. Test authentication with correct credentials
4. Check dashboard permissions

This system ensures that all companies and users created by SuperAdmin have proper login access and are directed to their appropriate dashboards based on their roles.
