from datetime import time, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Avg
from django.core.paginator import Paginator
from django.db.models import Q
from analytics.models import Lecturer, TeachingSession, WorkloadPrediction, Subject, TeachingFile, LecturerSettings
from analytics.services.decorators import admin_required, superadmin_required
from analytics.utils import format_date


@admin_required
def dashboard(request):
    """Admin dashboard with system statistics"""
    approved_lecturers = Lecturer.objects.filter(is_approved=True, user__is_staff=False)
    
    # Stats Cards
    active_lecturers_count = approved_lecturers.count()
    pending_approvals_count = Lecturer.objects.filter(is_approved=False, user__is_staff=False).count()
    
    total_minutes_agg = TeachingSession.objects.aggregate(total_minutes=Sum('minutes'))
    total_teaching_hours = (total_minutes_agg['total_minutes'] or 0) / 60
    
    total_sessions_count = TeachingSession.objects.count()
    
    workload_alerts = WorkloadPrediction.objects.exclude(risk_level='Normal')
    workload_alerts_count = workload_alerts.count()
    overload_count = workload_alerts.filter(risk_level='Overload').count()
    underload_count = workload_alerts.filter(risk_level='Underload').count()

    # Hours by Department
    department_hours = Lecturer.objects.filter(is_approved=True, user__is_staff=False) \
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
    
    # Workload Status & Recent Sessions
    workload_status = WorkloadPrediction.objects.select_related('lecturer__user', 'subject').order_by('-created_at')[:5]
    recent_sessions = TeachingSession.objects.select_related('lecturer__user', 'subject').order_by('-date', '-time_in')[:5]

    context = {
        'active_lecturers_count': active_lecturers_count,
        'pending_approvals_count': pending_approvals_count,
        'total_lecturers': active_lecturers_count + pending_approvals_count,
        
        'total_teaching_hours': total_teaching_hours,
        'total_sessions_count': total_sessions_count,
        
        'workload_alerts_count': workload_alerts_count,
        'overload_count': overload_count,
        'underload_count': underload_count,
        
        'department_hours': department_hours_list,
        'workload_status': workload_status,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'analytics/admin/dashboard.html', context)


@admin_required
def lecturers(request):
    """Admin lecturers management page"""
    lecturers_list = Lecturer.objects.select_related('user').order_by('is_approved', 'created_at')
    
    context = {
        'lecturers': lecturers_list,
        'pending_count': Lecturer.objects.filter(is_approved=False, user__is_staff=False).count(),
        'approved_count': Lecturer.objects.filter(is_approved=True, user__is_staff=False).count(),
    }
    
    return render(request, 'analytics/admin/lecturers.html', context)

@admin_required
@require_POST
def approve_lecturer(request, lecturer_id):
    """Approve a lecturer's account."""
    lecturer = get_object_or_404(Lecturer, id=lecturer_id)
    if not lecturer.is_approved:
        lecturer.is_approved = True
        lecturer.approved_by = request.user
        lecturer.approved_at = timezone.now()
        lecturer.save()
        messages.success(request, f"Lecturer {lecturer.user.get_full_name()} has been approved.")
    else:
        messages.warning(request, f"Lecturer {lecturer.user.get_full_name()} is already approved.")
    
    return redirect('lecturers')

@admin_required
def admin_teaching_records(request):
    """Admin view for all teaching records, with filtering."""
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

    # Always use the admin's settings
    try:
        admin_lecturer, created = Lecturer.objects.get_or_create(user=request.user)
        settings, created = LecturerSettings.objects.get_or_create(lecturer=admin_lecturer)
    except Exception as e:
        messages.error(request, f"Could not load admin settings: {e}")
        settings = LecturerSettings() # Fallback to default settings


    # Base query for sessions
    sessions_query = TeachingSession.objects.select_related(
        'subject', 'teaching_file', 'lecturer__user'
    ).order_by(settings.default_sort_order)

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
        
        session.formatted_date = format_date(session.date, settings.date_format)
        sessions_list.append(session)
    
    total_hours = round(total_minutes / 60, 2) if total_minutes else 0
    avg_per_session = round(total_hours / total_sessions, 2) if total_sessions else 0
    
    # Pagination
    paginator = Paginator(sessions_list, settings.records_per_page)
    page_number = request.GET.get('page', 1)
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

    # Build filter params for pagination links
    filter_params = request.GET.copy()
    if 'page' in filter_params:
        del filter_params['page']

    ordered_columns = settings.default_columns.split(',') if settings.default_columns else []
    if 'lecturer' not in ordered_columns:
        ordered_columns.insert(0, 'lecturer')

    context = {
        'sessions': sessions,
        'subjects': subjects,
        'lecturers': lecturers,
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
        'settings': settings,
        'ordered_columns': ordered_columns,
    }
    
    return render(request, 'analytics/admin/teaching_records.html', context)

@admin_required
@require_POST
def admin_upload_files(request):
    """Admin view for uploading files on behalf of lecturers."""
    lecturer_id = request.POST.get('lecturer')
    files = request.FILES.getlist('file')

    if not lecturer_id:
        messages.error(request, "Please select a lecturer.")
        return redirect('admin_teaching_records')
    
    if not files:
        messages.error(request, "Please select a file to upload.")
        return redirect('admin_teaching_records')

    try:
        lecturer = Lecturer.objects.get(id=lecturer_id)
        for f in files:
            TeachingFile.objects.create(lecturer=lecturer, file_name=f)
        messages.success(request, f"Successfully uploaded {len(files)} file(s) for {lecturer.user.get_full_name()}.")
    except Lecturer.DoesNotExist:
        messages.error(request, "The selected lecturer does not exist.")
    
    return redirect('admin_teaching_records')

@admin_required
def admin_workload_prediction(request):
    """Admin view for all workload predictions."""
    predictions = WorkloadPrediction.objects.select_related('lecturer__user', 'subject').order_by('-created_at')
    context = {
        'predictions': predictions,
    }
    return render(request, 'analytics/admin/workload_prediction.html', context)

@admin_required
def admin_settings(request):
    """Admin view for settings."""
    return render(request, 'analytics/admin/settings.html')

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
                records_per_page=10,
                workload_target=15
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
    admins = User.objects.filter(is_staff=True).order_by('-is_superuser', '-date_joined')
    
    context = {
        'admins': admins,
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
