import os
import json
from datetime import time, datetime, timedelta
import zipfile
from io import BytesIO
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Avg
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from django.db import transaction # <--- ADDED LINE
from analytics.models import Lecturer, TeachingSession, WorkloadPrediction, Subject, TeachingFile, LecturerSettings, AdminSettings
from analytics.services.decorators import admin_required, superadmin_required
from analytics.services.parser import parse_xlsb_and_create_sessions
from analytics.utils import format_date


@admin_required
def dashboard(request):
    """Admin dashboard with system statistics"""
    approved_lecturers = Lecturer.objects.filter(is_approved=True, user__is_staff=False)
    
    # Stats Cards
    active_lecturers_count = approved_lecturers.count()
    pending_approvals_count = Lecturer.objects.filter(is_approved=False, user__is_staff=False).count()
    total_lecturers_count = Lecturer.objects.filter(user__is_staff=False).count()

    total_minutes_agg = TeachingSession.objects.aggregate(total_minutes=Sum('minutes'))
    total_teaching_hours = (total_minutes_agg['total_minutes'] or 0) / 60
    
    total_sessions_count = TeachingSession.objects.count()
    
    all_predictions = WorkloadPrediction.objects.all() # Get all predictions
    total_predictions_count = all_predictions.count()
    workload_alerts = all_predictions.exclude(risk_level='Normal')
    workload_alerts_count = workload_alerts.count()
    overload_count = workload_alerts.filter(risk_level='Overload').count()
    underload_count = workload_alerts.filter(risk_level='Underload').count()
    normal_count = total_predictions_count - workload_alerts_count # Calculate normal predictions

    # Hours by Department
    department_hours = approved_lecturers \
        .values('department') \
        .annotate(total_minutes=Sum('sessions__minutes')) \
        .order_by('-total_minutes')

    # Convert minutes to hours and filter out departments with no hours
    department_hours_list = [
        {
            'department': item['department'],
            'hours': (item['total_minutes'] or 0) / 60
        } for item in department_hours if item['total_minutes']
    ]
    
    # Top 5 Lecturers by Teaching Hours
    top_lecturers_qs = Lecturer.objects.filter(is_approved=True, user__is_staff=False) \
        .annotate(total_minutes=Sum('sessions__minutes')) \
        .order_by('-total_minutes')[:5]

    top_lecturers = []
    for lecturer in top_lecturers_qs:
        total_minutes = lecturer.total_minutes or 0
        hours = total_minutes // 60
        minutes = total_minutes % 60
        top_lecturers.append({
            'lecturer': lecturer,
            'duration': f'{hours}h {minutes}m'
        })

    # Recent File Uploads
    recent_files_qs = TeachingFile.objects.select_related('lecturer__user').order_by('-upload_date')[:5].annotate(
        total_minutes=Sum('sessions__minutes')
    )
    
    recent_files = []
    for file in recent_files_qs:
        total_minutes = file.total_minutes or 0
        hours = total_minutes // 60
        minutes = total_minutes % 60
        recent_files.append({
            'file': file,
            'file_name_only': os.path.basename(file.file_name.name), # Add this line
            'duration': f'{hours}h {minutes}m'
        })

    context = {
        'active_lecturers_count': active_lecturers_count,
        'pending_approvals_count': pending_approvals_count,
        'total_lecturers_count': total_lecturers_count,
        
        'total_teaching_hours': total_teaching_hours,
        'total_sessions_count': total_sessions_count,
        
        'workload_alerts_count': workload_alerts_count,
        'overload_count': overload_count,
        'underload_count': underload_count,
        'total_predictions_count': total_predictions_count,
        'normal_count': normal_count,
        
        'department_hours': department_hours_list,
        'top_lecturers': top_lecturers,
        'recent_files': recent_files,
    }
    
    return render(request, 'analytics/admin/dashboard.html', context)


@admin_required
def lecturers(request):
    """Admin lecturers management page"""
    status = request.GET.get('status', 'all')
    
    # Base query for all non-staff lecturers
    base_query = Lecturer.objects.select_related('user').filter(user__is_staff=False)
    
    # Get counts for tabs
    pending_count = base_query.filter(is_approved=False).count()
    approved_count = base_query.filter(is_approved=True).count()
    all_count = base_query.count()

    # Filter the list for display based on status
    if status == 'pending':
        display_lecturers = base_query.filter(is_approved=False)
    elif status == 'approved':
        display_lecturers = base_query.filter(is_approved=True)
    else: # 'all'
        display_lecturers = base_query
        
    display_lecturers = display_lecturers.order_by('is_approved', 'created_at')

    # Get admin settings for pagination
    try:
        admin_settings = AdminSettings.objects.get(user=request.user)
        records_per_page = admin_settings.default_records_per_page
    except AdminSettings.DoesNotExist:
        records_per_page = 15  # Fallback (as before)

    # Pagination
    paginator = Paginator(display_lecturers, records_per_page)
    page_number = request.GET.get('page', 1)
    if page_number == '':
        page_number = 1
    lecturers_page = paginator.get_page(page_number)

    context = {
        'lecturers': lecturers_page,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'all_count': all_count,
        'current_status': status,
    }
    
    return render(request, 'analytics/admin/lecturers.html', context)

@admin_required
@require_POST
def approve_lecturer(request, lecturer_id):
    """Approve a lecturer's account and activate their user account."""
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    
    with transaction.atomic():
        if not lecturer.is_approved or not lecturer.user.is_active:
            lecturer.is_approved = True
            lecturer.approved_by = request.user
            lecturer.approved_at = timezone.now()
            
            lecturer.user.is_active = True # Activate the associated User account
            lecturer.user.save()
            lecturer.user.refresh_from_db() # Refresh User object
            
            lecturer.save()
            lecturer.refresh_from_db() # Refresh Lecturer object
            
            messages.success(request, f"Lecturer {lecturer.user.get_full_name()} has been approved and activated.")
        else:
            messages.warning(request, f"Lecturer {lecturer.user.get_full_name()} is already approved and active.")
    
    return redirect('lecturers')

@superadmin_required
@require_POST
def activate_admin(request, user_id):
    """Activate an admin user's account (set user.is_active to True)."""
    user = get_object_or_404(User, id=user_id, is_staff=True)
    if not user.is_active:
        user.is_active = True
        user.save()
        messages.success(request, f"Admin user {user.get_full_name() or user.username} has been activated.")
    else:
        messages.warning(request, f"Admin user {user.get_full_name() or user.username} is already active.")
    
    return redirect('manage_admins')

@admin_required
@require_POST
def deactivate_lecturer(request, lecturer_id):
    """Deactivate a lecturer's account (set is_approved to False and user.is_active to False)."""
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)

    with transaction.atomic():
        if lecturer.is_approved or lecturer.user.is_active:
            lecturer.is_approved = False
            lecturer.user.is_active = False # Deactivate the associated User account
            lecturer.user.save()
            lecturer.user.refresh_from_db() # Refresh User object
            
            lecturer.save()
            lecturer.refresh_from_db() # Refresh Lecturer object
            messages.success(request, f"Lecturer {lecturer.user.get_full_name()} has been deactivated.")
        else:
            messages.warning(request, f"Lecturer {lecturer.user.get_full_name()} is already deactivated.")
    
    return redirect('lecturers')

@admin_required
@require_POST
def activate_lecturer(request, lecturer_id):
    """Activate a deactivated lecturer's account."""
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    
    with transaction.atomic():
        # Only proceed if the lecturer is not currently approved and active
        if not lecturer.is_approved or not lecturer.user.is_active:
            lecturer.is_approved = True  # Set to approved
            lecturer.approved_by = request.user # Record who reactivated
            lecturer.approved_at = timezone.now() # Record when reactivated
            
            lecturer.user.is_active = True # Activate the associated User account
            lecturer.user.save()
            lecturer.user.refresh_from_db() # Refresh User object
            
            lecturer.save()
            lecturer.refresh_from_db() # Refresh Lecturer object
            
            messages.success(request, f"Lecturer {lecturer.user.get_full_name()} has been reactivated.")
        else:
            messages.warning(request, f"Lecturer {lecturer.user.get_full_name()} is already active.")
    
    return redirect('lecturers')

@superadmin_required
@require_POST
def deactivate_admin(request, user_id):
    """Deactivate an admin user's account (set user.is_active to False)."""
    user = get_object_or_404(User, id=user_id, is_staff=True)
    if user.is_active:
        if user == request.user:
            messages.error(request, "You cannot deactivate your own admin account.")
            return redirect('manage_admins')
        
        user.is_active = False
        user.save()
        messages.success(request, f"Admin user {user.get_full_name() or user.username} has been deactivated.")
    else:
        messages.warning(request, f"Admin user {user.get_full_name() or user.username} is already deactivated.")
    
    return redirect('manage_admins')

@admin_required
def admin_teaching_records(request):
    """Admin view for all teaching records, with filtering."""
    active_tab = request.GET.get('tab', 'sessions')
    lecturers = Lecturer.objects.filter(is_approved=True).select_related('user')
    selected_lecturer_id = request.GET.get('lecturer')
    
    # Get the selected lecturer object if an ID is provided
    selected_lecturer = None
    if selected_lecturer_id:
        try:
            selected_lecturer = Lecturer.objects.get(id=selected_lecturer_id)
        except Lecturer.DoesNotExist:
            messages.error(request, "Selected lecturer not found.")
            return redirect('admin_teaching_records')

    # Get admin's personal view settings (like sort order, columns)
    try:
        admin_as_lecturer, _ = Lecturer.objects.get_or_create(user=request.user)
        view_settings, _ = LecturerSettings.objects.get_or_create(lecturer=admin_as_lecturer)
    except Exception as e:
        messages.error(request, f"Could not load your personal view settings: {e}")
        view_settings = LecturerSettings()  # Fallback

    # Get system-wide admin settings for date format
    try:
        system_settings = AdminSettings.objects.get(user=request.user)
    except AdminSettings.DoesNotExist:
        # If settings don't exist, create them
        system_settings, _ = AdminSettings.objects.get_or_create(user=request.user)


    # Base query for sessions
    sessions_query = TeachingSession.objects.select_related(
        'subject', 'teaching_file', 'lecturer__user'
    ).order_by(view_settings.default_sort_order)

    # Filter by selected lecturer
    if selected_lecturer:
        sessions_query = sessions_query.filter(lecturer=selected_lecturer)

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        sessions_query = sessions_query.filter(
            Q(subject__subject_code__icontains=search_query) |
            Q(subject__subject_name__icontains=search_query)
        )
    
    # Filter by subject
    selected_subject = request.GET.get('subject', '')
    if selected_subject:
        sessions_query = sessions_query.filter(subject_id=selected_subject)
    
    # Filter by date range
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if date_from:
        sessions_query = sessions_query.filter(date__gte=date_from)
    if date_to:
        sessions_query = sessions_query.filter(date__lte=date_to)
    
    # Filter by time range
    time_from = request.GET.get('time_from', '')
    time_to = request.GET.get('time_to', '')
    
    if time_from:
        try:
            time_from_obj = time.fromisoformat(time_from)
            sessions_query = sessions_query.filter(time_in__gte=time_from_obj)
        except ValueError:
            pass
    
    if time_to:
        try:
            time_to_obj = time.fromisoformat(time_to)
            sessions_query = sessions_query.filter(time_out__lte=time_to_obj)
        except ValueError:
            pass
    
    # Calculate statistics
    total_minutes = 0
    total_sessions = sessions_query.count()
    sessions_list = []
    
    for session in sessions_query:
        # Existing duration calculation logic...
        if session.time_in and session.time_out:
            time_in_dt = datetime.combine(session.date, session.time_in)
            time_out_dt = datetime.combine(session.date, session.time_out)
            if time_out_dt < time_in_dt:
                time_out_dt += timedelta(days=1)
            duration = time_out_dt - time_in_dt
            actual_minutes = int(duration.total_seconds() / 60)
            
            hours_part = actual_minutes // 60
            minutes_part = actual_minutes % 60

            session.hours = hours_part
            session.minutes_part = minutes_part
            session.hours_decimal = round(actual_minutes / 60, 2)
            total_minutes += actual_minutes
        elif session.minutes:
            session.hours = session.minutes // 60
            session.minutes_part = session.minutes % 60
            session.hours_decimal = round(session.minutes / 60, 2)
            total_minutes += session.minutes
        else:
            session.hours = 0
            session.minutes_part = 0
            session.hours_decimal = 0
        
        session.formatted_date = format_date(session.date, system_settings.default_date_format)
        sessions_list.append(session)
    
    total_hours = round(total_minutes / 60, 2) if total_minutes else 0
    avg_per_session = round(total_hours / total_sessions, 2) if total_sessions else 0
    
    # Pagination
    paginator = Paginator(sessions_list, system_settings.default_records_per_page)
    page_number = request.GET.get('page', 1)
    if page_number == '':
        page_number = 1
    sessions = paginator.get_page(page_number)
    
    # Get subjects for filter dropdown
    subjects_query = Subject.objects.all()
    if selected_lecturer:
        subjects_query = subjects_query.filter(sessions__lecturer=selected_lecturer)
    subjects = subjects_query.distinct().order_by('subject_code')

    # Get files for the selected lecturer or all files
    files_query = TeachingFile.objects.select_related('lecturer__user')
    if selected_lecturer:
        files_query = files_query.filter(lecturer=selected_lecturer)
        
    files_list = files_query.annotate(
        sessions_count=Count('sessions')
    ).order_by('-upload_date')
    
    # File statistics
    total_files = files_list.count()
    parsed_files = files_list.filter(sessions_count__gt=0).count()
    pending_files = total_files - parsed_files

    # For searchable dropdown
    lecturers_for_js = [{'id': lec.id, 'name': lec.user.get_full_name() or lec.user.username} for lec in lecturers]

    # Build filter params for pagination links
    filter_params = request.GET.copy()
    if 'page' in filter_params:
        del filter_params['page']

    ordered_columns = system_settings.default_columns if system_settings.default_columns else []

    context = {
        'sessions': sessions,
        'subjects': subjects,
        'lecturers': lecturers,
        'lecturers_json': json.dumps(lecturers_for_js),
        'selected_lecturer': selected_lecturer,
        'selected_subject': selected_subject,
        'search_query': search_query,
        'filter_params': filter_params.urlencode(),
        'date_from': date_from,
        'date_to': date_to,
        'time_from': time_from,
        'time_to': time_to,
        'files': files_list,
        'stats': {
            'total_sessions': total_sessions,
            'total_hours': total_hours,
            'avg_per_session': avg_per_session,
        },
        'file_stats': {
            'total': total_files,
            'parsed': parsed_files,
            'pending': pending_files,
        },
        'settings': view_settings,
        'system_settings': system_settings,
        'ordered_columns': ordered_columns,
        'active_tab': active_tab,
    }
    
    return render(request, 'analytics/admin/teaching_records.html', context)

@admin_required
@require_POST
def admin_upload_files(request):
    """Admin view for uploading files on behalf of lecturers."""
    lecturer_id = request.POST.get('lecturer')
    files = request.FILES.getlist('files')
    auto_parse = request.POST.get('auto_parse') == 'on'

    if not lecturer_id:
        messages.error(request, "Please select a lecturer.")
        return redirect('admin_teaching_records')
    
    if not files:
        messages.error(request, "Please select a file to upload.")
        return redirect('admin_teaching_records')

    # Get admin settings for validation
    try:
        admin_settings = AdminSettings.objects.get(user=request.user)
    except AdminSettings.DoesNotExist:
        messages.error(request, "File upload settings are not configured.")
        return redirect('admin_teaching_records')

    max_size_bytes = admin_settings.max_file_size_mb * 1024 * 1024
    allowed_types = [ft.strip().lower() for ft in admin_settings.allowed_file_types.split(',')]

    validation_errors = []
    for file in files:
        if file.size > max_size_bytes:
            validation_errors.append(f"'{file.name}' exceeds the maximum file size of {admin_settings.max_file_size_mb} MB.")
        
        file_ext = f".{file.name.split('.')[-1].lower()}"
        if file_ext not in allowed_types:
            validation_errors.append(f"'{file.name}' has an invalid file type. Allowed types are {', '.join(allowed_types)}.")

    if validation_errors:
        for error in validation_errors:
            messages.error(request, error)
        return redirect('admin_teaching_records')

    try:
        lecturer = Lecturer.objects.get(id=lecturer_id)
        
        uploaded_files = []
        errors = []

        for file in files:
            if file.name.lower().endswith('.zip'):
                try:
                    zip_data = BytesIO(file.read())
                    with zipfile.ZipFile(zip_data, 'r') as zip_ref:
                        xlsb_found = False
                        for zip_info in zip_ref.namelist():
                            if zip_info.lower().endswith('.xlsb') and not zip_info.startswith('__MACOSX'):
                                xlsb_found = True
                                xlsb_data = zip_ref.read(zip_info)
                                xlsb_name = zip_info.split('/')[-1]
                                xlsb_file = ContentFile(xlsb_data, name=xlsb_name)
                                teaching_file = TeachingFile.objects.create(lecturer=lecturer, file_name=xlsb_file)
                                uploaded_files.append(teaching_file)
                        if not xlsb_found:
                            errors.append(f"No .xlsb files found in '{file.name}'.")
                except zipfile.BadZipFile:
                    errors.append(f"'{file.name}' is not a valid ZIP file.")
                except Exception as e:
                    errors.append(f"Error processing ZIP '{file.name}': {e}")
            
            elif file.name.lower().endswith('.xlsb'):
                teaching_file = TeachingFile.objects.create(lecturer=lecturer, file_name=file)
                uploaded_files.append(teaching_file)
            else:
                # This should be caught by the validation above, but is kept as a safeguard
                errors.append(f"'{file.name}' is not a valid XLSB or ZIP file and was skipped.")

        if errors:
            for error in errors:
                messages.warning(request, error)

        if not uploaded_files:
            messages.error(request, "No valid files were uploaded.")
            return redirect(f"{reverse('admin_teaching_records')}?tab=files&lecturer={lecturer_id}")

        total_sessions_created = 0
        if auto_parse:
            for tf in uploaded_files:
                try:
                    created_count = parse_xlsb_and_create_sessions(tf)
                    total_sessions_created += created_count
                except Exception as e:
                    messages.error(request, f"Error parsing file '{tf.file_name.name}': {e}")
        
        if uploaded_files:
            if auto_parse:
                messages.success(request, f"Successfully uploaded and parsed {len(uploaded_files)} file(s), creating {total_sessions_created} sessions for {lecturer.user.get_full_name()}.")
            else:
                messages.success(request, f"Successfully uploaded {len(uploaded_files)} file(s) for {lecturer.user.get_full_name()}. Parsing was not requested.")

    except Lecturer.DoesNotExist:
        messages.error(request, "The selected lecturer does not exist.")
        return redirect('admin_teaching_records')
    
    redirect_url = f"{reverse('admin_teaching_records')}?tab=files&lecturer={lecturer_id}"
    return redirect(redirect_url)

@admin_required
def admin_workload_prediction(request):
    """Admin view for all workload predictions."""
    predictions = WorkloadPrediction.objects.select_related('lecturer__user', 'subject').order_by('-created_at')

    total_predictions = predictions.count()
    workload_alerts = predictions.exclude(risk_level='Normal')
    workload_alerts_count = workload_alerts.count()
    overload_count = workload_alerts.filter(risk_level='Overload').count()
    underload_count = workload_alerts.filter(risk_level='Underload').count()
    normal_count = total_predictions - workload_alerts_count
    
    context = {
        'predictions': predictions,
        'total_predictions': total_predictions,
        'workload_alerts_count': workload_alerts_count,
        'overload_count': overload_count,
        'underload_count': underload_count,
        'normal_count': normal_count,
    }
    return render(request, 'analytics/admin/workload_prediction.html', context)

@admin_required
def admin_settings(request):
    """Admin view for managing system-wide settings."""
    # Define available columns for teaching records
    # This list should be comprehensive for an admin's view
    available_record_columns = [
        'lecturer',
        'subject',
        'date',
        'duration',
        'lecture_type',
        'time_in',
        'time_out',
        'source_file',
        # Add any other relevant columns an admin might want to see
    ]

    if request.method == 'POST':
        with transaction.atomic():
            # Get the settings object within the transaction context
            # It's better to fetch it directly inside, in case get_or_create has its own caching
            # Use get_or_create for robustness if it somehow doesn't exist
            settings, created = AdminSettings.objects.get_or_create(user=request.user)

            settings.default_theme = request.POST.get('default_theme', 'light')
            settings.default_date_format = request.POST.get('default_date_format', 'YYYY-MM-DD')
            settings.default_records_per_page = int(request.POST.get('default_records_per_page', 15))

            settings.default_workload_target = int(request.POST.get('default_workload_target', 20))
            settings.risk_threshold_overload = int(request.POST.get('risk_threshold_overload', 125))
            settings.risk_threshold_underload = int(request.POST.get('risk_threshold_underload', 75))

            settings.allowed_file_types = request.POST.get('allowed_file_types', '.xlsb,.zip')
            settings.max_file_size_mb = int(request.POST.get('max_file_size_mb', 15))
            settings.semester_workload_target = int(request.POST.get('semester_workload_target', 180))

            # Handle default_columns WITH ORDER
            default_columns_str = request.POST.get('default_columns', '')
            if default_columns_str:
                settings.default_columns = [col.strip() for col in default_columns_str.split(',') if col.strip()]
            else:
                settings.default_columns = []

            # Save with explicit update_fields
            settings.save(update_fields=[
                'default_theme', 'default_date_format', 'default_records_per_page',
                'default_workload_target', 'risk_threshold_overload', 'risk_threshold_underload',
                'allowed_file_types', 'max_file_size_mb', 'semester_workload_target',
                'default_columns'
            ])
            
            # Explicitly refresh from DB to clear ORM cache within this request if needed
            settings.refresh_from_db()

        messages.success(request, "Admin settings have been successfully updated.")
        return redirect('admin_settings') # Triggers a new GET request

    else: # GET request
        # Fetch the settings for rendering. Ensure it's the latest.
        # Use get_or_create to handle cases where settings might not exist yet.
        settings, created = AdminSettings.objects.get_or_create(user=request.user)
        # Explicitly refresh from DB just before rendering to ensure no stale data
        settings.refresh_from_db()

        # Ensure default_columns is never empty for existing objects
        if not settings.default_columns: # Checks for empty list or None
            settings.default_columns = ['lecturer', 'subject', 'date', 'duration']
            settings.save(update_fields=['default_columns']) # Save this default back to DB
            settings.refresh_from_db() # Refresh again to confirm saved state
            
    context = {
        'settings': settings,
        'available_record_columns': available_record_columns,
    }
    return render(request, 'analytics/admin/settings.html', context)

from django.contrib.auth.hashers import make_password

@admin_required
def edit_lecturer(request, lecturer_id):
    """Admin view for editing a lecturer's details."""
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    if request.method == 'POST':
        # Update user details
        lecturer.user.first_name = request.POST.get('first_name', '').strip()
        lecturer.user.last_name = request.POST.get('last_name', '').strip()
        lecturer.user.email = request.POST.get('email', '').strip()
        lecturer.user.save()
        
        # Update lecturer details
        lecturer.department = request.POST.get('department', '').strip()
        lecturer.save()
        
        messages.success(request, f"Successfully updated details for {lecturer.user.get_full_name()}.")
        return redirect('lecturers')
        
    context = {
        'lecturer': lecturer,
    }
    return render(request, 'analytics/admin/edit_lecturer.html', context)

@admin_required
def create_lecturer(request):
    """Admin view for creating a new lecturer."""
    if request.method == 'POST':
        # Create user
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        department = request.POST.get('department', '').strip()

        if not all([username, email, password, first_name, last_name, department]):
            messages.error(request, "All fields are required.")
            return redirect('lecturers')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect('lecturers')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' already exists.")
            return redirect('lecturers')

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Create lecturer profile
            lecturer = Lecturer.objects.create(
                user=user,
                lecturer_id=f"LEC{user.id:05d}",
                department=department,
                is_approved=True,
                approved_by=request.user
            )

            # Create default settings for the lecturer
            LecturerSettings.objects.create(
                lecturer=lecturer,
                theme='light',
                date_format='YYYY-MM-DD',
                enable_notifications=True,
                records_per_page=10
            )
            messages.success(request, f"Successfully created lecturer {first_name} {last_name}.")
            return redirect('lecturers')
        except Exception as e:
            messages.error(request, f"Failed to create lecturer: {e}")
            return redirect('lecturers')

    return redirect('lecturers')

@superadmin_required
def manage_admins(request):
    """Superadmin view for managing administrators."""
    admins_query = User.objects.filter(is_staff=True).order_by('-is_superuser', '-date_joined')
    
    # Get admin settings for pagination
    try:
        admin_settings = AdminSettings.objects.get(user=request.user)
        records_per_page = admin_settings.default_records_per_page
    except AdminSettings.DoesNotExist:
        records_per_page = 15  # Fallback (as before)

    # Pagination
    paginator = Paginator(admins_query, records_per_page)
    page_number = request.GET.get('page', 1)
    if page_number == '':
        page_number = 1
    admins_page = paginator.get_page(page_number)
    
    context = {
        'admins': admins_page,
    }
    
    return render(request, 'analytics/admin/manage_admins.html', context)

@superadmin_required
def create_admin(request):
    """Superadmin view for creating a new admin."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        is_superuser = request.POST.get('is_superuser') == 'on'

        if not all([username, email, password, first_name, last_name]):
            messages.error(request, "All fields are required.")
            return redirect('manage_admins')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect('manage_admins')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"Email '{email}' already exists.")
            return redirect('manage_admins')

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_superuser=is_superuser
            )
            messages.success(request, f"Successfully created admin {first_name} {last_name}.")
            return redirect('manage_admins')
        except Exception as e:
            messages.error(request, f"Failed to create admin: {e}")
            return redirect('manage_admins')

    return redirect('manage_admins')


@superadmin_required
def edit_admin(request, user_id):
    """Superadmin view for editing an administrator's details."""
    admin_user = get_object_or_404(User, id=user_id, is_staff=True)
    if request.method == 'POST':
        admin_user.first_name = request.POST.get('first_name', '').strip()
        admin_user.last_name = request.POST.get('last_name', '').strip()
        admin_user.email = request.POST.get('email', '').strip()
        
        # Prevent a user from removing their own superuser status
        if admin_user == request.user and not request.POST.get('is_superuser') == 'on':
            messages.warning(request, "You cannot remove your own superuser status.")
        else:
            admin_user.is_superuser = request.POST.get('is_superuser') == 'on'
        
        admin_user.save()
        
        messages.success(request, f"Successfully updated details for {admin_user.get_full_name()}.")
        return redirect('manage_admins')
        
    context = {
        'admin': admin_user,
    }
    return render(request, 'analytics/admin/edit_admin.html', context)

@admin_required
def recalculate_workload_predictions(request):
    """
    Manually triggers the workload prediction calculation for all lecturers.
    """
    from analytics.services.workload_service import update_workload_predictions
    
    try:
        update_workload_predictions()
        messages.success(request, "Successfully recalculated workload predictions for all approved lecturers.")
    except Exception as e:
        messages.error(request, f"An error occurred while recalculating predictions: {e}")
        
    return redirect('admin_workload_prediction')
