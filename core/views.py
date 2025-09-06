from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import csv
from django.views.decorators.http import require_POST
from django.db.models import Avg, Q
from django.db import models
from django.utils.translation import gettext as _
from django.db.models import Avg
from datetime import datetime, timedelta
from django.utils import timezone

from accounts.decorators import admin_required, lecturer_required
from accounts.models import User, Student
from .models import (
    NewsAndEvents, TimetableSlot, Batch, Classroom, CourseOffering,
    ActivityLog, Session, Semester, Announcement, Attendance, AttendanceSession, CollegeCalendar,
    FIRST, SECOND, THIRD, FOURTH, FIFTH, SIXTH, SEVENTH, EIGHTH, StudentFeedback, Feedback,
    StudentTuitionFee, TuitionFee
)
from .forms import (
    NewsAndEventsForm, SessionForm, SemesterForm,
    EnhancedAttendanceForm, AttendancePercentageForm, StudentSearchForm,
    AttendanceSessionForm, CollegeCalendarForm, BulkAttendanceForm,
    StudentFeedbackForm, BulkFeedbackForm, FeedbackFilterForm,
    AttendanceSearchForm, AttendanceCalculationForm, FeedbackForm,
    StudentTuitionFeeForm, BulkTuitionFeeUpdateForm
)
from .utils import (
    generate_timetable_for_day, generate_comprehensive_timetable,
    generate_timetable_for_batch, get_timetable_data_for_batch,
    get_all_batches_with_timetable, get_student_by_name,
    build_feature_vector_for_student, predict_performance, log_prediction,
    get_attendance_percentage, get_student_attendance_summary,
    get_batch_attendance_summary, mark_bulk_attendance,
    get_lecturer_courses, search_students, get_detention_list
)
from .ai_utils import get_ai_manager, is_ai_available

# Simple test view to bypass all redirects
def test_view(request):
    """Simple test view to verify HTTP access works"""
    return HttpResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CMS Test Page</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .success { color: #28a745; font-weight: bold; }
            .info { color: #17a2b8; }
            .warning { color: #ffc107; }
            .btn { display: inline-block; padding: 10px 20px; margin: 10px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">✅ CMS System is Working!</h1>
            <p class="info">This page confirms that your Django server is running correctly on HTTP.</p>
            
            <h2>System Status:</h2>
            <ul>
                <li>✅ Django Server: Running</li>
                <li>✅ Database: PostgreSQL Connected</li>
                <li>✅ AI Models: Loaded</li>
                <li>✅ HTTP Access: Working</li>
            </ul>
            
            <h2>Access Your System:</h2>
            <a href="/" class="btn">Go to Home Page</a>
            <a href="/admin/" class="btn">Admin Panel</a>
            <a href="/accounts/lecturer/add/" class="btn">Add Lecturer</a>
            <a href="/ai-predictions/" class="btn">AI Predictions</a>
            
            <h2>Login Credentials:</h2>
            <p><strong>Username:</strong> admin_new</p>
            <p><strong>Password:</strong> admin123</p>
            
            <p class="warning">If you see this page, your system is working perfectly!</p>
        </div>
    </body>
    </html>
    """)

# ########################################################
# News & Events
# ########################################################
@login_required
@lecturer_required
def announcement_list_view(request):
    announcements = Announcement.objects.all().order_by("-created_at")
    return render(request, "core/announcement_list.html", {"announcements": announcements})

@login_required
@admin_required
def announcement_add_view(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        if title and content:
            Announcement.objects.create(title=title, content=content, created_by=request.user)
            messages.success(request, "Announcement added successfully.")
            return redirect("announcement_list")
        messages.error(request, "Please provide both title and content.")
    return render(request, "core/announcement_add.html")

@login_required
@lecturer_required
def announcement_edit_view(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        if title and content:
            announcement.title = title
            announcement.content = content
            announcement.save()
            messages.success(request, "Announcement updated successfully.")
            return redirect("announcement_list")
        messages.error(request, "Please provide both title and content.")
    return render(request, "core/announcement_add.html", {"announcement": announcement})

@login_required
@admin_required
def announcement_delete_view(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    if request.method == "POST":
        announcement.delete()
        messages.success(request, "Announcement deleted successfully.")
        return redirect("announcement_list")
    return render(request, "core/announcement_confirm_delete.html", {"announcement": announcement})

def home_view(request):
    """Home page view"""
    # Get news and events for the ticker
    news_items = NewsAndEvents.objects.order_by('-updated_date')[:5]

    # Check if user can add news (only lecturers and admins)
    can_edit_news = request.user.is_superuser or (hasattr(request.user, 'lecturer') and request.user.is_lecturer and request.user.is_active)

    context = {
        'title': 'Home',
        'items': news_items,  # Template expects 'items' for news
        'can_edit_news': can_edit_news,
    }
    return render(request, 'core/index.html', context)


@login_required
def dashboard_view(request):
    """Dashboard view for all users"""
    # Note: Feedback popup is now handled by middleware after every login
    
    # Get user counts for admin dashboard
    student_count = User.objects.filter(is_student=True).count()
    lecturer_count = User.objects.filter(is_lecturer=True).count()
    superuser_count = User.objects.filter(is_superuser=True).count()
    
    context = {
        'student_count': student_count,
        'lecturer_count': lecturer_count,
        'superuser_count': superuser_count,
        'title': 'Dashboard'
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@admin_required
def timetable_admin_view(request):
    # Get the selected day from request, default to Monday (0)
    selected_day = request.GET.get('day', '0')
    try:
        selected_day = int(selected_day)
    except ValueError:
        selected_day = 0
    
    # Get slots for the selected day only
    slots = TimetableSlot.objects.select_related(
        'offering', 'offering__program', 'offering__course', 
        'offering__batch', 'offering__lecturer', 'classroom'
    ).filter(day=selected_day).order_by('start_time')
    
    # Day choices for the dropdown
    day_choices = [
        (0, 'Monday'),
        (1, 'Tuesday'), 
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday')
    ]
    
    context = {
        "slots": slots, 
        "title": "Timetable",
        "selected_day": selected_day,
        "day_choices": day_choices
    }
    return render(request, "core/timetable_admin.html", context)


@login_required
def post_add(request):
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been uploaded.")
            return redirect("home")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm()
    return render(request, "core/post_add.html", {"title": "Add Post", "form": form})


@login_required
@lecturer_required
def edit_post(request, pk):
    instance = get_object_or_404(NewsAndEvents, pk=pk)
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST, instance=instance)
        title = form.cleaned_data.get("title", "Post") if form.is_valid() else None
        if form.is_valid():
            form.save()
            messages.success(request, f"{title} has been updated.")
            return redirect("home")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm(instance=instance)
    return render(request, "core/post_add.html", {"title": "Edit Post", "form": form})


@login_required
@lecturer_required
def delete_post(request, pk):
    post = get_object_or_404(NewsAndEvents, pk=pk)
    post_title = post.title
    post.delete()
    messages.success(request, f"{post_title} has been deleted.")
    return redirect("home")


# ########################################################
# Session
# ########################################################
@login_required
@lecturer_required
def session_list_view(request):
    """Show list of all sessions"""
    sessions = Session.objects.all().order_by("-is_current_session", "-session")
    return render(request, "core/session_list.html", {"sessions": sessions})


@login_required
@lecturer_required
def session_add_view(request):
    """Add a new session"""
    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("is_current_session"):
                unset_current_session()
            form.save()
            messages.success(request, "Session added successfully.")
            return redirect("session_list")
    else:
        form = SessionForm()
    return render(request, "core/session_update.html", {"form": form})


@login_required
@lecturer_required
def session_update_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if request.method == "POST":
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            if form.cleaned_data.get("is_current_session"):
                unset_current_session()
            form.save()
            messages.success(request, "Session updated successfully.")
            return redirect("session_list")
    else:
        form = SessionForm(instance=session)
    return render(request, "core/session_update.html", {"form": form})


@login_required
@lecturer_required
def session_delete_view(request, pk):
    session = get_object_or_404(Session, pk=pk)
    if session.is_current_session:
        messages.error(request, "You cannot delete the current session.")
    else:
        session.delete()
        messages.success(request, "Session successfully deleted.")
    return redirect("session_list")


def unset_current_session():
    """Unset current session"""
    current_session = Session.objects.filter(is_current_session=True).first()
    if current_session:
        current_session.is_current_session = False
        current_session.save()


# ########################################################
# Semester
# ########################################################
@login_required
@lecturer_required
def semester_list_view(request):
    semesters = Semester.objects.all().order_by("semester")
    active_semesters = Semester.get_active_semesters()
    current_odd = Semester.get_current_odd_semester()
    current_even = Semester.get_current_even_semester()
    
    context = {
        "semesters": semesters,
        "active_semesters": active_semesters,
        "current_odd": current_odd,
        "current_even": current_even,
    }
    return render(request, "core/semester_list.html", context)


@login_required
@lecturer_required
def semester_add_view(request):
    if request.method == "POST":
        form = SemesterForm(request.POST)
        if form.is_valid():
            semester = form.save(commit=False)
            
            # Check if this semester can be activated
            if form.cleaned_data.get("is_current_semester"):
                if not Semester.can_activate_semester(semester.semester, semester.pk):
                    messages.error(
                        request, 
                        f"Cannot activate {semester.semester}. There's already an active {'odd' if semester.is_odd_semester else 'even'} semester."
                    )
                    return render(request, "core/semester_update.html", {"form": form})
                
                # Deactivate conflicting semesters
                if semester.is_odd_semester:
                    Semester.objects.filter(
                        is_current_semester=True,
                        semester__in=[FIRST, THIRD, FIFTH, SEVENTH]
                    ).update(is_current_semester=False)
                else:
                    Semester.objects.filter(
                        is_current_semester=True,
                        semester__in=[SECOND, FOURTH, SIXTH, EIGHTH]
                    ).update(is_current_semester=False)
            
            semester.save()
            messages.success(request, "Semester added successfully.")
            return redirect("semester_list")
    else:
        form = SemesterForm()
    return render(request, "core/semester_update.html", {"form": form})


@login_required
@lecturer_required
def semester_update_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if request.method == "POST":
        form = SemesterForm(request.POST, instance=semester)
        if form.is_valid():
            # Check if this semester can be activated
            if form.cleaned_data.get("is_current_semester"):
                if not Semester.can_activate_semester(semester.semester, semester.pk):
                    messages.error(
                        request, 
                        f"Cannot activate {semester.semester}. There's already an active {'odd' if semester.is_odd_semester else 'even'} semester."
                    )
                    return render(request, "core/semester_update.html", {"form": form})
                
                # Deactivate conflicting semesters
                if semester.is_odd_semester:
                    Semester.objects.filter(
                        is_current_semester=True,
                        semester__in=[FIRST, THIRD, FIFTH, SEVENTH]
                    ).exclude(pk=semester.pk).update(is_current_semester=False)
                else:
                    Semester.objects.filter(
                        is_current_semester=True,
                        semester__in=[SECOND, FOURTH, SIXTH, EIGHTH]
                    ).exclude(pk=semester.pk).update(is_current_semester=False)
            
            form.save()
            messages.success(request, "Semester updated successfully!")
            return redirect("semester_list")
    else:
        form = SemesterForm(instance=semester)
    return render(request, "core/semester_update.html", {"form": form})


@login_required
@lecturer_required
def semester_delete_view(request, pk):
    semester = get_object_or_404(Semester, pk=pk)
    if semester.is_current_semester:
        messages.error(request, "You cannot delete the current semester.")
    else:
        semester.delete()
        messages.success(request, "Semester successfully deleted.")
    return redirect("semester_list")


def unset_current_semester():
    """Unset current semester - updated to handle odd/even logic"""
    # This function is kept for backward compatibility
    # The new logic is handled in the model's save method
    pass


# ########################################################
# Predict Performance API and Pages
# ########################################################


@login_required
@require_POST
def predict_api(request):

    target_name = request.POST.get("student_name", "").strip()
    if request.user.is_student:
        target_user = request.user
    else:
        if not (request.user.is_superuser or request.user.is_lecturer):
            return JsonResponse({"error": "Not authorized"}, status=403)
        if not target_name:
            return JsonResponse({"error": "student_name is required"}, status=400)
        target_user = get_student_by_name(target_name)
        if not target_user:
            return JsonResponse({"error": "Student not found"}, status=404)

    raw = build_feature_vector_for_student(target_user)
    try:
        result = predict_performance(raw)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    log_prediction(target_user, request.user, result, raw)

    return JsonResponse({
        "student": target_user.get_full_name,
        "username": target_user.username,
        "category": result["category"],
        "predicted_marks": result["marks"],
    })


@login_required
def predict_admin_page(request):
    if not (request.user.is_superuser or request.user.is_lecturer):
        messages.error(request, "Not authorized")
        return redirect("home")
    return render(request, "core/predict_admin.html")


@login_required
def predict_student_page(request):
    # Check if user is a student using the same logic as middleware
    if not (hasattr(request.user, 'student') and not request.user.is_superuser and not request.user.is_lecturer):
        messages.error(request, "Not authorized. Only students can access this page.")
        return redirect("home")
    return render(request, "core/predict_student.html")


@login_required
@admin_required
def timetable_regenerate(request):
    try:
        # Get the day to generate timetable for, default to Monday (0)
        selected_day = request.POST.get('day', '0')
        try:
            selected_day = int(selected_day)
        except ValueError:
            selected_day = 0

        created = generate_timetable_for_day(selected_day)
        day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][selected_day]
        messages.success(request, f"Timetable generated for {day_name}. Created {created} slots.")
    except Exception as e:
        messages.error(request, f"Failed to generate timetable: {e}")
    return redirect('timetable_admin')


@login_required
@admin_required
def comprehensive_timetable_view(request):
    """View for comprehensive timetable generation and management."""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate_all':
            # Generate timetable for all batches
            try:
                results = generate_comprehensive_timetable()
                if 'error' in results:
                    messages.error(request, results['error'])
                else:
                    total_slots = sum(results.values())
                    messages.success(request, f"Generated comprehensive timetable with {total_slots} slots across {len(results)} batches.")
            except Exception as e:
                messages.error(request, f"Failed to generate comprehensive timetable: {e}")
        
        elif action == 'generate_batch':
            # Generate timetable for specific batch
            batch_id = request.POST.get('batch_id')
            if batch_id:
                try:
                    created = generate_timetable_for_batch(int(batch_id))
                    messages.success(request, f"Generated {created} slots for the selected batch.")
                except Exception as e:
                    messages.error(request, f"Failed to generate timetable for batch: {e}")
        
        return redirect('comprehensive_timetable')
    
    # Get all batches with their timetable status
    batches = get_all_batches_with_timetable()
    
    # Get comprehensive timetable data
    timetable_data = get_timetable_data_for_batch()
    
    context = {
        'batches': batches,
        'timetable_data': timetable_data,
        'title': 'Comprehensive Timetable Management'
    }
    
    return render(request, 'core/comprehensive_timetable.html', context)


@login_required
@admin_required
def batch_timetable_view(request, batch_id):
    """View for a specific batch's timetable."""
    try:
        batch = Batch.objects.get(id=batch_id)
    except Batch.DoesNotExist:
        messages.error(request, "Batch not found.")
        return redirect('comprehensive_timetable')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate':
            try:
                created = generate_timetable_for_batch(batch_id)
                messages.success(request, f"Generated {created} slots for {batch.title}.")
            except Exception as e:
                messages.error(request, f"Failed to generate timetable: {e}")
        
        return redirect('batch_timetable', batch_id=batch_id)
    
    # Get timetable data for this batch
    timetable_data = get_timetable_data_for_batch(batch_id)
    
    context = {
        'batch': batch,
        'timetable_data': timetable_data,
        'title': f'Timetable - {batch.title}'
    }
    
    return render(request, 'core/batch_timetable.html', context)


# -----------------------------
# Attendance Management Views
# -----------------------------

@login_required
def attendance_dashboard(request):
    """Main attendance dashboard view."""
    if request.user.is_student:
        return redirect('student_attendance')
    elif request.user.is_lecturer:
        return redirect('lecturer_attendance')
    elif request.user.is_superuser:
        return redirect('admin_attendance')
    else:
        messages.error(request, "Access denied.")
        return redirect('home')


@login_required
@admin_required
def admin_attendance(request):
    """Admin view for managing all attendance."""
    
    search_form = AttendanceSearchForm(request.GET or None)
    calculation_form = AttendanceCalculationForm(request.POST or None)
    
    attendance_data = []
    calculation_result = None
    
    if search_form.is_valid():
        student_search = search_form.cleaned_data.get('student_search')
        start_date = search_form.cleaned_data.get('start_date')
        end_date = search_form.cleaned_data.get('end_date')
        course_offering = search_form.cleaned_data.get('course_offering')
        
        if student_search:
            students = search_students(student_search)
            for student in students:
                if course_offering:
                    summary = get_student_attendance_summary(student, course_offering, start_date, end_date)
                    attendance_data.append({
                        'student': student,
                        'summary': summary
                    })
                else:
                    summaries = get_student_attendance_summary(student, None, start_date, end_date)
                    attendance_data.append({
                        'student': student,
                        'summaries': summaries
                    })
    
    if calculation_form.is_valid():
        student = calculation_form.cleaned_data.get('student')
        course_offering = calculation_form.cleaned_data.get('course_offering')
        start_date = calculation_form.cleaned_data.get('start_date')
        end_date = calculation_form.cleaned_data.get('end_date')
        
        calculation_result = get_student_attendance_summary(student, course_offering, start_date, end_date)
    
    context = {
        'search_form': search_form,
        'calculation_form': calculation_form,
        'attendance_data': attendance_data,
        'calculation_result': calculation_result,
        'title': 'Attendance Management (Admin)'
    }
    
    return render(request, 'core/attendance_admin.html', context)


@login_required
@lecturer_required
def lecturer_attendance(request):
    """Enhanced lecturer view for managing attendance for their courses."""
    
    lecturer_courses = get_lecturer_courses(request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'mark_attendance':
            form = EnhancedAttendanceForm(request.POST, lecturer=request.user)
            if form.is_valid():
                course_offering = form.cleaned_data.get('course_offering')
                date = form.cleaned_data.get('date')
                present_students = form.cleaned_data.get('present_students')
                notes = form.cleaned_data.get('notes')
                
                # Verify lecturer has permission for this course
                if course_offering in lecturer_courses:
                    from .utils import mark_attendance_for_course
                    attendance_records, session = mark_attendance_for_course(
                        course_offering, date, present_students, request.user, notes
                    )
                    messages.success(request, f"Attendance marked for {len(attendance_records)} students.")
                else:
                    messages.error(request, "You don't have permission to mark attendance for this course.")
        elif action == 'calculate_percentage':
            percentage_form = AttendancePercentageForm(request.POST, lecturer=request.user)
            if percentage_form.is_valid():
                student = percentage_form.cleaned_data.get('student')
                course_offering = percentage_form.cleaned_data.get('course_offering')
                start_date = percentage_form.cleaned_data.get('start_date')
                end_date = percentage_form.cleaned_data.get('end_date')
                
                from .utils import calculate_attendance_percentage
                percentage_result = calculate_attendance_percentage(
                    student, course_offering, start_date, end_date
                )
                messages.info(request, f"Attendance percentage calculated for {student.get_full_name}.")
        else:
            form = EnhancedAttendanceForm(lecturer=request.user)
            percentage_form = AttendancePercentageForm(lecturer=request.user)
    else:
        form = EnhancedAttendanceForm(lecturer=request.user)
        percentage_form = AttendancePercentageForm(lecturer=request.user)
    
    # Get recent attendance sessions for lecturer's courses
    recent_sessions = AttendanceSession.objects.filter(
        course_offering__in=lecturer_courses
    ).order_by('-date')[:10]
    
    # Get course summaries
    course_summaries = []
    for course in lecturer_courses:
        from .utils import get_course_attendance_summary
        summary = get_course_attendance_summary(course)
        course_summaries.append(summary)
    
    context = {
        'form': form,
        'percentage_form': percentage_form,
        'lecturer_courses': lecturer_courses,
        'recent_sessions': recent_sessions,
        'course_summaries': course_summaries,
        'title': 'Enhanced Attendance Management (Lecturer)'
    }
    
    return render(request, 'core/attendance_lecturer_enhanced.html', context)


@login_required
def student_attendance(request):
    """Student view for viewing their own attendance."""
    # Simple student role check
    if not hasattr(request.user, 'student'):
        messages.error(request, "Access denied. Only students can view this page.")
        return redirect('home')
    
    
    calculation_form = AttendanceCalculationForm(request.POST or None)
    calculation_result = None
    
    if calculation_form.is_valid():
        student = calculation_form.cleaned_data.get('student')
        course_offering = calculation_form.cleaned_data.get('course_offering')
        start_date = calculation_form.cleaned_data.get('start_date')
        end_date = calculation_form.cleaned_data.get('end_date')
        
        # Ensure student can only view their own attendance
        if student == request.user:
            calculation_result = get_student_attendance_summary(student, course_offering, start_date, end_date)
        else:
            messages.error(request, "You can only view your own attendance.")
    
    # Pre-populate form with current student
    if not calculation_form.is_bound:
        calculation_form.fields['student'].initial = request.user
    
    # Get student's attendance summary for all courses
    student_summaries = get_student_attendance_summary(request.user)
    
    context = {
        'calculation_form': calculation_form,
        'calculation_result': calculation_result,
        'student_summaries': student_summaries,
        'title': 'My Attendance'
    }
    
    return render(request, 'core/attendance_student.html', context)


@login_required
@admin_required
def batch_attendance(request, batch_id):
    """View attendance for a specific batch."""
    try:
        batch = Batch.objects.get(id=batch_id)
    except Batch.DoesNotExist:
        messages.error(request, "Batch not found.")
        return redirect('admin_attendance')
    
    
    search_form = AttendanceSearchForm(request.GET or None)
    attendance_data = []
    
    if search_form.is_valid():
        start_date = search_form.cleaned_data.get('start_date')
        end_date = search_form.cleaned_data.get('end_date')
        course_offering = search_form.cleaned_data.get('course_offering')
        
        attendance_data = get_batch_attendance_summary(batch, course_offering, start_date, end_date)
    
    context = {
        'batch': batch,
        'search_form': search_form,
        'attendance_data': attendance_data,
        'title': f'Batch Attendance - {batch.title}'
    }
    
    return render(request, 'core/attendance_batch.html', context)


@login_required
@admin_required
def detention_list(request):
    """View students with low attendance."""
    threshold = request.GET.get('threshold', 75.0)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    try:
        threshold = float(threshold)
    except ValueError:
        threshold = 75.0
    
    detention_list_data = get_detention_list(threshold, start_date, end_date)
    
    context = {
        'detention_list': detention_list_data,
        'threshold': threshold,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Detention List'
    }
    
    return render(request, 'core/detention_list.html', context)


@login_required
@admin_required
def attendance_reports(request):
    """Generate attendance reports."""
    from .models import Attendance, AttendanceSession, CollegeCalendar
    from datetime import datetime, timedelta
    
    # Get date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get statistics
    total_attendance_records = Attendance.objects.filter(
        date__range=[start_date, end_date]
    ).count()
    
    total_sessions = AttendanceSession.objects.filter(
        date__range=[start_date, end_date]
    ).count()
    
    working_days = CollegeCalendar.objects.filter(
        date__range=[start_date, end_date],
        is_working_day=True
    ).count()
    
    # Get attendance by course
    course_attendance = {}
    for session in AttendanceSession.objects.filter(date__range=[start_date, end_date]):
        course_name = session.course_offering.course.title
        if course_name not in course_attendance:
            course_attendance[course_name] = {
                'total_sessions': 0,
                'total_students': 0,
                'total_present': 0
            }
        
        course_attendance[course_name]['total_sessions'] += 1
        course_attendance[course_name]['total_students'] += session.total_students
        course_attendance[course_name]['total_present'] += session.present_students
    
    # Calculate percentages
    for course in course_attendance.values():
        if course['total_students'] > 0:
            course['percentage'] = (course['total_present'] / course['total_students']) * 100
        else:
            course['percentage'] = 0
    
    context = {
        'total_attendance_records': total_attendance_records,
        'total_sessions': total_sessions,
        'working_days': working_days,
        'course_attendance': course_attendance,
        'start_date': start_date,
        'end_date': end_date,
        'title': 'Attendance Reports'
    }
    
    return render(request, 'core/attendance_reports.html', context)

# ########################################################
# Student Feedback System
# ########################################################

@login_required
def feedback_popup_view(request):
    """Show feedback popup for students after every login"""
    if not hasattr(request.user, 'student'):
        return redirect('home')
    
    student = request.user.student
    
    # Get ALL active lecturers - feedback is mandatory for everyone
    # This automatically includes any newly added lecturers
    active_lecturers = User.objects.filter(is_lecturer=True, is_active=True).order_by('first_name', 'last_name')
    
    # If no lecturers exist, redirect to home
    if not active_lecturers.exists():
        return redirect('home')
    
    # Get existing feedback to show what's already completed
    existing_feedback = StudentFeedback.objects.filter(student=student)
    completed_lecturers = set(feedback.lecturer_id for feedback in existing_feedback)
    
    # Pre-fill existing feedback data
    initial_data = {}
    for feedback in existing_feedback:
        initial_data[f'rating_{feedback.lecturer.id}'] = feedback.rating
        initial_data[f'message_{feedback.lecturer.id}'] = feedback.message
    
    if request.method == 'POST':
        form = BulkFeedbackForm(request.POST, lecturers=active_lecturers)
        if form.is_valid():
            # Process feedback for each lecturer
            feedback_created = False
            for lecturer in active_lecturers:
                rating = form.cleaned_data.get(f'rating_{lecturer.id}')
                message = form.cleaned_data.get(f'message_{lecturer.id}', '')
                
                # Rating is mandatory for all lecturers
                if rating:
                    # Check if feedback already exists for this lecturer
                    feedback, created = StudentFeedback.objects.get_or_create(
                        student=student,
                        lecturer=lecturer,
                        defaults={'rating': rating, 'message': message}
                    )
                    
                    # Update existing feedback if it already exists
                    if not created:
                        feedback.rating = rating
                        feedback.message = message
                        feedback.save()
                    
                    feedback_created = True
                else:
                    # If any rating is missing, show error
                    form.add_error(f'rating_{lecturer.id}', 'Rating is required for all lecturers')
                    break
            
            if feedback_created and form.is_valid():
                # Check if all lecturers now have feedback
                total_feedback_count = StudentFeedback.objects.filter(student=student).count()
                total_lecturers_count = active_lecturers.count()
                
                # Update feedback_submitted flag based on whether all lecturers have feedback
                student.feedback_submitted = (total_feedback_count >= total_lecturers_count)
                student.save()
                
                if existing_feedback.exists():
                    messages.success(request, "Thank you for updating your feedback! You can now access all features.")
                else:
                    messages.success(request, "Thank you for your feedback! You can now access all features.")
                
                # Redirect to home page after successful feedback submission
                return redirect('home')
    else:
        form = BulkFeedbackForm(lecturers=active_lecturers, initial=initial_data)
    
    context = {
        'form': form,
        'lecturers': active_lecturers,
        'existing_feedback': existing_feedback,
        'completed_lecturers': completed_lecturers,
        'show_popup': True,
        'is_mandatory': True,
        'total_lecturers': active_lecturers.count(),
        'completed_count': existing_feedback.count(),
        'remaining_count': active_lecturers.count() - existing_feedback.count(),
        'has_existing_feedback': existing_feedback.exists()
    }
    return render(request, 'core/feedback_popup.html', context)

@login_required
@admin_required
def admin_feedback_view(request):
    """Admin view to see all feedback"""
    feedback_list = StudentFeedback.objects.select_related('student', 'lecturer').all()
    
    # Apply filters
    filter_form = FeedbackFilterForm(request.GET)
    if filter_form.is_valid():
        lecturer = filter_form.cleaned_data.get('lecturer')
        rating = filter_form.cleaned_data.get('rating')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if lecturer:
            feedback_list = feedback_list.filter(lecturer=lecturer)
        if rating:
            feedback_list = feedback_list.filter(rating=rating)
        if date_from:
            feedback_list = feedback_list.filter(created_at__date__gte=date_from)
        if date_to:
            feedback_list = feedback_list.filter(created_at__date__lte=date_to)
    
    # Get comprehensive statistics
    total_feedback = feedback_list.count()
    avg_rating = feedback_list.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Get all active lecturers and their feedback status
    active_lecturers = User.objects.filter(is_lecturer=True, is_active=True)
    total_students = User.objects.filter(is_student=True, is_active=True).count()
    
    lecturer_summary = {}
    total_expected_feedback = 0
    total_completed_feedback = 0
    
    for lecturer in active_lecturers:
        lecturer_feedback = feedback_list.filter(lecturer=lecturer)
        expected_feedback = total_students  # Each student should give feedback to each lecturer
        completed_feedback = lecturer_feedback.count()
        
        total_expected_feedback += expected_feedback
        total_completed_feedback += completed_feedback
        
        lecturer_summary[lecturer] = {
            'count': completed_feedback,
            'expected': expected_feedback,
            'completion_rate': round((completed_feedback / expected_feedback) * 100, 1) if expected_feedback > 0 else 0,
            'avg_rating': round(lecturer_feedback.aggregate(Avg('rating'))['rating__avg'], 1) if lecturer_feedback.exists() else 0,
            'recent_feedback': lecturer_feedback[:3],  # Last 3 feedback
            'rating_distribution': {
                '1': lecturer_feedback.filter(rating=1).count(),
                '2': lecturer_feedback.filter(rating=2).count(),
                '3': lecturer_feedback.filter(rating=3).count(),
                '4': lecturer_feedback.filter(rating=4).count(),
                '5': lecturer_feedback.filter(rating=5).count(),
            }
        }
    
    # Overall system statistics
    overall_completion_rate = round((total_completed_feedback / total_expected_feedback) * 100, 1) if total_expected_feedback > 0 else 0
    
    # Recent feedback (last 10)
    recent_feedback = feedback_list.order_by('-created_at')[:10]
    
    context = {
        'feedback_list': feedback_list,
        'filter_form': filter_form,
        'total_feedback': total_feedback,
        'avg_rating': round(avg_rating, 1),
        'lecturer_summary': lecturer_summary,
        'total_lecturers': active_lecturers.count(),
        'total_students': total_students,
        'total_expected_feedback': total_expected_feedback,
        'total_completed_feedback': total_completed_feedback,
        'overall_completion_rate': overall_completion_rate,
        'recent_feedback': recent_feedback,
        'title': 'Student Feedback Management'
    }
    return render(request, 'core/admin_feedback.html', context)

@login_required
@admin_required
def feedback_detail_view(request, lecturer_id):
    """Detailed view of feedback for a specific lecturer"""
    lecturer = get_object_or_404(User, id=lecturer_id, is_lecturer=True)
    feedback_list = StudentFeedback.objects.filter(lecturer=lecturer).select_related('student').order_by('-created_at')
    
    # Statistics
    total_feedback = feedback_list.count()
    avg_rating = feedback_list.aggregate(Avg('rating'))['rating__avg'] or 0
    rating_distribution = {}
    rating_percentages = {}
    
    for i in range(1, 6):
        count = feedback_list.filter(rating=i).count()
        rating_distribution[i] = count
        # Calculate percentage for each rating
        if total_feedback > 0:
            rating_percentages[i] = round((count / total_feedback) * 100, 1)
        else:
            rating_percentages[i] = 0
    
    context = {
        'lecturer': lecturer,
        'feedback_list': feedback_list,
        'total_feedback': total_feedback,
        'avg_rating': round(avg_rating, 1),
        'rating_distribution': rating_distribution,
        'rating_percentages': rating_percentages,
        'title': f'Feedback for {lecturer.get_full_name}'
    }
    return render(request, 'core/feedback_detail.html', context)

@login_required
@admin_required
def feedback_export_view(request):
    """Export feedback data to CSV"""
    import csv
    from datetime import datetime
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="student_feedback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student', 'Lecturer', 'Rating', 'Message', 'Date'])
    
    feedback_list = StudentFeedback.objects.select_related('student', 'lecturer').all()
    
    # Apply same filters as admin view
    filter_form = FeedbackFilterForm(request.GET)
    if filter_form.is_valid():
        lecturer = filter_form.cleaned_data.get('lecturer')
        rating = filter_form.cleaned_data.get('rating')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if lecturer:
            feedback_list = feedback_list.filter(lecturer=lecturer)
        if rating:
            feedback_list = feedback_list.filter(rating=rating)
        if date_from:
            feedback_list = feedback_list.filter(created_at__date__gte=date_from)
        if date_to:
            feedback_list = feedback_list.filter(created_at__date__lte=date_to)
    
    for feedback in feedback_list:
        writer.writerow([
            feedback.student.student.get_full_name,
            feedback.lecturer.get_full_name,
            feedback.rating,
            feedback.message,
            feedback.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


def test_student_access(request):
    """Simple test view to debug student access issues."""
    if request.user.is_authenticated:
        user_info = {
            'username': request.user.username,
            'is_student': getattr(request.user, 'is_student', False),
            'is_lecturer': getattr(request.user, 'is_lecturer', False),
            'is_superuser': request.user.is_superuser,
            'has_student_attr': hasattr(request.user, 'student'),
            'student_id': getattr(request.user.student, 'id', None) if hasattr(request.user, 'student') else None,
        }
        return JsonResponse(user_info)
    else:
        return JsonResponse({'error': 'User not authenticated'})


@login_required
def feedback_view(request):
    """Handle student feedback submission"""
    # Check if user is a student
    if not hasattr(request.user, 'student') or request.user.is_superuser or request.user.is_lecturer:
        return redirect('home')
    
    # If student already has feedback for at least 1 lecturer, redirect to home
    if Feedback.objects.filter(student=request.user).exists():
        return redirect("home")  # already submitted at least 1 feedback

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            fb = form.save(commit=False)
            fb.student = request.user
            fb.save()
            messages.success(request, "Thank you for your feedback! You can now access all features.")
            return redirect("home")
    else:
        form = FeedbackForm()

    # Render without student sidebar/topbar layout
    return render(request, "core/feedback_form_standalone.html", {"form": form})


@login_required
def feedback_check(request):
    """Check if user needs feedback and redirect accordingly"""
    # Debug: Log user information
    print(f"DEBUG: User: {request.user.username}")
    print(f"DEBUG: Is student: {getattr(request.user, 'is_student', False)}")
    print(f"DEBUG: Has student attr: {hasattr(request.user, 'student')}")
    print(f"DEBUG: Is superuser: {request.user.is_superuser}")
    print(f"DEBUG: Is lecturer: {getattr(request.user, 'is_lecturer', False)}")
    
    # If user is a student, check feedback requirement
    if hasattr(request.user, 'student') and not request.user.is_superuser and not request.user.is_lecturer:
        print(f"DEBUG: User identified as student")
        
        # Check if student needs to provide feedback
        active_lecturers = User.objects.filter(is_lecturer=True, is_active=True)
        existing_feedback = StudentFeedback.objects.filter(student=request.user.student)
        
        print(f"DEBUG: Active lecturers: {active_lecturers.count()}")
        print(f"DEBUG: Existing feedback: {existing_feedback.count()}")
        
        if active_lecturers.exists() and existing_feedback.count() < active_lecturers.count():
            print(f"DEBUG: Student needs feedback, redirecting to feedback_popup")
            # Student needs feedback, redirect to feedback popup
            return redirect('feedback_popup')
        else:
            print(f"DEBUG: Student has completed feedback, redirecting to home")
    
    print(f"DEBUG: Redirecting to home")
    # No feedback needed or not a student, redirect to home
    return redirect('home')


@login_required
def search_suggestions_api(request):
    """Universal search suggestions API for all search bars"""
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Normalize query (remove extra spaces, convert to lowercase)
    normalized_query = ' '.join(query.lower().split())
    
    suggestions = []
    
    try:
        # Search in Students
        from accounts.models import Student
        students = Student.objects.filter(
            Q(student__first_name__icontains=normalized_query) |
            Q(student__last_name__icontains=normalized_query) |
            Q(student__username__icontains=normalized_query) |
            Q(student__email__icontains=normalized_query)
        )[:5]
        
        for student in students:
            suggestions.append({
                'type': 'student',
                'id': student.student.id,
                'title': f"{student.student.get_full_name}",
                'subtitle': f"Student ID: {student.student.username}",
                'url': f"/accounts/profile/{student.student.id}/detail/",
                'icon': '👨‍🎓'
            })
        
        # Search in Lecturers
        from accounts.models import User
        lecturers = User.objects.filter(
            is_lecturer=True
        ).filter(
            Q(first_name__icontains=normalized_query) |
            Q(last_name__icontains=normalized_query) |
            Q(username__icontains=normalized_query) |
            Q(email__icontains=normalized_query)
        )[:5]
        
        for lecturer in lecturers:
            suggestions.append({
                'type': 'lecturer',
                'id': lecturer.id,
                'title': f"{lecturer.get_full_name}",
                'subtitle': f"Lecturer ID: {lecturer.username}",
                'url': f"/accounts/profile/{lecturer.id}/detail/",
                'icon': '👨‍🏫'
            })
        
        # Search in Courses
        from course.models import Course
        courses = Course.objects.filter(
            Q(title__icontains=normalized_query) |
            Q(code__icontains=normalized_query) |
            Q(summary__icontains=normalized_query)
        )[:5]
        
        for course in courses:
            suggestions.append({
                'type': 'course',
                'id': course.id,
                'title': f"{course.title}",
                'subtitle': f"Course Code: {course.code}",
                'url': f"/programs/course/{course.id}/",
                'icon': '📚'
            })
        
        # Search in News & Events
        news_events = NewsAndEvents.objects.filter(
            Q(title__icontains=normalized_query) |
            Q(summary__icontains=normalized_query)
        )[:5]
        
        for news in news_events:
            suggestions.append({
                'type': 'news',
                'id': news.id,
                'title': f"{news.title}",
                'subtitle': f"News & Events",
                'url': f"/news/{news.id}/",
                'icon': '📰'
            })
        
        # Search in Programs
        from course.models import Program
        programs = Program.objects.filter(
            Q(title__icontains=normalized_query) |
            Q(summary__icontains=normalized_query)
        )[:5]
        
        for program in programs:
            suggestions.append({
                'type': 'program',
                'id': program.id,
                'title': f"{program.title}",
                'subtitle': f"Program",
                'url': f"/programs/program/{program.id}/",
                'icon': '🎓'
            })
        
        # Limit total suggestions to 20
        suggestions = suggestions[:20]
        
    except Exception as e:
        print(f"Search error: {e}")
        suggestions = []
    
    return JsonResponse({'suggestions': suggestions})


@login_required
def universal_search_demo_view(request):
    """Demo page showing universal search functionality"""
    return render(request, "core/universal_search_demo.html")

# Tuition Fee Views
@login_required
def tuition_fee_dashboard(request):
    """Admin dashboard for tuition fee management"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('home')
    
    # Get statistics
    total_students = User.objects.filter(is_student=True).count()
    pending_fees = StudentTuitionFee.objects.filter(is_paid=False).count()
    overdue_fees = StudentTuitionFee.objects.filter(is_overdue=True).count()
    paid_fees = StudentTuitionFee.objects.filter(is_paid=True).count()
    
    # Get recent fee updates
    recent_fees = StudentTuitionFee.objects.select_related('student').order_by('-updated_at')[:10]
    
    # Get semester fee configuration
    semester_fees = TuitionFee.objects.all().order_by('semester')
    
    context = {
        'total_students': total_students,
        'pending_fees': pending_fees,
        'overdue_fees': overdue_fees,
        'paid_fees': paid_fees,
        'recent_fees': recent_fees,
        'semester_fees': semester_fees,
    }
    return render(request, 'core/tuition_fee_dashboard.html', context)

@login_required
def student_tuition_fees(request, student_id):
    """View individual student's tuition fees"""
    student = get_object_or_404(User, id=student_id, is_student=True)
    
    # Check if user has permission to view this student's fees
    if not (request.user.is_staff or request.user == student):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    # Get or create tuition fee records for all 8 semesters
    tuition_fees = []
    for semester in range(1, 9):
        fee, created = StudentTuitionFee.objects.get_or_create(
            student=student,
            semester=semester,
            defaults={
                'due_date': timezone.now().date() + timedelta(days=30),
                'amount_paid': 0.00,
                'is_paid': False
            }
        )
        tuition_fees.append(fee)
    
    # Calculate totals
    total_paid = sum(fee.amount_paid for fee in tuition_fees)
    total_due = sum(fee.amount_paid for fee in tuition_fees if not fee.is_paid)
    
    context = {
        'student': student,
        'tuition_fees': tuition_fees,
        'total_paid': total_paid,
        'total_due': total_due,
    }
    return render(request, 'core/student_tuition_fees.html', context)

@login_required
def update_tuition_fee(request, fee_id):
    """Update individual tuition fee record"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('home')
    
    fee = get_object_or_404(StudentTuitionFee, id=fee_id)
    
    if request.method == 'POST':
        form = StudentTuitionFeeForm(request.POST, instance=fee)
        if form.is_valid():
            form.save()
            messages.success(request, f"Tuition fee for {fee.student.username} - Semester {fee.semester} updated successfully.")
            return redirect('student_tuition_fees', student_id=fee.student.id)
    else:
        form = StudentTuitionFeeForm(instance=fee)
    
    context = {
        'form': form,
        'fee': fee,
        'student': fee.student,
    }
    return render(request, 'core/update_tuition_fee.html', context)

@login_required
def bulk_update_tuition_fees(request):
    """Bulk update tuition fees for all students"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('home')
    
    if request.method == 'POST':
        form = BulkTuitionFeeUpdateForm(request.POST)
        if form.is_valid():
            semester = int(form.cleaned_data['semester'])
            due_date = form.cleaned_data['due_date']
            amount = form.cleaned_data['amount']
            send_notifications = form.cleaned_data['send_notifications']
            
            # Update or create semester fee configuration
            tuition_fee, created = TuitionFee.objects.get_or_create(
                semester=semester,
                defaults={'due_date': due_date, 'amount': amount}
            )
            if not created:
                tuition_fee.due_date = due_date
                tuition_fee.amount = amount
                tuition_fee.save()
            
            # Update all student records for this semester
            students = User.objects.filter(is_student=True)
            updated_count = 0
            
            for student in students:
                student_fee, created = StudentTuitionFee.objects.get_or_create(
                    student=student,
                    semester=semester,
                    defaults={'due_date': due_date, 'amount_paid': 0.00, 'is_paid': False}
                )
                if not created:
                    student_fee.due_date = due_date
                    student_fee.save()
                updated_count += 1
            
            messages.success(request, f"Updated tuition fees for {updated_count} students in Semester {semester}.")
            
            # Send email notifications if requested
            if send_notifications:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    subject = f"Tuition Fee Update - Semester {semester}"
                    message = f"""
Dear Student,

Your tuition fee for Semester {semester} has been updated:

- Due Date: {due_date}
- Amount: ${amount}
- Semester: {semester}

Please ensure timely payment to avoid any late fees or restrictions.

Best regards,
KCET CMS Team
                    """
                    
                    # Send emails to all students
                    student_emails = [student.email for student in students if student.email]
                    if student_emails:
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.EMAIL_FROM_ADDRESS,
                            recipient_list=student_emails,
                            fail_silently=False,
                        )
                        messages.success(request, f"Email notifications sent to {len(student_emails)} students.")
                    else:
                        messages.warning(request, "No student emails found to send notifications.")
                        
                except Exception as e:
                    messages.error(request, f"Error sending email notifications: {str(e)}")
                    print(f"❌ Error sending tuition fee emails: {e}")
            
            return redirect('tuition_fee_dashboard')
    else:
        form = BulkTuitionFeeUpdateForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/bulk_update_tuition_fees.html', context)

@login_required
def tuition_fee_reports(request):
    """Generate tuition fee reports"""
    if not request.user.is_staff:
        messages.error(request, "Access denied. Staff only.")
        return redirect('home')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    semester_filter = request.GET.get('semester', '')
    
    # Build queryset
    fees = StudentTuitionFee.objects.select_related('student').all()
    
    if status_filter:
        if status_filter == 'pending':
            fees = fees.filter(is_paid=False)
        elif status_filter == 'overdue':
            fees = fees.filter(is_overdue=True)
        elif status_filter == 'paid':
            fees = fees.filter(is_paid=True)
    
    if semester_filter:
        fees = fees.filter(semester=int(semester_filter))
    
    # Export functionality
    export_format = request.GET.get('export', '')
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="tuition_fees_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'Student Name', 'Semester', 'Amount Paid', 'Payment Date', 'Due Date', 'Status', 'Overdue'])
        
        for fee in fees:
            writer.writerow([
                fee.student.username,
                f"{fee.student.first_name} {fee.student.last_name}",
                fee.semester,
                fee.amount_paid,
                fee.payment_date or 'N/A',
                fee.due_date,
                fee.status,
                'Yes' if fee.is_overdue else 'No'
            ])
        
        return response
    
    context = {
        'fees': fees,
        'status_filter': status_filter,
        'semester_filter': semester_filter,
    }
    return render(request, 'core/tuition_fee_reports.html', context)

@login_required
def ai_predictions_view(request):
    """View for AI predictions and analytics"""
    if not request.user.is_staff and not hasattr(request.user, 'lecturer'):
        messages.error(request, "Access denied. Only staff and lecturers can view AI predictions.")
        return redirect('home')
    
    ai_manager = get_ai_manager()
    ai_info = ai_manager.get_model_info()
    
    context = {
        'ai_available': is_ai_available(),
        'ai_info': ai_info,
        'feature_names': ai_manager.get_feature_names(),
    }
    
    return render(request, 'core/ai_predictions.html', context)

@login_required
def student_performance_prediction(request, student_id):
    """Predict performance for a specific student"""
    if not request.user.is_staff and not hasattr(request.user, 'lecturer'):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    try:
        student = User.objects.get(id=student_id)
        if not hasattr(student, 'student'):
            messages.error(request, "User is not a student.")
            return redirect('home')
        
        # Get student data for prediction (this would need to be implemented based on your data structure)
        # For now, we'll use dummy data
        student_features = [0.0] * 10  # Adjust based on your feature count
        
        ai_manager = get_ai_manager()
        performance_prediction, error = ai_manager.predict_performance(student_features)
        score_prediction, score_error = ai_manager.predict_score(student_features)
        
        context = {
            'student': student,
            'performance_prediction': performance_prediction,
            'score_prediction': score_prediction,
            'prediction_error': error,
            'score_error': score_error,
            'ai_available': is_ai_available(),
        }
        
        return render(request, 'core/student_prediction.html', context)
        
    except User.DoesNotExist:
        messages.error(request, "Student not found.")
        return redirect('home')
    except Exception as e:
        messages.error(request, f"Error making prediction: {str(e)}")
        return redirect('home')


def check_result_by_enrollment(request):
    """Public view for checking student results using enrollment number"""
    result_data = None
    student_info = None
    error_message = None
    
    if request.method == 'POST':
        enrollment_number = request.POST.get('enrollment_number', '').strip()
        
        if enrollment_number:
            try:
                # Find student by enrollment number
                from accounts.models import Student
                student = Student.objects.select_related('student', 'program').get(
                    enrollment_number=enrollment_number
                )
                
                # Get student's results
                from result.models import Result, TakenCourse
                results = Result.objects.filter(student=student).order_by('session', 'semester')
                taken_courses = TakenCourse.objects.filter(student=student).order_by('course__semester')
                
                # Group results by session and semester
                result_summary = {}
                for result in results:
                    key = f"{result.session} - {result.semester}"
                    if key not in result_summary:
                        result_summary[key] = {
                            'session': result.session,
                            'semester': result.semester,
                            'gpa': result.gpa,
                            'cgpa': result.cgpa,
                            'level': result.level
                        }
                
                # Group courses by semester
                course_summary = {}
                for course in taken_courses:
                    semester = course.course.semester
                    if semester not in course_summary:
                        course_summary[semester] = []
                    course_summary[semester].append({
                        'title': course.course.title,
                        'code': course.course.code,
                        'credit': course.course.credit,
                        'grade': course.grade,
                        'point': course.point,
                        'comment': course.comment
                    })
                
                context = {
                    'student': student,
                    'result_summary': result_summary,
                    'course_summary': course_summary,
                    'enrollment_number': enrollment_number,
                    'title': 'Result Check'
                }
                
                return render(request, 'core/check_result_public.html', context)
                
            except Student.DoesNotExist:
                error_message = "No student found with this enrollment number. Please check and try again."
            except Exception as e:
                error_message = f"An error occurred while fetching results. Please try again later. Error: {str(e)}"
        else:
            error_message = "Please enter an enrollment number."
    
    context = {
        'error_message': error_message,
        'title': 'Check Results'
    }
    
    return render(request, 'core/check_result_form.html', context)


@csrf_exempt
def health_check(request):
    """Health check endpoint for Render deployment"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'College Management System',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })
