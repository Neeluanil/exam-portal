from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from students.models import Student
from teachers.models import Teacher
from students.models import StudentExamSubmission

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('student_login')  # Or a custom login page
    return render(request, 'admin_portal/dashboard.html', {
        'user': request.user
    })

@login_required
def approve_users(request):
    if not request.user.is_superuser:
        return redirect('student_login')
    
    students = Student.objects.filter(is_approved=False)
    teachers = Teacher.objects.filter(is_approved=False)
    
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids')
        teacher_ids = request.POST.getlist('teacher_ids')
        
        if student_ids:
            Student.objects.filter(id__in=student_ids).update(is_approved=True)
        if teacher_ids:
            Teacher.objects.filter(id__in=teacher_ids).update(is_approved=True)
        return redirect('approve_users')
    
    return render(request, 'admin_portal/approve_users.html', {
        'students': students,
        'teachers': teachers
    })

@login_required
def monitor_exams(request):
    if not request.user.is_superuser:
        return redirect('student_login')
    
    submissions = StudentExamSubmission.objects.all().select_related('student', 'exam')
    return render(request, 'admin_portal/monitor_exams.html', {
        'submissions': submissions
    })