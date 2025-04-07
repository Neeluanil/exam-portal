from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from students.models import Student, StudentExamSubmission
from teachers.models import Teacher, Exam, Question
import face_recognition
import base64
from io import BytesIO
from PIL import Image
import numpy as np

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('student_login')
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

@login_required
def submission_detail(request, submission_id):
    if not request.user.is_superuser:
        return redirect('student_login')
    
    try:
        submission = StudentExamSubmission.objects.get(id=submission_id)
        questions = Question.objects.filter(exam=submission.exam)

        if request.method == 'POST' and 'flag_submission' in request.POST:
            submission.flagged = not submission.flagged  # Toggle flag
            submission.save()
            return redirect('submission_detail', submission_id=submission_id)
        
        # Load student’s registered photos
        student = submission.student
        stored_images = [
            face_recognition.load_image_file(student.photo1.path),
            face_recognition.load_image_file(student.photo2.path),
            face_recognition.load_image_file(student.photo3.path),
        ]
        stored_encodings = []
        for img in stored_images:
            encodings = face_recognition.face_encodings(img)
            if encodings:
                stored_encodings.append(encodings[0])

        # Verify snapshots
        snapshot_results = []
        for snapshot_data in submission.snapshots:
            try:
                format, imgstr = snapshot_data.split(';base64,')
                data = base64.b64decode(imgstr)
                snapshot_image = Image.open(BytesIO(data))
                snapshot_np = np.array(snapshot_image)
                snapshot_encodings = face_recognition.face_encodings(snapshot_np)
                
                if snapshot_encodings and stored_encodings:
                    matches = face_recognition.compare_faces(stored_encodings, snapshot_encodings[0], tolerance=0.45)
                    match_result = "Match" if any(matches) else "No Match"
                else:
                    match_result = "No Face Detected"
                snapshot_results.append({'data': snapshot_data, 'result': match_result})
            except Exception as e:
                snapshot_results.append({'data': snapshot_data, 'result': f"Error: {str(e)}"})

        return render(request, 'admin_portal/submission_detail.html', {
            'submission': submission,
            'questions': questions,
            'snapshots': snapshot_results
        })
    except StudentExamSubmission.DoesNotExist:
        return redirect('monitor_exams')