from django.db import models
from django.contrib.auth.models import User

# Supports payroll later
# Multi‑lecturer ready
class Lecturer(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    lecturer_id = models.CharField(max_length=50, unique=True)    
    department = models.CharField(max_length=100)
    hourly_rate = models.DecimalField(
        max_digits=8, decimal_places=2, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name} ({self.lecturer_id})"

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
class TeachingFile(models.Model):
    lecturer = models.ForeignKey(
        Lecturer, on_delete=models.CASCADE, related_name="teaching_files"
    )
    file_name = models.FileField(upload_to="teaching_files/")
    upload_date = models.DateTimeField(auto_now_add=True)
    semester = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.file_name.name}"

# One row = one teaching day
# Prevents duplicate sessions
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

    week_number = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("lecturer", "subject", "date")

    def __str__(self):
        return f"{self.date} - {self.minutes} mins"

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

# Clean separation of prediction logic#
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

