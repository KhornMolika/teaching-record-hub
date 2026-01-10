from rest_framework import serializers
from django.contrib.auth.models import User
from .models import TeachingSession, Subject
import os

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user

class TeachingSessionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    semester = serializers.CharField(source='teaching_file.semester')
    lecturer_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    subject = serializers.CharField(source='subject.subject_name')
    teaching_type = serializers.CharField()
    lecture_type = serializers.CharField()
    session_date = serializers.DateField(source='date', format='%Y-%m-%d')
    start_time = serializers.TimeField(source='time_in', format='%H:%M', allow_null=True)
    end_time = serializers.TimeField(source='time_out', format='%H:%M', allow_null=True)
    duration_hours = serializers.DecimalField(max_digits=5, decimal_places=2, source='hours_decimal')
    num_students = serializers.IntegerField()
    file_name = serializers.SerializerMethodField()
    file_id = serializers.IntegerField(source='teaching_file.id')

    def get_lecturer_name(self, obj):
        return obj.lecturer.user.get_full_name() or obj.lecturer.user.username

    def get_department(self, obj):
        return obj.lecturer.department

    def get_file_name(self, obj):
        return os.path.basename(obj.teaching_file.file_name.name)
