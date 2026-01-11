from django.urls import path
from .views import auth_views, admin_views, lecturer_views

urlpatterns = [
    # Authentication URLs
    path('register/', auth_views.register_view, name='register'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('pending-approval/', auth_views.pending_approval, name='pending_approval'),
    
    # Admin URLs
    path('dashboard/', admin_views.dashboard, name='dashboard'),
    
    # Lecturer URLs
    path('', lecturer_views.home, name='home'),
    path('workload/', lecturer_views.workload, name='workload'),
    path('settings/', lecturer_views.settings_view, name='settings'),
    
    # Teaching Records URLs
    path('teaching-records/', lecturer_views.teaching_records, name='teaching_records'),
    path('teaching-records/upload/', lecturer_views.upload_files, name='upload_files'),
    path('teaching-records/parse/<int:file_id>/', lecturer_views.parse_file, name='parse_file'),
    path('teaching-records/delete-file/<int:file_id>/', lecturer_views.delete_file, name='delete_file'),
    path('teaching-records/delete-session/<int:session_id>/', lecturer_views.delete_session, name='delete_session'),
    path('teaching-records/delete-sessions/', lecturer_views.delete_sessions, name='delete_sessions'),
    path('teaching-records/download/', lecturer_views.download_records, name='download_records'),
]