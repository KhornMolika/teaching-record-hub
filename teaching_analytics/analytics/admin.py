
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

# ----------------------------
# Lecturer Admin
# ----------------------------
@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = (
        "lecturer_id",
        "user",
        "department",
        "hourly_rate",
        "created_at",
    )
    search_fields = ("lecturer_id", "user__username", "user__first_name", "user__last_name")
    list_filter = ("department",)
    ordering = ("lecturer_id",)


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