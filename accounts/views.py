from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, render_to_string
from django.utils.decorators import method_decorator
from django.views.generic import CreateView
from django_filters.views import FilterView
from xhtml2pdf import pisa
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.db.models import Avg

from accounts.decorators import admin_required, lecturer_required
from accounts.filters import LecturerFilter, StudentFilter
from accounts.forms import (
    ParentAddForm,
    ProfileUpdateForm,
    ProgramUpdateForm,
    StaffAddForm,
    StudentAddForm,
    StudentEditForm,
)
from accounts.models import Parent, Student, User
from core.models import Semester, Session
from course.models import Course
from result.models import TakenCourse
from core.models import StudentFeedback

# ########################################################
# Utility Functions
# ########################################################


def render_to_pdf(template_name, context):
    """Render a given template to PDF format."""
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'filename="profile.pdf"'
    template = render_to_string(template_name, context)
    pdf = pisa.CreatePDF(template, dest=response)
    if pdf.err:
        return HttpResponse("We had some problems generating the PDF")
    return response


# ########################################################
# Authentication and Registration
# ########################################################


def validate_username(request):
    username = request.GET.get("username", None)
    data = {"is_taken": User.objects.filter(username__iexact=username).exists()}
    return JsonResponse(data)


def register(request):
    if request.method == "POST":
        form = StudentAddForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully.")
            return redirect("login")
        messages.error(
            request, "Something is not correct, please fill all fields correctly."
        )
    else:
        form = StudentAddForm()
    return render(request, "registration/register.html", {"form": form})


# ########################################################
# Profile Views
# ########################################################


@login_required
def profile(request):
    """Show profile of the current user."""
    current_session = Session.objects.filter(is_current_session=True).first()
    current_semester = Semester.objects.filter(
        is_current_semester=True, session=current_session
    ).first()

    context = {
        "title": request.user.get_full_name,
        "current_session": current_session,
        "current_semester": current_semester,
    }

    if request.user.is_lecturer:
        # Get courses from both old and new systems for compatibility
        old_courses = Course.objects.filter(
            allocated_course__lecturer__pk=request.user.id, semester=current_semester
        )
        
        # Get courses from new CourseOffering system
        from core.models import CourseOffering
        new_courses = CourseOffering.objects.filter(lecturer=request.user)
        
        context.update({
            "courses": old_courses,
            "course_offerings": new_courses,
        })
        return render(request, "accounts/profile.html", context)

    if request.user.is_student:
        student = get_object_or_404(Student, student__pk=request.user.id)
        parent = Parent.objects.filter(student=student).first()
        courses = TakenCourse.objects.filter(
            student__student__id=request.user.id, course__level=student.level
        )
        context.update(
            {
                "parent": parent,
                "courses": courses,
                "level": student.level,
            }
        )
        return render(request, "accounts/profile.html", context)

    # For superuser or other staff
    staff = User.objects.filter(is_lecturer=True)
    context["staff"] = staff
    return render(request, "accounts/profile.html", context)


@login_required
@admin_required
def profile_single(request, user_id):
    """Show profile of any selected user."""
    if request.user.id == user_id:
        return redirect("profile")

    current_session = Session.objects.filter(is_current_session=True).first()
    current_semester = Semester.objects.filter(
        is_current_semester=True, session=current_session
    ).first()
    user = get_object_or_404(User, pk=user_id)

    context = {
        "title": user.get_full_name,
        "user": user,
        "current_session": current_session,
        "current_semester": current_semester,
    }

    if user.is_lecturer:
        # Get courses from both old and new systems for compatibility
        
        # Get courses from old CourseAllocation system
        # First try to get courses with current session
        old_courses_with_session = Course.objects.filter(
            allocated_course__lecturer__pk=user_id, 
            allocated_course__session=current_session
        )
        
        # If no courses with current session, get all allocated courses regardless of session
        all_allocated_courses = Course.objects.filter(
            allocated_course__lecturer__pk=user_id
        ).exclude(allocated_course__courses__isnull=True)  # Exclude allocations with no courses
        
        # Get courses from new CourseOffering system
        from course.models import CourseOffering
        new_courses = CourseOffering.objects.filter(lecturer=user)
        
        # Prioritize CourseOffering system (new system) over old CourseAllocation
        # Only show old system courses if no CourseOfferings exist
        courses_to_show = new_courses if new_courses.exists() else old_courses_with_session
        
        context.update(
            {
                "user_type": "Lecturer",
                "courses": courses_to_show,
                "course_offerings": new_courses,
                "all_allocated_courses": all_allocated_courses,
                "current_semester_courses": old_courses_with_session,
            }
        )
    elif user.is_student:
        student = get_object_or_404(Student, student__pk=user_id)
        courses = TakenCourse.objects.filter(
            student__student__id=user_id, course__level=student.level
        )
        context.update(
            {
                "user_type": "Student",
                "courses": courses,
                "student": student,
            }
        )
    else:
        context["user_type"] = "Superuser"

    if request.GET.get("download_pdf"):
        return render_to_pdf("pdf/profile_single.html", context)

    return render(request, "accounts/profile_single.html", context)


@login_required
@admin_required
def admin_panel(request):
    return render(request, "setting/admin_panel.html", {"title": "Admin Panel"})


# ########################################################
# Settings Views
# ########################################################


@login_required
def profile_update(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("profile")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, "setting/profile_info_change.html", {"form": form})


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect("profile")
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "setting/password_change.html", {"form": form})


# ########################################################
# Staff (Lecturer) Views
# ########################################################


@login_required
@admin_required
def staff_add_view(request):
    if request.method == "POST":
        form = StaffAddForm(request.POST)
        if form.is_valid():
            lecturer = form.save()
            full_name = lecturer.get_full_name
            email = lecturer.email
            # Show generated credentials inline for admin convenience
            messages.info(
                request,
                f"Lecturer ID: {lecturer.username}. A temporary password has been set and emailed.",
            )
            messages.success(
                request,
                f"Account for lecturer {full_name} has been created. "
                f"An email with account credentials will be sent to {email} within a minute.",
            )
            return redirect("lecturer_list")
    else:
        form = StaffAddForm()
    return render(
        request, "accounts/add_staff.html", {"title": "Add Lecturer", "form": form}
    )


@admin_required
def edit_staff(request, pk):
    lecturer = get_object_or_404(User, is_lecturer=True, pk=pk)
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, request.FILES, instance=lecturer)
        if form.is_valid():
            form.save()
            
            # Check if lecturer has courses, if not, auto-assign some
            try:
                from course.models import CourseAllocation
                from core.models import CourseOffering
                
                # Check if lecturer has any course allocations with courses
                allocations = CourseAllocation.objects.filter(lecturer=lecturer)
                has_courses = any(
                    allocation.courses.exists() 
                    for allocation in allocations
                )
                
                if not has_courses:
                    # Auto-assign courses to lecturer
                    from course.models import Course, Program
                    from core.models import Session, Batch
                    
                    # Get current session
                    current_session = Session.objects.filter(is_current_session=True).first()
                    if not current_session:
                        current_session, _ = Session.objects.get_or_create(
                            is_current_session=True,
                            defaults={'session': '2025'}
                        )
                    
                    # Get or create default program and batch
                    default_program, _ = Program.objects.get_or_create(
                        title="Default Program",
                        defaults={'summary': 'Default program for auto-assignment'}
                    )
                    
                    default_batch, _ = Batch.objects.get_or_create(
                        title="Default Batch",
                        program=default_program
                    )
                    
                    # Get available courses (assign only 2 available)
                    available_courses = Course.objects.all()[:2]
                    
                    if available_courses.exists():
                        # Create or get CourseAllocation
                        allocation, created = CourseAllocation.objects.get_or_create(
                            lecturer=lecturer,
                            session=current_session,
                            defaults={}
                        )
                        
                        # Add courses to allocation
                        for course in available_courses:
                            allocation.courses.add(course)
                        
                        # Create CourseOfferings automatically
                        for course in available_courses:
                            CourseOffering.objects.get_or_create(
                                course=course,
                                lecturer=lecturer,
                                batch=default_batch,
                                program=default_program,
                                defaults={'lectures_per_week': 3}
                            )
                        
                        messages.info(
                            request, 
                            f"✅ Auto-assigned {available_courses.count()} courses to {lecturer.get_full_name}"
                        )
                    else:
                        messages.warning(
                            request,
                            f"⚠️ No courses available to assign to {lecturer.get_full_name}"
                        )
                else:
                    messages.info(
                        request, 
                        f"ℹ️ {lecturer.get_full_name} already has courses - no changes made"
                    )
                        
            except Exception as e:
                print(f"⚠️ Error auto-assigning courses to {lecturer.get_full_name}: {e}")
                
        full_name = lecturer.get_full_name
        messages.success(request, f"Lecturer {full_name} has been updated.")
        return redirect("lecturer_list")
        messages.error(request, "Please correct the error below.")
    else:
        form = ProfileUpdateForm(instance=lecturer)
    return render(
        request, "accounts/edit_lecturer.html", {"title": "Edit Lecturer", "form": form}
    )


@method_decorator([login_required, admin_required], name="dispatch")
class LecturerFilterView(FilterView):
    filterset_class = LecturerFilter
    queryset = User.objects.filter(is_lecturer=True)
    template_name = "accounts/lecturer_list.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Lecturers"
        return context


@login_required
@admin_required
def render_lecturer_pdf_list(request):
    lecturers = User.objects.filter(is_lecturer=True)
    template_path = "pdf/lecturer_list.html"
    context = {"lecturers": lecturers}
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'filename="lecturers_list.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse(f"We had some errors <pre>{html}</pre>")
    return response


@login_required
@admin_required
def delete_staff(request, pk):
    lecturer = get_object_or_404(User, is_lecturer=True, pk=pk)
    full_name = lecturer.get_full_name
    lecturer.delete()
    messages.success(request, f"Lecturer {full_name} has been deleted.")
    return redirect("lecturer_list")




# ########################################################
# Student Views
# ########################################################


@login_required
@admin_required
def student_add_view(request):
    if request.method == "POST":
        form = StudentAddForm(request.POST)
        if form.is_valid():
            student = form.save()
            full_name = student.get_full_name
            email = student.email
            messages.info(
                request,
                f"Student ID: {student.username}. A temporary password has been set and emailed.",
            )
            messages.success(
                request,
                f"Account for {full_name} has been created. "
                f"An email with account credentials will be sent to {email} within a minute.",
            )
            return redirect("student_list")
        messages.error(request, "Correct the error(s) below.")
    else:
        form = StudentAddForm()
    return render(
        request, "accounts/add_student.html", {"title": "Add Student", "form": form}
    )


@login_required
@admin_required
def edit_student(request, pk):
    student_user = get_object_or_404(User, is_student=True, pk=pk)
    student = get_object_or_404(Student, student=student_user)
    
    if request.method == "POST":
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            # Update student data
            form.save()
            
            # Update user data
            student_user.first_name = form.cleaned_data.get("first_name")
            student_user.last_name = form.cleaned_data.get("last_name")
            student_user.email = form.cleaned_data.get("email")
            student_user.phone = form.cleaned_data.get("phone")
            student_user.address = form.cleaned_data.get("address")
            student_user.gender = form.cleaned_data.get("gender")
            student_user.save()
            
            full_name = student_user.get_full_name
            messages.success(request, f"Student {full_name} has been updated.")
            return redirect("student_list")
        messages.error(request, "Please correct the error below.")
    else:
        # Initialize form with current data
        form = StudentEditForm(instance=student)
        form.fields["first_name"].initial = student_user.first_name
        form.fields["last_name"].initial = student_user.last_name
        form.fields["email"].initial = student_user.email
        form.fields["phone"].initial = student_user.phone
        form.fields["address"].initial = student_user.address
        form.fields["gender"].initial = student_user.gender
    
    return render(
        request, "accounts/edit_student.html", {"title": "Edit Student", "form": form}
    )


@method_decorator([login_required, admin_required], name="dispatch")
class StudentListView(FilterView):
    queryset = Student.objects.all()
    filterset_class = StudentFilter
    template_name = "accounts/student_list.html"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Students"
        return context


@login_required
@admin_required
def render_student_pdf_list(request):
    students = Student.objects.all()
    template_path = "pdf/student_list.html"
    context = {"students": students}
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'filename="students_list.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse(f"We had some errors <pre>{html}</pre>")
    return response


@login_required
@admin_required
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    full_name = student.student.get_full_name
    student.delete()
    messages.success(request, f"Student {full_name} has been deleted.")
    return redirect("student_list")


@login_required
@admin_required
def edit_student_program(request, pk):
    student = get_object_or_404(Student, student_id=pk)
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = ProgramUpdateForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            full_name = user.get_full_name
            messages.success(request, f"{full_name}'s program has been updated.")
            return redirect("profile_single", user_id=pk)
        messages.error(request, "Please correct the error(s) below.")
    else:
        form = ProgramUpdateForm(instance=student)
    return render(
        request,
        "accounts/edit_student_program.html",
        {"title": "Edit Program", "form": form, "student": student},
    )


# ########################################################
# Parent Views
# ########################################################


@method_decorator([login_required, admin_required], name="dispatch")
class ParentAdd(CreateView):
    model = Parent
    form_class = ParentAddForm
    template_name = "accounts/parent_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Parent added successfully.")
        return super().form_valid(form)


def custom_logout(request):
    """Custom logout view that redirects to login page"""
    from django.contrib.auth import logout
    from django.shortcuts import redirect
    
    logout(request)
    return redirect('login')
