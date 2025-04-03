from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('approve-users/', views.approve_users, name='approve_users'),
    path('monitor-exams/', views.monitor_exams, name='monitor_exams'),
]