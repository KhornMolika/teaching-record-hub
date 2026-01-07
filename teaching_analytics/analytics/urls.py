from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Admin URLs
    path('admin/dashboard/', views.dashboard, name='dashboard'),
    
    # Lecturer URLs
    path('', views.home, name='home'),
    path('teaching-records/', views.teaching_records, name='teaching_records'),
    path('workload/', views.workload, name='workload'),
]