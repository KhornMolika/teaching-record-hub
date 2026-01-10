from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Supports payroll later
# Multi‑lecturer ready
class Lecturer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    lecturer_id = models.CharField(max_length=50, unique=True)    
    department = models.CharField(max_length=100)
    hourly_rate = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.lecturer_id})"


class LecturerSettings(models.Model):
    lecturer = models.OneToOneField(
        Lecturer, on_delete=models.CASCADE, related_name='settings'
    )
    theme = models.CharField(
        max_length=20, default='light', choices=[('light', 'Light'), ('dark', 'Dark')]
    )
    date_format = models.CharField(
        max_length=20, default='YYYY-MM-DD', 
        help_text="e.g., YYYY-MM-DD, DD/MM/YYYY"
    )
    enable_notifications = models.BooleanField(default=True)
    records_per_page = models.PositiveSmallIntegerField(default=10)
    
    # UPDATED: Changed default order to match your requirement
    default_columns = models.CharField(
        max_length=255, 
        default='date,subject,lecture_type,time_in,time_out,duration,source_file',
        help_text="Comma-separated list of default columns for teaching records table"
    )
    
    default_sort_order = models.CharField(
        max_length=50, default='-date',
        help_text="Default sort order for teaching records (e.g., -date, subject__name)"
    )
    workload_display = models.CharField(
        max_length=20, default='weekly',
        choices=[('weekly', 'Weekly Hours'), ('monthly', 'Monthly Hours'), ('semester', 'Per Semester')]
    )
    workload_target = models.PositiveSmallIntegerField(
        default=15, help_text="Weekly workload target in hours"
    )

    def __str__(self):
        return f"Settings for {self.lecturer.user.username}"


# Enables per‑subject analytics
class Subject(models.Model):
    subject_code = models.CharField(max_length=20, unique=True)
    subject_name = models.CharField(max_length=150)
    degree_level = models.CharField(max_length=50)
    major = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"


# Tracks XLSB uploads
# Links file → lecturer
# Subject and semester are extracted from file automatically during parsing
class TeachingFile(models.Model):
    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, related_name="teaching_files"
    )
    file_name = models.FileField(upload_to="media/teaching_files/")
    upload_date = models.DateTimeField(auto_now_add=True)
    
    # Auto-filled by parser after upload
    semester = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Auto-filled from XLSB file when parsed"
    )
    
    # Track parsing status
    is_parsed = models.BooleanField(default=False)

    def __str__(self):
        if self.semester:
            return f"{self.file_name.name} ({self.semester})"
        return f"{self.file_name.name}"
    
    @property
    def session_count(self):
        """Return the number of sessions created from this file"""
        return self.sessions.count()


# One row = one teaching day/session
# UPDATED: Prevents duplicate sessions based on date + time slot
# Ready for analytics & prediction
class TeachingSession(models.Model):
    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, related_name="sessions"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="sessions"
    )
    teaching_file = models.ForeignKey(
        TeachingFile, on_delete=models.CASCADE, related_name="sessions"
    )

    date = models.DateField()
    time_in = models.TimeField(blank=True, null=True)
    time_out = models.TimeField(blank=True, null=True)
    minutes = models.PositiveIntegerField()
    
    # Lecture type (e.g., "Introduction", "Topology", "Lab", "Tutorial")
    lecture_type = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name="Lecture Type",
        help_text="Type of lecture (e.g., Introduction, Lab, Tutorial)"
    )

    week_number = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()

    def clean(self):
        # Logical validation (business rules)
        if self.minutes == 0:
            raise ValidationError("Minutes must be greater than zero.")

        if self.time_in and self.time_out:
            if self.time_out <= self.time_in:
                raise ValidationError("time_out must be after time_in.")

    class Meta:
        # FIXED: Unique constraint now includes time_in and time_out
        # This allows multiple sessions on same day at different times
        # But prevents duplicates in the same time slot
        constraints = [
            models.UniqueConstraint(
                fields=['lecturer', 'subject', 'date', 'time_in', 'time_out'],
                name='unique_session_timeslot'
            )
        ]
        
        # Add indexes for faster queries
        indexes = [
            models.Index(fields=['lecturer', 'date']),
            models.Index(fields=['subject', 'date']),
            models.Index(fields=['date', 'time_in']),
        ]

    def __str__(self):
        if self.lecture_type:
            return f"{self.date} - {self.lecture_type} - {self.duration}"
        return f"{self.date} - {self.duration}"
    
    @property
    def duration(self):
        """Return formatted duration as 'Xh Ym'"""
        hours = self.minutes // 60
        mins = self.minutes % 60
        return f"{hours}h {mins}m"
    
    @property
    def duration_minutes(self):
        """Return total minutes for calculations"""
        return self.minutes


# Phase‑1 manual reports
# Phase‑2 analytics
class TeachingSummary(models.Model):
    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, related_name="summaries"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="summaries"
    )

    start_date = models.DateField()
    end_date = models.DateField()
    total_minutes = models.PositiveIntegerField()
    average_minutes_per_week = models.PositiveIntegerField()
    completion_percentage = models.DecimalField(
        max_digits=5, decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary {self.lecturer} ({self.start_date} → {self.end_date})"


# Clean separation of prediction logic
# Can be ignored until Phase‑3
class WorkloadPrediction(models.Model):
    RISK_CHOICES = (
        ("Normal", "Normal"),
        ("Overload", "Overload"),
        ("Underload", "Underload"),
    )

    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, related_name="predictions"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="predictions"
    )

    current_minutes = models.PositiveIntegerField()
    predicted_total_minutes = models.PositiveIntegerField()
    remaining_weeks = models.PositiveSmallIntegerField()
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lecturer} - {self.risk_level}"