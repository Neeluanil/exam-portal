from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import Student, StudentExamSubmission
from teachers.models import Teacher, Exam, Question  # Import Exam and Question
import random
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.base import ContentFile
import base64
from django.db import IntegrityError
import face_recognition
import numpy as np
from PIL import Image
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def student_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        name = request.POST.get('name')
        course = request.POST.get('course')
        department = request.POST.get('department')
        register_no = request.POST.get('register_no')
        photo1_data = request.POST.get('photo1')
        photo2_data = request.POST.get('photo2')
        photo3_data = request.POST.get('photo3')

        if not all([username, email, password1, password2, name, course, department, register_no, photo1_data, photo2_data, photo3_data]):
            return render(request, 'students/register.html', {'error': 'All fields and photos are required'})
        if password1 != password2:
            return render(request, 'students/register.html', {'error': 'Passwords do not match'})

        if User.objects.filter(username=username).exists():
            return render(request, 'students/register.html', {'error': 'Username already taken'})
        if Student.objects.filter(email=email).exists():
            return render(request, 'students/register.html', {'error': 'Email already registered'})
        if Student.objects.filter(register_no=register_no).exists():
            return render(request, 'students/register.html', {'error': 'Register number already taken'})

        photos = [photo1_data, photo2_data, photo3_data]
        for i, photo_data in enumerate(photos, 1):
            format, imgstr = photo_data.split(';base64,')
            data = base64.b64decode(imgstr)
            img = Image.open(BytesIO(data))
            img_np = np.array(img)
            if not face_recognition.face_encodings(img_np):
                return render(request, 'students/register.html', {'error': f'No face detected in Photo {i}'})

        otp = random.randint(100000, 999999)
        request.session['otp'] = otp
        request.session['student_data'] = {
            'username': username,
            'email': email,
            'password': password1,
            'name': name,
            'course': course,
            'department': department,
            'register_no': register_no,
            'photo1_data': photo1_data,
            'photo2_data': photo2_data,
            'photo3_data': photo3_data,
        }

        send_mail(
            'OTP for Registration',
            f'Your OTP is: {otp}',
            'gokulsanil99@gmail.com',
            [email],
            fail_silently=False,
        )

        return redirect('verify_otp')
    return render(request, 'students/register.html')

def verify_otp(request):
    if request.method == 'POST':
        user_otp = request.POST.get('otp')
        stored_otp = request.session.get('otp')

        if user_otp == str(stored_otp):
            student_data = request.session.get('student_data')
            try:
                user = User.objects.create_user(
                    username=student_data['username'],
                    email=student_data['email'],
                    password=student_data['password'],
                )

                student = Student(
                    user=user,
                    name=student_data['name'],
                    course=student_data['course'],
                    department=student_data['department'],
                    register_no=student_data['register_no'],
                    email=student_data['email'],
                    is_approved=False
                )

                for i, photo_key in enumerate(['photo1_data', 'photo2_data', 'photo3_data'], 1):
                    photo_data = student_data[photo_key]
                    format, imgstr = photo_data.split(';base64,')
                    ext = format.split('/')[-1]
                    data = base64.b64decode(imgstr)
                    photo_file = ContentFile(data, name=f'{student_data["register_no"]}_photo{i}.{ext}')
                    getattr(student, f'photo{i}').save(photo_file.name, photo_file, save=False)
                
                student.save()
                print("Student saved successfully:", student.id)

                del request.session['otp']
                del request.session['student_data']
                return redirect('student_login')
            except IntegrityError as e:
                print(f"IntegrityError: {e}")
                return render(request, 'students/verify_otp.html', {'error': 'Username, email, or register number already taken'})
            except Exception as e:
                print(f"Error saving student: {e}")
                return render(request, 'students/verify_otp.html', {'error': f'Error saving data: {str(e)}'})
        else:
            return render(request, 'students/verify_otp.html', {'error': 'Invalid OTP'})
    return render(request, 'students/verify_otp.html')

def student_login(request):
    if request.method == 'POST':
        department = request.POST.get('department')
        course = request.POST.get('course')
        register_no = request.POST.get('register_no')
        password = request.POST.get('password')
        photo_data = request.POST.get('photo')

        if not all([department, course, register_no, password, photo_data]):
            return render(request, 'students/login.html', {'error': 'All fields and photo are required'})

        try:
            student = Student.objects.get(
                department=department,
                course=course,
                register_no=register_no,
                is_approved=True
            )
            if not student.user.check_password(password):
                return render(request, 'students/login.html', {'error': 'Invalid credentials'})
        except Student.DoesNotExist:
            return render(request, 'students/login.html', {'error': 'Invalid credentials or not approved'})

        format, imgstr = photo_data.split(';base64,')
        data = base64.b64decode(imgstr)
        captured_image = Image.open(BytesIO(data))
        captured_image_np = np.array(captured_image)

        captured_encodings = face_recognition.face_encodings(captured_image_np)
        if not captured_encodings:
            return render(request, 'students/login.html', {'error': 'No face detected in captured photo'})
        if len(captured_encodings) > 1:
            return render(request, 'students/login.html', {'error': 'Multiple faces detected. Capture one face only.'})
        captured_encoding = captured_encodings[0]

        stored_images = [
            face_recognition.load_image_file(student.photo1.path),
            face_recognition.load_image_file(student.photo2.path),
            face_recognition.load_image_file(student.photo3.path),
        ]
        stored_encodings = []
        for i, img in enumerate(stored_images, 1):
            encodings = face_recognition.face_encodings(img)
            if encodings:
                stored_encodings.append(encodings[0])
            else:
                print(f"Warning: No face in student photo {i} for {register_no}")

        if not stored_encodings:
            return render(request, 'students/login.html', {'error': 'No valid face data in your registered photos. Contact admin.'})

        matches = face_recognition.compare_faces(stored_encodings, captured_encoding, tolerance=0.45)
        print(f"Matches with {register_no}'s photos: {matches}")
        if not any(matches):
            return render(request, 'students/login.html', {'error': 'Face does not match your registered photos'})

        all_students = Student.objects.exclude(id=student.id)
        all_teachers = Teacher.objects.all()

        other_encodings = []
        for other_student in all_students:
            for photo_field in [other_student.photo1, other_student.photo2, other_student.photo3]:
                if photo_field:
                    img = face_recognition.load_image_file(photo_field.path)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        other_encodings.append((other_student.register_no, encodings[0]))

        for teacher in all_teachers:
            for photo_field in [teacher.photo1, teacher.photo2, teacher.photo3]:
                if photo_field:
                    img = face_recognition.load_image_file(photo_field.path)
                    encodings = face_recognition.face_encodings(img)
                    if encodings:
                        other_encodings.append((teacher.teacher_id, encodings[0]))

        if other_encodings:
            other_matches = face_recognition.compare_faces([enc for _, enc in other_encodings], captured_encoding, tolerance=0.45)
            matched_users = [user_id for (user_id, _), match in zip(other_encodings, other_matches) if match]
            print(f"Cross-check matches with other users: {matched_users}")
            if any(other_matches):
                return render(request, 'students/login.html', {'error': f'Face matches another user ({", ".join(matched_users)}). Login denied.'})

        request.session['student_id'] = student.id
        return redirect('student_dashboard')

    return render(request, 'students/login.html')

def student_dashboard(request):
    if 'student_id' not in request.session:
        return redirect('student_login')
    student = Student.objects.get(id=request.session['student_id'])
    return render(request, 'students/dashboard.html', {'student': student})

def student_logout(request):
    if 'student_id' in request.session:
        del request.session['student_id']
    return redirect('student_login')

def student_exam_list(request):
    if 'student_id' not in request.session:
        return redirect('student_login')
    student = Student.objects.get(id=request.session['student_id'])
    exams = Exam.objects.filter(course=student.course, department=student.department)
    return render(request, 'students/exam_list.html', {'student': student, 'exams': exams})

# ... (other imports remain unchanged)
def take_exam(request, exam_id):
    if 'student_id' not in request.session:
        return redirect('student_login')
    student = Student.objects.get(id=request.session['student_id'])
    
    try:
        exam = Exam.objects.get(id=exam_id, course=student.course, department=student.department)
    except Exam.DoesNotExist:
        return redirect('student_exam_list')

    if StudentExamSubmission.objects.filter(student=student, exam=exam).exists():
        return redirect('exam_result_detail', exam_id=exam_id)  # Redirect to detailed results if submitted

    questions = Question.objects.filter(exam=exam)
    total_questions = questions.count()

    # Check for termination
    if request.session.get(f'exam_{exam_id}_terminate'):
        return render(request, 'students/exam_terminated.html', {
            'student': student,
            'exam': exam,
            'reason': request.session.get(f'exam_{exam_id}_terminate_reason', 'Unknown')
        })

    # Initialize session data
    if f'exam_{exam_id}_answers' not in request.session:
        request.session[f'exam_{exam_id}_answers'] = {}
    if f'exam_{exam_id}_current_question' not in request.session:
        request.session[f'exam_{exam_id}_current_question'] = 0
    if f'exam_{exam_id}_snapshots' not in request.session:
        request.session[f'exam_{exam_id}_snapshots'] = []

    current_index = request.session[f'exam_{exam_id}_current_question']
    answers = request.session[f'exam_{exam_id}_answers']

    if request.method == 'POST':
        action = request.POST.get('action')
        answer = request.POST.get(f'question_{questions[current_index].id}')

        # Save answer
        if answer:
            answers[str(questions[current_index].id)] = answer
            request.session[f'exam_{exam_id}_answers'] = answers

        if action == 'next' and current_index < total_questions - 1:
            request.session[f'exam_{exam_id}_current_question'] = current_index + 1
        elif action == 'prev' and current_index > 0:
            request.session[f'exam_{exam_id}_current_question'] = current_index - 1
        elif action == 'submit':
            # Face verification
            face_snapshots = request.session.get(f'exam_{exam_id}_snapshots', [])
            if not face_snapshots:
                current_question = questions[current_index] if questions else None
                current_answer = answers.get(str(current_question.id)) if current_question else None
                return render(request, 'students/take_exam.html', {
                    'student': student,
                    'exam': exam,
                    'question': current_question,
                    'current_answer': current_answer,
                    'current_index': current_index,
                    'total_questions': total_questions,
                    'time_limit': exam.time_limit * 60,
                    'error': 'No face snapshots captured. Please enable webcam.'
                })

            stored_images = [
                face_recognition.load_image_file(student.photo1.path),
                face_recognition.load_image_file(student.photo2.path),
                face_recognition.load_image_file(student.photo3.path),
            ]
            stored_encodings = [enc[0] for img in stored_images for enc in face_recognition.face_encodings(img) if enc]
            if not stored_encodings:
                current_question = questions[current_index] if questions else None
                current_answer = answers.get(str(current_question.id)) if current_question else None
                return render(request, 'students/take_exam.html', {
                    'student': student,
                    'exam': exam,
                    'question': current_question,
                    'current_answer': current_answer,
                    'current_index': current_index,
                    'total_questions': total_questions,
                    'time_limit': exam.time_limit * 60,
                    'error': 'No valid face data in your profile. Contact admin.'
                })

            face_verified = True
            for snapshot_data in face_snapshots:
                format, imgstr = snapshot_data.split(';base64,')
                data = base64.b64decode(imgstr)
                snapshot_image = Image.open(BytesIO(data))
                snapshot_np = np.array(snapshot_image)
                snapshot_encodings = face_recognition.face_encodings(snapshot_np)
                if not snapshot_encodings or not any(face_recognition.compare_faces(stored_encodings, snapshot_encodings[0], tolerance=0.45)):
                    face_verified = False
                    request.session[f'exam_{exam_id}_face_mismatch'] = True
                    break

            if not face_verified or request.session.get(f'exam_{exam_id}_face_mismatch'):
                current_question = questions[current_index] if questions else None
                current_answer = answers.get(str(current_question.id)) if current_question else None
                return render(request, 'students/take_exam.html', {
                    'student': student,
                    'exam': exam,
                    'question': current_question,
                    'current_answer': current_answer,
                    'current_index': current_index,
                    'total_questions': total_questions,
                    'time_limit': exam.time_limit * 60,
                    'error': 'Face verification failed during exam. Submission denied.'
                })

            # Calculate score and save submission
            score = 0
            for question in questions:
                submitted_answer = answers.get(str(question.id))
                if submitted_answer == question.correct_answer:
                    score += question.marks_correct
                elif submitted_answer:
                    score -= question.marks_wrong

            StudentExamSubmission.objects.create(
                student=student,
                exam=exam,
                score=score,
                answers=answers
            )
            
            # Clean up session
            session_keys = [
                f'exam_{exam_id}_snapshots',
                f'exam_{exam_id}_answers',
                f'exam_{exam_id}_current_question',
                f'exam_{exam_id}_face_mismatch',
                f'exam_{exam_id}_terminate',
                f'exam_{exam_id}_terminate_reason'
            ]
            for key in session_keys:
                if key in request.session:
                    del request.session[key]
            return redirect('exam_result_detail', exam_id=exam_id)  # Updated redirect

        request.session.modified = True

    # Render current question
    current_question = questions[current_index] if questions else None
    current_answer = answers.get(str(current_question.id)) if current_question else None
    return render(request, 'students/take_exam.html', {
        'student': student,
        'exam': exam,
        'question': current_question,
        'current_answer': current_answer,
        'current_index': current_index,
        'total_questions': total_questions,
        'time_limit': exam.time_limit * 60
    })

def exam_result(request, exam_id):
    if 'student_id' not in request.session:
        return redirect('student_login')
    student = Student.objects.get(id=request.session['student_id'])
    try:
        submission = StudentExamSubmission.objects.get(student=student, exam_id=exam_id)
        return render(request, 'students/exam_result.html', {
            'student': student,
            'submission': submission
        })
    except StudentExamSubmission.DoesNotExist:
        return redirect('student_exam_list')

def exam_result_detail(request, exam_id):
    if 'student_id' not in request.session:
        return redirect('student_login')
    student = Student.objects.get(id=request.session['student_id'])
    try:
        submission = StudentExamSubmission.objects.get(student=student, exam_id=exam_id)
        questions = Question.objects.filter(exam=submission.exam)
        return render(request, 'students/exam_result_detail.html', {
            'student': student,
            'submission': submission,
            'questions': questions
        })
    except StudentExamSubmission.DoesNotExist:
        return redirect('student_exam_list')

@csrf_exempt
def save_snapshot(request, exam_id):
    if request.method != 'POST' or 'student_id' not in request.session:
        return JsonResponse({'status': 'error'}, status=400)

    student = Student.objects.get(id=request.session['student_id'])
    data = json.loads(request.body)
    snapshot = data.get('snapshot')
    if not snapshot:
        return JsonResponse({'status': 'error', 'message': 'No snapshot provided'}, status=400)

    # Decode snapshot
    format, imgstr = snapshot.split(';base64,')
    data = base64.b64decode(imgstr)
    snapshot_image = Image.open(BytesIO(data))
    snapshot_np = np.array(snapshot_image)
    snapshot_encodings = face_recognition.face_encodings(snapshot_np)

    if not snapshot_encodings:
        request.session[f'exam_{exam_id}_face_mismatch'] = True
        request.session[f'exam_{exam_id}_terminate'] = True
        request.session[f'exam_{exam_id}_terminate_reason'] = 'No face detected'
        return JsonResponse({'status': 'error', 'message': 'No face detected'})

    snapshot_encoding = snapshot_encodings[0]

    # Load student’s registered photos
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

    if not stored_encodings:
        return JsonResponse({'status': 'error', 'message': 'No valid face data in profile'}, status=500)

    # Check against student’s photos
    matches = face_recognition.compare_faces(stored_encodings, snapshot_encoding, tolerance=0.45)
    if not any(matches):
        request.session[f'exam_{exam_id}_face_mismatch'] = True
        request.session[f'exam_{exam_id}_terminate'] = True
        request.session[f'exam_{exam_id}_terminate_reason'] = 'Face does not match registered photos'
        return JsonResponse({'status': 'error', 'message': 'Face does not match registered photos'})

    # Cross-check against other users
    all_teachers = Teacher.objects.all()
    all_students = Student.objects.exclude(id=student.id)
    other_encodings = []
    for other_student in all_students:
        for photo_field in [other_student.photo1, other_student.photo2, other_student.photo3]:
            if photo_field:
                img = face_recognition.load_image_file(photo_field.path)
                encodings = face_recognition.face_encodings(img)
                if encodings:
                    other_encodings.append((other_student.register_no, encodings[0]))
    for teacher in all_teachers:
        for photo_field in [teacher.photo1, teacher.photo2, teacher.photo3]:
            if photo_field:
                img = face_recognition.load_image_file(photo_field.path)
                encodings = face_recognition.face_encodings(img)
                if encodings:
                    other_encodings.append((teacher.teacher_id, encodings[0]))

    if other_encodings:
        other_matches = face_recognition.compare_faces([enc for _, enc in other_encodings], snapshot_encoding, tolerance=0.45)
        if any(other_matches):
            matched_users = [user_id for (user_id, _), match in zip(other_encodings, other_matches) if match]
            request.session[f'exam_{exam_id}_face_mismatch'] = True
            request.session[f'exam_{exam_id}_terminate'] = True
            request.session[f'exam_{exam_id}_terminate_reason'] = f'Face matches another user: {", ".join(matched_users)}'
            return JsonResponse({'status': 'error', 'message': f'Face matches another user: {", ".join(matched_users)}'})

    snapshots = request.session.get(f'exam_{exam_id}_snapshots', [])
    snapshots.append(snapshot)
    request.session[f'exam_{exam_id}_snapshots'] = snapshots
    return JsonResponse({'status': 'success'})