from django.shortcuts import redirect
from django.urls import reverse
from .models import Feedback
from .models import Lecturer


class FeedbackRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for staff/admin or unauthenticated users
        if request.user.is_authenticated and not request.user.is_staff:
            # Check if user is a student
            if hasattr(request.user, 'student') and not request.user.is_superuser and not request.user.is_lecturer:
                # Check if student has given feedback to AT LEAST 1 lecturer
                total_lecturers = Lecturer.objects.count()
                student_feedback_count = Feedback.objects.filter(student=request.user).count()
                feedback_url = reverse("feedback")

                # If there are lecturers and student hasn't provided feedback for at least 1, force redirect
                if total_lecturers > 0 and student_feedback_count == 0:
                    if request.path != feedback_url:
                        print(f"DEBUG MIDDLEWARE: Student {request.user.username} needs feedback for at least 1 lecturer, redirecting from {request.path} to feedback")
                        return redirect("feedback")
                    else:
                        print(f"DEBUG MIDDLEWARE: Student {request.user.username} on feedback page, needs to submit at least 1 feedback")
                elif total_lecturers > 0:
                    print(f"DEBUG MIDDLEWARE: Student {request.user.username} has feedback for {student_feedback_count} lecturer(s), allowing access to {request.path}")
                else:
                    print(f"DEBUG MIDDLEWARE: No lecturers in system, allowing student access")

        return self.get_response(request)
