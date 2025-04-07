from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField
from teachers.models import Exam

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    register_no = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    photo1 = models.ImageField(upload_to='student_photos/')
    photo2 = models.ImageField(upload_to='student_photos/')
    photo3 = models.ImageField(upload_to='student_photos/')
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class StudentExamSubmission(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    answers = JSONField(default=dict)  # Keeps detailed answers (e.g., {"1": {"answer": "A", "marks": 2}})
    snapshots = JSONField(default=list)  # Add this for Base64 snapshots
    flagged = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('student', 'exam')  # Prevent re-taking same exam

    def __str__(self):
        return f"{self.student.name} - {self.exam.course} - {self.score}"