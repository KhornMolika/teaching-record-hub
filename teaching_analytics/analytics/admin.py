from django.contrib import admin
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


# ----------------------------
# Teaching Session Admin (CORE)
# ----------------------------
@admin.action(description="Generate Teaching Summary")
def generate_summary_action(modeladmin, request, queryset):
    if not queryset.exists():
        return

    lecturers = queryset.values_list("lecturer", flat=True).distinct()
    subjects = queryset.values_list("subject", flat=True).distinct()

    if lecturers.count() > 1 or subjects.count() > 1:
        modeladmin.message_user(
            request,
            "Please select sessions for ONE lecturer and ONE subject only.",
            level="error"
        )
        return

    first = queryset.first()

    generate_summary(
        lecturer=first.lecturer,
        subject=first.subject,
        start_date=queryset.earliest("date").date,
        end_date=queryset.latest("date").date,
    )

    modeladmin.message_user(request, "Teaching summary generated.")


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
        "total_minutes",
        "average_minutes_per_week",
        "completion_percentage",
        "created_at",
    )
    list_filter = ("lecturer", "subject")
    ordering = ("-created_at",)


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
