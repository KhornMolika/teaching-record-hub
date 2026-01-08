from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Lecturer URLs
    path('', views.home, name='home'),
    path('workload/', views.workload, name='workload'),
    path('upload-files/', views.upload_files, name='upload_files'),
    
    # Teaching Records URLs
    path('teaching-records/', views.teaching_records, name='teaching_records'),
    path('teaching-records/upload/', views.upload_files, name='upload_files'),
    path('teaching-records/parse/<int:file_id>/', views.parse_file, name='parse_file'),
    path('teaching-records/delete-file/<int:file_id>/', views.delete_file, name='delete_file'),
    path('teaching-records/delete-session/<int:session_id>/', views.delete_session, name='delete_session'),
    path('teaching-records/delete-sessions/', views.delete_sessions, name='delete_sessions'),
    path('teaching-records/download/', views.download_records, name='download_records'),
]