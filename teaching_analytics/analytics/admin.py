from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
from .models import (
    Lecturer,
    Subject,
    TeachingFile,
    TeachingSession,
    TeachingSummary,
    WorkloadPrediction,
)
from .services.parser import parse_xlsb_and_create_sessions
from .services.summary_service import generate_summary
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from analytics.models import Lecturer, LecturerSettings
from analytics.services.decorators import admin_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html

# ----------------------------
# Lecturer Admin
# ----------------------------
@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = (
        "lecturer_id",
        "user_full_name",
        "user_email",
        "department",
        "approval_status",
        "created_at",
        "quick_actions",
    )
    list_filter = ("is_approved", "department", "created_at")
    search_fields = ("lecturer_id", "user__username", "user__first_name", "user__last_name", "user__email")
    ordering = ("-created_at",)
    
    # Make approval fields read-only (they're set automatically)
    readonly_fields = ("approved_by", "approved_at", "created_at")
    
    # Custom display methods
    def user_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_full_name.short_description = "Name"
    user_full_name.admin_order_field = "user__first_name"
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email"
    user_email.admin_order_field = "user__email"
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: #28a745;">{}</span>', '✓ Approved')
        return format_html('<span style="color: #ffc107;">{}</span>', '⏳ Pending')
    approval_status.short_description = "Status"
    approval_status.admin_order_field = "is_approved"
    
    def quick_actions(self, obj):
        if not obj.is_approved:
            url = f'/admin/analytics/lecturer/{obj.pk}/approve/'
            return format_html('<a class="button" href="{}">{}</a>', url, 'Approve')
        return "—"
    quick_actions.short_description = "Quick Actions"
    
    # Custom URLs for approve action
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:lecturer_id>/approve/',
                self.admin_site.admin_view(self.approve_lecturer),
                name='analytics_lecturer_approve',
            ),
        ]
        return custom_urls + urls
    
    def approve_lecturer(self, request, lecturer_id):
        """Quick approve a lecturer"""
        lecturer = Lecturer.objects.get(pk=lecturer_id)
        
        # Directly approve without confirmation page
        lecturer.is_approved = True
        lecturer.approved_by = request.user
        lecturer.approved_at = timezone.now()
        lecturer.save()
        
        # Ensure settings exist
        LecturerSettings.objects.get_or_create(
            lecturer=lecturer,
            defaults={
                'theme': 'light',
                'date_format': 'YYYY-MM-DD',
                'enable_notifications': True,
                'records_per_page': 10,
                'workload_target': 15
            }
        )
        
        self.message_user(
            request,
            f"✓ Lecturer '{lecturer.user.get_full_name()}' ({lecturer.lecturer_id}) has been approved!",
            messages.SUCCESS
        )
        return redirect('admin:analytics_lecturer_changelist')
    
    # Admin actions for bulk operations
    actions = ['approve_selected_lecturers', 'reject_selected_lecturers']
    
    @admin.action(description='✓ Approve selected lecturers')
    def approve_selected_lecturers(self, request, queryset):
        """Approve multiple lecturers at once"""
        unapproved = queryset.filter(is_approved=False)
        count = unapproved.count()
        
        if count == 0:
            self.message_user(request, "No unapproved lecturers selected.", messages.WARNING)
            return
        
        # Approve all
        for lecturer in unapproved:
            lecturer.is_approved = True
            lecturer.approved_by = request.user
            lecturer.approved_at = timezone.now()
            lecturer.save()
            
            # Ensure settings exist
            LecturerSettings.objects.get_or_create(
                lecturer=lecturer,
                defaults={
                    'theme': 'light',
                    'date_format': 'YYYY-MM-DD',
                    'enable_notifications': True,
                    'records_per_page': 10,
                    'workload_target': 15
                }
            )
        
        self.message_user(
            request,
            f"✓ Successfully approved {count} lecturer(s).",
            messages.SUCCESS
        )
    
    @admin.action(description='✗ Reject selected lecturers')
    def reject_selected_lecturers(self, request, queryset):
        """Reject and delete selected lecturers"""
        pending = queryset.filter(is_approved=False)
        count = pending.count()
        
        if count == 0:
            self.message_user(request, "No pending lecturers selected.", messages.WARNING)
            return
        
        # Delete users (cascade will delete lecturer profiles)
        for lecturer in pending:
            lecturer.user.delete()
        
        self.message_user(
            request,
            f"✗ Successfully rejected and deleted {count} lecturer(s).",
            messages.SUCCESS
        )
    
    # Customize form fields
    def get_fieldsets(self, request, obj=None):
        """Organize fields into logical groups"""
        if obj is None:  # Creating new lecturer
            return (
                ('User Account', {
                    'fields': ('user',)
                }),
                ('Lecturer Information', {
                    'fields': ('lecturer_id', 'department', 'hourly_rate')
                }),
            )
        else:  # Editing existing lecturer
            if obj.is_approved:
                return (
                    ('User Account', {
                        'fields': ('user',)
                    }),
                    ('Lecturer Information', {
                        'fields': ('lecturer_id', 'department', 'hourly_rate')
                    }),
                    ('Approval Information', {
                        'fields': ('is_approved', 'approved_by', 'approved_at', 'created_at'),
                        'classes': ('collapse',),
                    }),
                )
            else:
                return (
                    ('User Account', {
                        'fields': ('user',)
                    }),
                    ('Lecturer Information', {
                        'fields': ('lecturer_id', 'department', 'hourly_rate')
                    }),
                    ('Approval Status', {
                        'fields': ('is_approved', 'created_at'),
                        'description': 'This lecturer is pending approval. Use the "Approve" button in the list view to approve quickly.'
                    }),
                )


# ----------------------------
# Subject Admin
# ----------------------------
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "subject_code",
        "subject_name",
        "degree_level",
        "major",
    )
    search_fields = ("subject_code", "subject_name", "major")
    list_filter = ("degree_level", "major")
    ordering = ("subject_code",)


# ----------------------------
# Teaching File Admin
# ----------------------------
@admin.action(description="Parse XLSB → Create Teaching Sessions")
def parse_xlsb_files(modeladmin, request, queryset):
    total_created = 0
    total_updated = 0
    errors = []
    
    for teaching_file in queryset:
        try:
            created = parse_xlsb_and_create_sessions(teaching_file)
            total_created += created
        except Exception as e:
            errors.append(f"{teaching_file.file_name.name}: {str(e)}")

    if total_created > 0:
        modeladmin.message_user(
            request, 
            f"Successfully created {total_created} teaching sessions.",
            level="success"
        )
    
    if errors:
        error_msg = "Errors occurred:\n" + "\n".join(errors)
        modeladmin.message_user(request, error_msg, level="error")


@admin.register(TeachingFile)
class TeachingFileAdmin(admin.ModelAdmin):
    list_display = (
        "file_name",
        "lecturer",
        "semester",
        "upload_date",
    )
    search_fields = ("file_name", "lecturer__lecturer_id", "semester")
    list_filter = ("semester", "upload_date", "lecturer")
    ordering = ("-upload_date",)
    actions = [parse_xlsb_files]
    
    # Semester is auto-filled by parser, so it's always readonly
    readonly_fields = ("upload_date", "semester")
    
    def get_fields(self, request, obj=None):
        # When adding new file (obj is None), only show lecturer and file_name
        if obj is None:
            return ("lecturer", "file_name")
        # When editing existing file, show all fields including auto-filled semester
        return ("lecturer", "file_name", "semester", "upload_date")
    
    def get_urls(self):
        """Add custom URL for bulk upload"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-upload/',
                self.admin_site.admin_view(self.bulk_upload_view),
                name='analytics_teachingfile_bulk_upload',
            ),
        ]
        return custom_urls + urls
    
    def bulk_upload_view(self, request):
        """Handle bulk file upload"""
        if request.method == 'POST':
            lecturer_id = request.POST.get('lecturer')
            files = request.FILES.getlist('files')
            auto_parse = request.POST.get('auto_parse') == 'on'
            
            if not lecturer_id:
                messages.error(request, "Please select a lecturer.")
                return redirect('.')
            
            if not files:
                messages.error(request, "Please select at least one file.")
                return redirect('.')
            
            try:
                lecturer = Lecturer.objects.get(id=lecturer_id)
                uploaded_files = []
                total_created = 0
                errors = []
                
                # Upload all files
                for file in files:
                    # Validate file extension
                    if not file.name.endswith('.xlsb'):
                        errors.append(f"{file.name}: Not an XLSB file")
                        continue
                    
                    # Create TeachingFile record
                    teaching_file = TeachingFile.objects.create(
                        lecturer=lecturer,
                        file_name=file,
                        semester=""  # Will be auto-filled by parser
                    )
                    uploaded_files.append(teaching_file)
                
                # Auto-parse if requested
                if auto_parse and uploaded_files:
                    for teaching_file in uploaded_files:
                        try:
                            created = parse_xlsb_and_create_sessions(teaching_file)
                            total_created += created
                        except Exception as e:
                            errors.append(f"{teaching_file.file_name.name}: {str(e)}")
                
                # Show results
                if uploaded_files:
                    if auto_parse:
                        messages.success(
                            request,
                            f"Successfully uploaded {len(uploaded_files)} files and created {total_created} teaching sessions."
                        )
                    else:
                        messages.success(
                            request,
                            f"Successfully uploaded {len(uploaded_files)} files. Use 'Parse XLSB' action to process them."
                        )
                
                if errors:
                    messages.warning(request, "Some errors occurred:\n" + "\n".join(errors))
                
                return redirect('..')
                
            except Lecturer.DoesNotExist:
                messages.error(request, "Lecturer not found.")
                return redirect('.')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
                import traceback
                traceback.print_exc()
                return redirect('.')
        
        # GET request - show form
        lecturers = Lecturer.objects.all().order_by('lecturer_id')
        context = {
            'title': 'Bulk Upload Teaching Files',
            'lecturers': lecturers,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/analytics/teachingfile/bulk_upload.html', context)
    
    def changelist_view(self, request, extra_context=None):
        """Add bulk upload button to changelist"""
        extra_context = extra_context or {}
        extra_context['bulk_upload_url'] = 'bulk-upload/'
        return super().changelist_view(request, extra_context=extra_context)


# ----------------------------
# Teaching Session Admin (CORE)
# ----------------------------
@admin.action(description="Generate Teaching Summary (Single/Multiple Subjects)")
def generate_summary_action(modeladmin, request, queryset):
    if not queryset.exists():
        modeladmin.message_user(
            request,
            "No sessions selected.",
            level="warning"
        )
        return

    # Check if all sessions are for the same lecturer
    lecturers = queryset.values_list("lecturer", flat=True).distinct()
    if lecturers.count() > 1:
        modeladmin.message_user(
            request,
            "Please select sessions for ONE lecturer only.",
            level="error"
        )
        return

    # Get subjects and date range
    lecturer = queryset.first().lecturer
    subject_ids = queryset.values_list("subject", flat=True).distinct()
    subjects = Subject.objects.filter(id__in=subject_ids)
    
    start_date = queryset.earliest("date").date
    end_date = queryset.latest("date").date

    # Import the enhanced summary service
    from .services.summary_service import generate_multi_subject_summaries, format_summary_report

    try:
        # Generate summaries
        result = generate_multi_subject_summaries(
            lecturer=lecturer,
            subjects=list(subjects),
            start_date=start_date,
            end_date=end_date
        )
        
        # Format and print report to console
        report = format_summary_report(
            result['individual_summaries'],
            result['consolidated_summary']
        )
        print("\n" + report)
        
        # Show success message
        individual_count = len(result['individual_summaries'])
        has_consolidated = result['consolidated_summary'] is not None
        
        if individual_count == 1 and not has_consolidated:
            message = f"Generated summary for 1 subject."
        elif individual_count > 1:
            message = f"Generated {individual_count} individual summaries + 1 consolidated summary."
        else:
            message = "No summaries generated (no valid sessions found)."
        
        modeladmin.message_user(request, message, level="success")
        
    except Exception as e:
        modeladmin.message_user(
            request,
            f"Error generating summaries: {str(e)}",
            level="error"
        )
        import traceback
        traceback.print_exc()


@admin.register(TeachingSession)
class TeachingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "lecturer",
        "subject",
        "minutes",
        "week_number",
        "month",
    )
    search_fields = (
        "lecturer__lecturer_id",
        "subject__subject_code",
    )
    list_filter = (
        "lecturer",
        "subject",
        "month",
        "week_number",
    )
    ordering = ("-date",)
    date_hierarchy = "date"
    actions = [generate_summary_action]


# ----------------------------
# Teaching Summary Admin
# ----------------------------
@admin.register(TeachingSummary)
class TeachingSummaryAdmin(admin.ModelAdmin):
    list_display = (
        "lecturer",
        "subject",
        "start_date",
        "end_date",
        "total_hours_display",
        "average_minutes_per_week",
        "completion_percentage",
        "created_at",
    )
    list_filter = ("lecturer", "subject", "created_at")
    ordering = ("-created_at",)
    search_fields = ("lecturer__lecturer_id", "subject__subject_code", "subject__subject_name")
    
    def total_hours_display(self, obj):
        """Display total time in hours and minutes"""
        hours = obj.total_minutes // 60
        minutes = obj.total_minutes % 60
        return f"{hours}h {minutes}m"
    total_hours_display.short_description = "Total Time"
    
    # Make most fields read-only since they're auto-generated
    readonly_fields = (
        "lecturer",
        "subject",
        "start_date",
        "end_date",
        "total_minutes",
        "average_minutes_per_week",
        "completion_percentage",
        "created_at",
    )


# ----------------------------
# Workload Prediction Admin
# ----------------------------
@admin.register(WorkloadPrediction)
class WorkloadPredictionAdmin(admin.ModelAdmin):
    list_display = (
        "lecturer",
        "subject",
        "current_minutes",
        "predicted_total_minutes",
        "remaining_weeks",
        "risk_level",
        "created_at",
    )
    list_filter = ("risk_level", "lecturer", "subject")
    ordering = ("-created_at",)



@admin_required
def pending_users(request):
    """
    Display pending lecturer approvals.
    Shows all lecturers with is_approved=False
    """
    # Get all lecturers pending approval (not approved yet)
    pending_lecturers = Lecturer.objects.filter(
        is_approved=False
    ).select_related('user').order_by('-created_at')
    
    context = {
        'pending_lecturers': pending_lecturers,
    }
    
    return render(request, 'analytics/admin/pending_users.html', context)


@admin_required
def approve_user(request, user_id):
    """
    Approve a pending lecturer.
    Sets is_approved=True and updates department if provided.
    """
    if request.method != 'POST':
        return redirect('pending_users')
    
    user = get_object_or_404(User, id=user_id)
    
    try:
        lecturer = Lecturer.objects.get(user=user)
    except Lecturer.DoesNotExist:
        messages.error(request, "No lecturer profile found for this user.")
        return redirect('pending_users')
    
    # Get form data
    department = request.POST.get('department', lecturer.department)
    lecturer_id = request.POST.get('lecturer_id', lecturer.lecturer_id)
    
    # Validate lecturer_id
    if not lecturer_id:
        messages.error(request, "Lecturer ID is required.")
        return redirect('pending_users')
    
    # Check if lecturer_id is already taken by another lecturer
    if Lecturer.objects.filter(lecturer_id=lecturer_id).exclude(id=lecturer.id).exists():
        messages.error(request, f"Lecturer ID '{lecturer_id}' is already in use.")
        return redirect('pending_users')
    
    try:
        # Update lecturer profile
        lecturer.lecturer_id = lecturer_id
        lecturer.department = department
        lecturer.is_approved = True
        lecturer.approved_by = request.user
        lecturer.approved_at = timezone.now()
        lecturer.save()
        
        # Ensure settings exist
        LecturerSettings.objects.get_or_create(
            lecturer=lecturer,
            defaults={
                'theme': 'light',
                'date_format': 'YYYY-MM-DD',
                'enable_notifications': True,
                'records_per_page': 10,
                'workload_target': 15
            }
        )
        
        messages.success(
            request, 
            f"Lecturer '{user.get_full_name()}' has been approved with ID: {lecturer_id}"
        )
        
        # TODO: Send email notification to user about approval
        
    except Exception as e:
        messages.error(request, f"Error approving lecturer: {str(e)}")
    
    return redirect('pending_users')


@admin_required
def reject_user(request, user_id):
    """
    Reject and delete a pending lecturer registration.
    Deletes both User and Lecturer records.
    """
    if request.method != 'POST':
        return redirect('pending_users')
    
    user = get_object_or_404(User, id=user_id)
    username = user.username
    full_name = user.get_full_name()
    
    try:
        # Check if user has a lecturer profile
        try:
            lecturer = Lecturer.objects.get(user=user)
            # Only allow rejection of unapproved lecturers
            if lecturer.is_approved:
                messages.error(request, f"Cannot reject an already approved lecturer.")
                return redirect('pending_users')
        except Lecturer.DoesNotExist:
            pass
        
        # Delete the user (cascade will delete Lecturer profile)
        user.delete()
        
        messages.success(request, f"Lecturer '{full_name}' (@{username}) has been rejected and removed.")
        
    except Exception as e:
        messages.error(request, f"Error rejecting user: {str(e)}")
    
    return redirect('pending_users')