from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from analytics.models import Lecturer, LecturerSettings
from django.shortcuts import render, redirect
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from analytics.models import Lecturer, LecturerSettings



def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
        else:
            # Create a temporary user object for validation
            temp_user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            try:
                # Validate password using Django's built-in validators
                validate_password(password, user=temp_user)
                
                # Create the user - ACTIVE but not approved yet
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    is_active=True,   # ACTIVE - can login
                    is_staff=False     # Regular lecturer, not admin
                )
                
                # Create Lecturer profile - NOT APPROVED
                lecturer_id = f"LEC{user.id:05d}"  # e.g., LEC00001, LEC00002
                
                lecturer = Lecturer.objects.create(
                    user=user,
                    lecturer_id=lecturer_id,
                    department="Pending Assignment",
                    is_approved=False  # NOT APPROVED - needs admin approval
                )
                
                # Create default settings for the lecturer
                LecturerSettings.objects.create(
                    lecturer=lecturer,
                    theme='light',
                    date_format='YYYY-MM-DD',
                    enable_notifications=True,
                    records_per_page=10,
                    workload_target=15
                )
                
                # Auto-login the user
                login(request, user)
                
                messages.success(
                    request, 
                    "Account created successfully! Waiting for admin approval..."
                )
                
                # Redirect to pending approval page
                return redirect('pending_approval')
                
            except ValidationError as e:
                # Display all validation errors
                for error in e.messages:
                    messages.error(request, error)

    return render(request, 'analytics/auth/register.html')

def login_view(request):
    # Clear any old messages from previous sessions
    storage = messages.get_messages(request)
    storage.used = True
    
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.is_staff and request.user.is_active:
            return redirect('dashboard')
        elif request.user.is_active:
            # Check if approved lecturer
            try:
                lecturer = Lecturer.objects.get(user=request.user)
                if lecturer.is_approved:
                    return redirect('home')
                else:
                    return redirect('pending_approval')
            except Lecturer.DoesNotExist:
                return redirect('pending_approval')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')  # 'administrator' or 'lecturer'
        
        user = authenticate(request, username=username, password=password)
        
        if user:
            if not user.is_active:
                messages.error(request, "Your account has been deactivated.")
                return render(request, 'analytics/auth/login.html')
            
            # Role-based validation
            if role == 'administrator':
                # Admin login: Just needs is_staff=True and is_active=True
                if user.is_staff and user.is_active:
                    login(request, user)
                    
                    # Store theme preference
                    try:
                        lecturer = Lecturer.objects.get(user=user)
                        settings = LecturerSettings.objects.get(lecturer=lecturer)
                        request.session['theme'] = settings.theme
                    except:
                        request.session['theme'] = 'light'
                    
                    return redirect('dashboard')
                else:
                    messages.error(request, "You don't have administrator privileges.")
            
            elif role == 'lecturer':
                # Lecturer login: Needs Lecturer profile AND is_approved=True
                # OR is_staff=True (admins can access lecturer area)
                
                if user.is_active:
                    # If admin (staff), allow them in immediately
                    if user.is_staff:
                        login(request, user)
                        
                        # Get or create lecturer profile for admin
                        try:
                            lecturer = Lecturer.objects.get(user=user)
                        except Lecturer.DoesNotExist:
                            # Create admin lecturer profile
                            lecturer = Lecturer.objects.create(
                                user=user,
                                lecturer_id=f"ADMIN{user.id:03d}",
                                department="Administration",
                                is_approved=True  # Auto-approve admins
                            )
                            LecturerSettings.objects.create(lecturer=lecturer)
                        
                        # Get settings
                        settings, _ = LecturerSettings.objects.get_or_create(lecturer=lecturer)
                        request.session['theme'] = settings.theme
                        
                        return redirect('home')
                    
                    # If regular user, check if they have an APPROVED lecturer profile
                    else:
                        try:
                            lecturer = Lecturer.objects.get(user=user)
                            
                            # Check if approved
                            if lecturer.is_approved:
                                login(request, user)
                                
                                # Get settings
                                settings = LecturerSettings.objects.get(lecturer=lecturer)
                                request.session['theme'] = settings.theme
                                
                                return redirect('home')
                            else:
                                # NOT APPROVED - login but redirect to pending page
                                login(request, user)
                                return redirect('pending_approval')
                                
                        except Lecturer.DoesNotExist:
                            messages.error(request, "No lecturer profile found. Please contact the administrator.")
                else:
                    messages.error(request, "Your account has been deactivated.")
            
            else:
                messages.error(request, "Invalid role selected.")
        else:
            messages.error(request, "Invalid username or password")
    
    return render(request, 'analytics/auth/login.html')


@login_required
def pending_approval(request):
    """
    Page shown to users whose accounts are pending admin approval.
    Only accessible to active but unapproved users.
    """
    # Redirect staff/admins
    if request.user.is_staff:
        return redirect('dashboard')
    
    try:
        lecturer = Lecturer.objects.get(user=request.user)
        
        # If already approved, redirect to home
        if lecturer.is_approved:
            return redirect('home')
        
        # Show pending page
        context = {
            'lecturer': lecturer,
            'user': request.user,
        }
        return render(request, 'analytics/auth/pending_approval.html', context)
        
    except Lecturer.DoesNotExist:
        messages.error(request, "No lecturer profile found.")
        return redirect('login')


# Logout view
@login_required(login_url='login')
def logout_view(request):
    user_name = request.user.get_full_name().strip() or request.user.username
    logout(request)

    storage = messages.get_messages(request)
    storage.used = True

    messages.success(request, f"Goodbye {user_name}! You have been logged out successfully.")
    
    return redirect('login')