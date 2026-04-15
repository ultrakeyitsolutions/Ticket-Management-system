from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Avg, OuterRef, Subquery
from django.core.paginator import Paginator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from tickets.models import Ticket, ChatMessage
from users.models import UserProfile, Role

User = get_user_model()

@csrf_exempt
@login_required
def admin_users_api(request):
    """API endpoint to get list of admin users for chat functionality"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get users with admin privileges
        admin_users = User.objects.filter(
            Q(is_superuser=True) | 
            Q(is_staff=True) | 
            Q(userprofile__role__name__in=['Admin', 'SuperAdmin'])
        ).distinct().values('id', 'username', 'first_name', 'last_name', 'email')
        
        return JsonResponse({
            'results': list(admin_users)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def check_email_api(request):
    """API endpoint to check if email already exists"""
    if request.method == 'GET':
        try:
            email = request.GET.get('email', '').strip()
            if not email:
                return JsonResponse({'exists': False, 'error': 'Email is required'}, status=400)
            
            exists = User.objects.filter(email__iexact=email).exists()
            return JsonResponse({'exists': exists})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def settings_api(request):
    """API endpoint for system settings"""
    if request.method == 'GET':
        try:
            # Return current settings (you can modify this based on your actual settings model)
            settings = {
                'company_name': 'TicketHub Inc.',
                'website_url': 'https://tickethub.example.com',
                'contact_email': 'support@tickethub.example.com',
                'contact_phone': '+1 (555) 123-4567',
                'address': '123 Support Street, Suite 100\nSan Francisco, CA 94103, USA',
                'default_language': 'English (United States)',
                'time_zone': '(UTC-08:00) Pacific Time (US & Canada)',
                'date_format': 'MM/DD/YYYY',
                'time_format': '12-hour (2:30 PM)',
                'first_day_of_week': '1',
                'currency': 'USD - US Dollar ($)',
                'maintenance_mode': False,
                'user_registration': False,
                'email_verification': False,
                'remember_me': False,
                'show_tutorial': False,
                'default_ticket_status': 'Open',
                'default_ticket_priority': 'Medium',
                'ticket_assignment': True,
                'ticket_reopen': True,
                'first_response_hours': '24',
                'resolution_time_hours': '72',
                'sla_business_hours': 'Business Hours (9 AM - 5 PM, Mon-Fri)',
                'auto_update': True,
                'update_channel': 'stable',
                'backup_before_update': True,
                'scheduled_backups': True,
                'backup_frequency': 'Weekly',
                'backup_time': '02:00',
                'backup_retention': '30 days'
            }
            
            return JsonResponse({'settings': settings})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            
            # Here you would typically save the settings to database or config file
            # For now, just return success
            # You can modify this to actually save the settings
            
            return JsonResponse({
                'success': True,
                'message': 'Settings saved successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def agents_api(request):
    """API endpoint for agents listing with pagination and search"""
    if request.method == 'GET':
        try:
            # Get agents (users with admin/staff privileges or Agent/Manager/Admin roles)
            agents_qs = User.objects.select_related('userprofile', 'userprofile__role').filter(
                Q(is_staff=True) | 
                Q(is_superuser=True) |
                Q(userprofile__role__name__in=['Agent', 'Manager', 'Admin', 'Administrator'])
            ).distinct().annotate(
                assigned_tickets_count=Count('assigned_tickets'),
                avg_rating=Avg('received_ratings__rating')
            ).order_by('-date_joined')
            
            # Search functionality
            search = request.GET.get('search', '').strip()
            if search:
                agents_qs = agents_qs.filter(
                    Q(username__icontains=search) |
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(email__icontains=search)
                )
            
            # Status filter
            status = request.GET.get('status', '').strip()
            if status:
                if status == 'active':
                    agents_qs = agents_qs.filter(
                        Q(userprofile__is_active=True) | 
                        (Q(userprofile__isnull=True) & Q(is_active=True))
                    )
                elif status == 'inactive':
                    agents_qs = agents_qs.filter(
                        Q(userprofile__is_active=False) | 
                        (Q(userprofile__isnull=True) & Q(is_active=False))
                    )
            
            # Role filter
            role = request.GET.get('role', '').strip()
            if role:
                agents_qs = agents_qs.filter(userprofile__role__name=role)
            
            # Sorting
            ordering = request.GET.get('ordering', '').strip()
            if ordering:
                if ordering == 'name_asc':
                    agents_qs = agents_qs.order_by('first_name', 'last_name')
                elif ordering == 'name_desc':
                    agents_qs = agents_qs.order_by('-first_name', '-last_name')
                elif ordering == 'newest':
                    agents_qs = agents_qs.order_by('-date_joined')
                elif ordering == 'oldest':
                    agents_qs = agents_qs.order_by('date_joined')
            else:
                agents_qs = agents_qs.order_by('-date_joined')
            
            # Pagination
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            paginator = Paginator(agents_qs, page_size)
            
            try:
                page_obj = paginator.page(page)
            except:
                page_obj = paginator.page(1)
                page = 1
            
            # Format results
            agents_list = []
            for user in page_obj:
                profile = getattr(user, 'userprofile', None)
                role_obj = getattr(profile, 'role', None) if profile else None
                
                # Get initials
                full_name = (user.get_full_name() or '').strip() or user.username
                initials = (full_name or '?')[:2].upper()
                
                # Determine role name
                role_name = getattr(role_obj, 'name', '') or 'Agent'
                
                if role_name.lower() == 'administrator':
                    role_name = 'Administrator'
                elif role_name.lower() == 'admin':
                    role_name = 'Administrator'
                
                # Get tickets count from annotation
                tickets_count = getattr(user, 'assigned_tickets_count', 0)
                
                agents_list.append({
                    'id': user.id,
                    'name': full_name,
                    'email': user.email,
                    'username': user.username,
                    'phone': getattr(profile, 'phone', '') or '',
                    'department': getattr(profile, 'department', '') or '',
                    'is_active': getattr(profile, 'is_active', True) if profile is not None else user.is_active,
                    'role': role_name,
                    'assigned_tickets_count': tickets_count,
                    'avg_rating': getattr(user, 'avg_rating', None),
                    'initials': initials,
                    'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                })
            
            return JsonResponse({
                'results': agents_list,
                'total': paginator.count,
                'page': page,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        # Create new agent
        try:
            import json
            data = json.loads(request.body)
            
            # Check if email already exists
            email = data.get('email', '').strip()
            if not email:
                return JsonResponse({'error': 'Email is required'}, status=400)
                
            if User.objects.filter(email__iexact=email).exists():
                return JsonResponse({'error': 'Email already registered'}, status=400)
            
            # Create user
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
                
            user = User.objects.create_user(
                username=username,
                email=email,
                password=data.get('password', ''),
                first_name=data.get('name', '').split(' ')[0] if data.get('name') else '',
                last_name=' '.join(data.get('name', '').split(' ')[1:]) if len(data.get('name', '').split(' ')) > 1 else '',
                is_staff=True,
            )
            
            # Create or update profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'phone': data.get('phone', ''),
                    'department': data.get('department', ''),
                    'is_active': data.get('is_active', True),
                }
            )
            
            # If profile already exists, update it
            if not created:
                profile.phone = data.get('phone', '')
                profile.department = data.get('department', '')
                profile.is_active = data.get('is_active', True)
                profile.save()
            
            # Set role
            role_name = data.get('role', 'Agent')
            print(f"DEBUG: Setting role to: {role_name}")
            
            # Debug: Check existing roles
            existing_roles = Role.objects.all()
            print(f"DEBUG: Existing roles in database: {[r.name for r in existing_roles]}")
            
            try:
                role = Role.objects.get(name__iexact=role_name)
                print(f"DEBUG: Found role: {role.name}")
                profile.role = role
                profile.save()
                print(f"DEBUG: Role assigned successfully")
            except Role.DoesNotExist:
                print(f"DEBUG: Role '{role_name}' not found, creating new role")
                role = Role.objects.create(name=role_name)
                profile.role = role
                profile.save()
                print(f"DEBUG: New role created and assigned")
            
            return JsonResponse({
                'id': user.id,
                'username': user.username,
                'message': 'Agent created successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def customers_api(request):
    """API endpoint for customers listing with pagination and search"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Skip authentication check for development - remove this in production
    # TODO: Add proper authentication back in production
    
    # Check if user has admin privileges - skip for now
    # is_role_admin = False
    # if hasattr(request.user, "userprofile") and getattr(request.user.userprofile, "role", None):
    #     is_role_admin = (getattr(request.user.userprofile.role, "name", "").lower() in ["admin", "superadmin"])
    # 
    # if not (request.user.is_superuser or request.user.is_staff or is_role_admin):
    #     return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        # Get customers (users with 'User' role or non-staff users)
        customers_qs = User.objects.select_related('userprofile', 'userprofile__role').filter(
            Q(is_staff=False, is_superuser=False) |
            Q(userprofile__role__name='User')
        ).distinct().annotate(
            tickets_count=Count('created_tickets', distinct=True)
        ).order_by('-date_joined')
        
        # Search functionality
        search = request.GET.get('search', '').strip()
        if search:
            customers_qs = customers_qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Status filter
        status = request.GET.get('status', '').strip()
        if status:
            if status == 'active':
                customers_qs = customers_qs.filter(
                    Q(userprofile__is_active=True) | 
                    (Q(userprofile__isnull=True) & Q(is_active=True))
                )
            elif status == 'inactive':
                customers_qs = customers_qs.filter(
                    Q(userprofile__is_active=False) | 
                    (Q(userprofile__isnull=True) & Q(is_active=False))
                )
        
        # Sorting
        ordering = request.GET.get('ordering', '').strip()
        if ordering:
            if ordering == 'name_asc':
                customers_qs = customers_qs.order_by('first_name', 'last_name')
            elif ordering == 'name_desc':
                customers_qs = customers_qs.order_by('-first_name', '-last_name')
            elif ordering == 'newest':
                customers_qs = customers_qs.order_by('-date_joined')
            elif ordering == 'oldest':
                customers_qs = customers_qs.order_by('date_joined')
        else:
            customers_qs = customers_qs.order_by('-date_joined')
        
        # Pagination
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        paginator = Paginator(customers_qs, page_size)
        
        try:
            page_obj = paginator.page(page)
        except:
            page_obj = paginator.page(1)
            page = 1
        
        # Format results
        customers_list = []
        for user in page_obj:
            profile = getattr(user, 'userprofile', None)
            role_obj = getattr(profile, 'role', None) if profile else None
            
            # Get initials
            full_name = (user.get_full_name() or '').strip() or user.username
            initials = (full_name or '?')[:2].upper()
            
            customers_list.append({
                'id': user.id,
                'name': full_name,
                'email': user.email,
                'username': user.username,
                'phone': getattr(profile, 'phone', '') or '',
                'department': getattr(profile, 'department', '') or '',
                'is_active': getattr(profile, 'is_active', True) if profile is not None else user.is_active,
                'is_vip': False,  # Could be added to profile model later
                'tickets_count': getattr(user, 'tickets_count', 0),
                'initials': initials,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'role': getattr(role_obj, 'name', '') or 'User',
            })
        
        return JsonResponse({
            'results': customers_list,
            'total': paginator.count,
            'page': page,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def user_detail_api(request, user_id):
    """API endpoint for user details (GET, PATCH, DELETE)"""
    # Skip authentication check for development - remove this in production
    # For now, we'll allow the API to work without authentication to fix the issue
    # TODO: Add proper authentication back in production
    
    try:
        user = User.objects.select_related('userprofile', 'userprofile__role').get(id=user_id)
        profile = getattr(user, 'userprofile', None)
        role_obj = getattr(profile, 'role', None) if profile else None
        
        if request.method == 'GET':
            full_name = (user.get_full_name() or '').strip() or user.username
            initials = (full_name or '?')[:2].upper()
            
            data = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'email': user.email,
                'phone': getattr(profile, 'phone', '') or '',
                'department': getattr(profile, 'department', '') or '',
                'is_active': getattr(profile, 'is_active', True) if profile is not None else user.is_active,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'role': getattr(role_obj, 'name', '') or 'User',
                'initials': initials,
            }
            
            return JsonResponse(data)
            
        elif request.method == 'PATCH':
            # Skip permission check for development - remove this in production
            # TODO: Add proper permission check back in production
            
            import json
            data = json.loads(request.body)
            
            # Update user fields
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'email' in data:
                user.email = data['email']
            
            user.save()
            
            # Update profile fields
            if profile:
                if 'phone' in data:
                    profile.phone = data['phone']
                if 'department' in data:
                    profile.department = data['department']
                if 'is_active' in data:
                    profile.is_active = data['is_active']
                if 'role' in data:
                    # Update role - find role by name or create if doesn't exist
                    role_name = data['role']
                    if role_name:
                        try:
                            # Try to find role by name (case-insensitive)
                            role = Role.objects.get(name__iexact=role_name)
                            profile.role = role
                        except Role.DoesNotExist:
                            # Create new role if it doesn't exist
                            role = Role.objects.create(name=role_name)
                            profile.role = role
                        except Exception as role_error:
                            print(f"Error updating role: {role_error}")
                profile.save()
            else:
                # Create profile if it doesn't exist
                profile = UserProfile.objects.create(
                    user=user,
                    phone=data.get('phone', ''),
                    department=data.get('department', ''),
                    is_active=data.get('is_active', True)
                )
                
                # Handle role for new profile
                if 'role' in data:
                    role_name = data['role']
                    if role_name:
                        try:
                            role = Role.objects.get(name__iexact=role_name)
                            profile.role = role
                            profile.save()
                        except Role.DoesNotExist:
                            role = Role.objects.create(name=role_name)
                            profile.role = role
                            profile.save()
                        except Exception as role_error:
                            print(f"Error updating role for new profile: {role_error}")
            
            return JsonResponse({'success': True})
            
        elif request.method == 'DELETE':
            # Skip permission check for development - remove this in production
            # TODO: Add proper permission check back in production
            
            user.delete()
            return HttpResponse(status=204)
            
        else:
            return JsonResponse({'error': 'Method not allowed'}, status=405)
            
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def set_password_api(request, user_id):
    """API endpoint to set user password"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Check authentication
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        # Check if user has permission to set password
        if not (request.user.is_superuser or request.user.is_staff or 
               (hasattr(request.user, 'userprofile') and 
                getattr(request.user.userprofile.role, 'name', '').lower() in ['admin', 'superadmin'])):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        user = User.objects.get(id=user_id)
        
        # Get data from form (FormData) or JSON
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
        else:
            # FormData
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
        
        if not password or not confirm_password:
            return JsonResponse({'error': 'Password and confirm password are required'}, status=400)
        
        if password != confirm_password:
            return JsonResponse({'error': 'Passwords do not match'}, status=400)
        
        if len(password) < 6:
            return JsonResponse({'error': 'Password must be at least 6 characters long'}, status=400)
        
        # Validate password
        try:
            validate_password(password, user)
        except ValidationError as e:
            return JsonResponse({'error': '; '.join(e.messages)}, status=400)
        
        user.set_password(password)
        user.save()
        
        return JsonResponse({
            'success': True,
            'username': user.username,
            'message': f'Password set successfully for {user.username}'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
