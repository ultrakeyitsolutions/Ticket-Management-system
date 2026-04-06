#!/usr/bin/env python
"""
Test script to verify 2FA functionality
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile
import pyotp
import time

def test_2fa_functionality():
    """Test 2FA functionality"""
    print("Testing 2FA functionality...")
    
    try:
        # Get current user
        user = User.objects.first()
        if not user:
            print("❌ No users found in database.")
            return
            
        print(f"👤 Testing with user: {user.username}")
        
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if created:
            print("📝 Created new user profile")
        
        # Test TOTP secret generation
        print(f"\n🔐 Testing TOTP secret generation...")
        
        if not profile.two_factor_secret:
            # Generate a test secret
            profile.two_factor_secret = pyotp.random_base32()
            profile.save()
            print(f"✅ Generated TOTP secret: {profile.two_factor_secret}")
        else:
            print(f"✅ Existing TOTP secret: {profile.two_factor_secret}")
        
        # Test TOTP code generation and verification
        print(f"\n🔢 Testing TOTP code generation and verification...")
        
        totp = pyotp.TOTP(profile.two_factor_secret)
        current_code = totp.now()
        
        print(f"   - Current TOTP code: {current_code}")
        print(f"   - Time remaining: {totp.interval - (int(time.time()) % totp.interval)} seconds")
        
        # Test verification
        if totp.verify(current_code):
            print(f"✅ TOTP code verification successful!")
        else:
            print(f"❌ TOTP code verification failed!")
        
        # Test provisioning URI generation
        print(f"\n📱 Testing provisioning URI generation...")
        
        provisioning_uri = pyotp.totp.TOTP(profile.two_factor_secret).provisioning_uri(
            name=user.email,
            issuer_name="TicketHub"
        )
        
        print(f"✅ Provisioning URI: {provisioning_uri}")
        
        # Test QR code generation
        print(f"\n🖼️ Testing QR code generation...")
        
        try:
            import qrcode
            import io
            import base64
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code_data = base64.b64encode(buffer.getvalue()).decode()
            
            print(f"✅ QR code generated successfully!")
            print(f"   - Data URI length: {len(qr_code_data)} characters")
            print(f"   - Preview: data:image/png;base64,{qr_code_data[:50]}...")
            
        except Exception as e:
            print(f"❌ QR code generation failed: {e}")
        
        # Test 2FA enable/disable
        print(f"\n🔄 Testing 2FA enable/disable...")
        
        # Enable 2FA
        profile.two_factor_enabled = True
        profile.save()
        print(f"✅ 2FA enabled for user: {user.username}")
        
        # Disable 2FA
        profile.two_factor_enabled = False
        profile.save()
        print(f"✅ 2FA disabled for user: {user.username}")
        
        print(f"\n🎉 2FA functionality test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing 2FA functionality: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_2fa_functionality()
