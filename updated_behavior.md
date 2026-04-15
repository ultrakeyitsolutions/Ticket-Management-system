# Updated Forgot Password Behavior

## Changes Made

The forgot password functionality now shows specific messages based on email status:

### **New Behavior:**

1. **If email is NOT registered in the system:**
   - Message: "Your email is not registered"
   - Stays on forgot password page

2. **If email exists but user is NOT a SuperAdmin:**
   - Message: "Your email is not registered as a SuperAdmin"
   - Stays on forgot password page

3. **If email exists and user IS a SuperAdmin:**
   - Message: "Verification code sent to [email]. Please check your email."
   - Redirects to reset password page

### **Test Scenarios:**

#### Test with Non-registered Email:
1. Go to: http://127.0.0.1:8000/superadmin/forgot-password/
2. Enter: `nonregistered@test.com`
3. Expected: "Your email is not registered"

#### Test with Regular User Email:
1. Find a regular user email (not superadmin)
2. Enter that email
3. Expected: "Your email is not registered as a SuperAdmin"

#### Test with SuperAdmin Email:
1. Enter any of these superadmin emails:
   - `arikatlasathvika98@gmail.com`
   - `jane.smith@example.com`
   - `test@superadmin.com`
2. Expected: Success message + redirect to reset page

### **Code Changes:**

Updated `apps/superadmin/views.py` in the `superadmin_forgot_password` function:

```python
if user:
    if _is_superadmin_user(user):
        # Send verification code and redirect
        ...
    else:
        # User exists but not superadmin
        messages.error(request, 'Your email is not registered as a SuperAdmin')
        return render(request, 'superadmin/forgot_password.html')
else:
    # Email not registered
    messages.error(request, 'Your email is not registered')
    return render(request, 'superadmin/forgot_password.html')
```

### **Security Note:**
This change reveals whether an email is registered in the system, which is less secure than the previous approach. However, it provides better user experience as requested.

Ready for testing at: http://127.0.0.1:8000/superadmin/forgot-password/
