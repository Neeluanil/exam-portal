from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.student_register, name='student_register'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('login/', views.student_login, name='student_login'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('logout/', views.student_logout, name='student_logout'),
    path('exams/', views.student_exam_list, name='student_exam_list'),
    path('exam/<int:exam_id>/', views.take_exam, name='take_exam'),
    path('save_snapshot/<int:exam_id>/', views.save_snapshot, name='save_snapshot'),
    path('exam/<int:exam_id>/result/', views.exam_result, name='exam_result'),
    path('exam/<int:exam_id>/result/detail/', views.exam_result_detail, name='exam_result_detail'),
    path('exam/<int:exam_id>/pending/', views.submission_pending, name='submission_pending'),
    path('result_check/', views.student_result_check, name='student_result_check'),  # Added here
]