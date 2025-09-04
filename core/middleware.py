from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponse
from .models import StudentFeedback
from accounts.models import User


class ForceHTTPMiddleware:
    """Middleware to allow both HTTP and HTTPS access"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow both HTTP and HTTPS - don't force redirects
        response = self.get_response(request)
        
        # Add security headers that work with both protocols
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Allow both HTTP and HTTPS (don't force either)
        response['Strict-Transport-Security'] = 'max-age=0; includeSubDomains'
        
        return response


class FeedbackRedirectMiddleware:
    """Middleware to redirect students to feedback popup after login"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if we need to redirect to feedback after login
        if (request.user.is_authenticated and 
            request.session.get('redirect_to_feedback') and 
            hasattr(request.user, 'student') and 
            not request.user.is_superuser and 
            not request.user.is_lecturer):
            
            print(f"DEBUG FEEDBACK REDIRECT: Redirecting {request.user.username} to feedback_popup")
            
            # Clear the session flag
            del request.session['redirect_to_feedback']
            
            # Redirect to feedback popup
            from django.shortcuts import redirect
            return redirect('feedback_popup')
        
        return self.get_response(request)


class FeedbackRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for staff/admin or unauthenticated users
        if request.user.is_authenticated and not request.user.is_staff:
            # Check if user is a student
            if hasattr(request.user, 'student') and not request.user.is_superuser and not request.user.is_lecturer:
                # Check if student has submitted mandatory feedback for ALL active lecturers
                total_lecturers = User.objects.filter(is_lecturer=True, is_active=True).count()
                feedback_url = reverse("feedback_popup")
                
                if total_lecturers > 0:
                    # Check if student has feedback for all lecturers
                    existing_feedback_count = StudentFeedback.objects.filter(student=request.user.student).count()
                    feedback_complete = existing_feedback_count >= total_lecturers
                    
                    # Update the feedback_submitted flag to match current state
                    if request.user.student.feedback_submitted != feedback_complete:
                        request.user.student.feedback_submitted = feedback_complete
                        request.user.student.save()
                    
                    if not feedback_complete:
                        if request.path != feedback_url:
                            print(f"DEBUG MIDDLEWARE: Student {request.user.username} needs feedback ({existing_feedback_count}/{total_lecturers}), redirecting from {request.path} to feedback_popup")
                            return redirect("feedback_popup")
                        else:
                            print(f"DEBUG MIDDLEWARE: Student {request.user.username} on feedback page")
                    else:
                        print(f"DEBUG MIDDLEWARE: Student {request.user.username} has completed feedback ({existing_feedback_count}/{total_lecturers}), allowing access to {request.path}")
                else:
                    print(f"DEBUG MIDDLEWARE: No lecturers in system, allowing student access")

        return self.get_response(request)
