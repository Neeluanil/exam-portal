from django.contrib import admin
from .models import Student, StudentExamSubmission  # Add your other student models if any

admin.site.register(Student)

@admin.register(StudentExamSubmission)
class StudentExamSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'is_published')
    list_filter = ('is_published',)
    actions = ['publish_results']

    def publish_results(self, request, queryset):
        queryset.update(is_published=True)
        self.message_user(request, "Selected results have been published.")
    publish_results.short_description = "Publish selected results"