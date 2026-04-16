# SuperAdmin Forgot Password - Manual Test Instructions

## Setup Complete
The forgot password functionality has been implemented with debug logging.

## Test URLs
- Login Page: http://127.0.0.1:8000/superadmin/login/
- Forgot Password: http://127.0.0.1:8000/superadmin/forgot-password/
- Reset Password: http://127.0.0.1:8000/superadmin/reset-password/

## Test Emails (SuperAdmin Accounts)
Use any of these emails for testing:
- arikatlasathvika98@gmail.com
- jane.smith@example.com
- test@superadmin.com
- zoe@example.com
- siddu@gmail.com
- raju@gmail.com

## Testing Steps

### 1. Test Forgot Password
1. Go to: http://127.0.0.1:8000/superadmin/forgot-password/
2. Enter a valid superadmin email (e.g., arikatlasathvika98@gmail.com)
3. Click "Send Verification Code"
4. Check the server console for debug output
5. Check your email for the verification code

### 2. Test Password Reset
1. After receiving the code, you'll be redirected to the reset page
2. Enter the 6-digit verification code
3. Enter new password (minimum 8 characters, letters + numbers)
4. Confirm password
5. Click "Reset Password"

### 3. Test Login with New Password
1. Go to: http://127.0.0.1:8000/superadmin/login/
2. Enter your email and new password
3. Verify login works

## Debug Information
The server console will show debug output including:
- Email being processed
- User lookup results
- Verification code generation
- Email sending status
- Session storage

## Common Issues & Solutions

### Email Not Received
- Check spam/junk folder
- Verify email settings in config/settings.py
- Check server console for email sending errors

### Invalid Code Error
- Ensure code is entered correctly (6 digits)
- Check if code expired (15 minutes)
- Try requesting a new code

### Page Not Working
- Ensure server is running: `python manage.py runserver`
- Check for any syntax errors in views.py
- Verify URL patterns in urls.py

## Security Features Implemented
- Only registered superadmin emails receive codes
- 15-minute code expiry
- Session-based storage (no database persistence)
- Password strength requirements
- No email enumeration attacks
