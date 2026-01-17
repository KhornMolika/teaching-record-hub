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
    path('lecturers/', admin_views.lecturers, name='lecturers'),
    path('lecturers/approve/<int:lecturer_id>/', admin_views.approve_lecturer, name='approve_lecturer'),
    path('lecturers/deactivate/<int:lecturer_id>/', admin_views.deactivate_lecturer, name='deactivate_lecturer'),
    path('lecturers/edit/<int:lecturer_id>/', admin_views.edit_lecturer, name='edit_lecturer'),
    path('lecturers/create/', admin_views.create_lecturer, name='create_lecturer'),
    path('administrator/teaching-records/', admin_views.admin_teaching_records, name='admin_teaching_records'),
    path('administrator/teaching-records/upload/', admin_views.admin_upload_files, name='admin_upload_files'),

    path('administrator/workload-prediction/', admin_views.admin_workload_prediction, name='admin_workload_prediction'),
    path('administrator/settings/', admin_views.admin_settings, name='admin_settings'),
    path('administrator/manage-admins/', admin_views.manage_admins, name='manage_admins'),
    path('administrator/create-admin/', admin_views.create_admin, name='create_admin'),
    path('administrator/deactivate-admin/<int:user_id>/', admin_views.deactivate_admin, name='deactivate_admin'),
    path('administrator/activate-admin/<int:user_id>/', admin_views.activate_admin, name='activate_admin'),
    
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