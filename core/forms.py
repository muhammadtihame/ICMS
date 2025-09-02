from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    NewsAndEvents,
    Session,
    Semester,
    Announcement,
    Attendance,
    AttendanceSession,
    CollegeCalendar,
    StudentFeedback,
    Feedback,
    CourseOffering,
)
from accounts.models import User


class NewsAndEventsForm(forms.ModelForm):
    class Meta:
        model = NewsAndEvents
        fields = ["title", "summary", "posted_as"]


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ["session", "is_current_session", "next_session_begins"]


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ["semester", "is_current_semester", "session", "next_semester_begins"]


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "content"]


# -----------------------------
# Attendance Management Forms
# -----------------------------

class EnhancedAttendanceForm(forms.Form):
    """Enhanced form for marking attendance with search functionality."""
    course_offering = forms.ModelChoiceField(
        queryset=CourseOffering.objects.none(),  # Will be set dynamically
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Course')
    )
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('Date')
    )
    student_search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search students by name or ID...')
        }),
        label=_('Search Students')
    )
    present_students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),  # Will be set dynamically
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label=_('Present Students')
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        label=_('Notes')
    )
    
    def __init__(self, *args, **kwargs):
        lecturer = kwargs.pop('lecturer', None)
        super().__init__(*args, **kwargs)
        
        if lecturer:
            # Set course offerings for this lecturer
            from .utils import get_lecturer_courses
            lecturer_courses = get_lecturer_courses(lecturer)
            self.fields['course_offering'].queryset = lecturer_courses
            
            # Set enrolled students for this lecturer
            from .utils import get_lecturer_enrolled_students
            enrolled_students = get_lecturer_enrolled_students(lecturer)
            self.fields['present_students'].queryset = enrolled_students


class AttendancePercentageForm(forms.Form):
    """Form for calculating attendance percentage."""
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(is_student=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Student')
    )
    course_offering = forms.ModelChoiceField(
        queryset=CourseOffering.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Course')
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('Start Date')
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('End Date')
    )
    
    def __init__(self, *args, **kwargs):
        lecturer = kwargs.pop('lecturer', None)
        super().__init__(*args, **kwargs)
        
        if lecturer:
            # Set course offerings for this lecturer
            from .utils import get_lecturer_courses
            lecturer_courses = get_lecturer_courses(lecturer)
            self.fields['course_offering'].queryset = lecturer_courses
            
            # Set enrolled students for this lecturer
            from .utils import get_lecturer_enrolled_students
            enrolled_students = get_lecturer_enrolled_students(lecturer)
            self.fields['student'].queryset = enrolled_students


class StudentSearchForm(forms.Form):
    """Form for searching students in lecturer's courses."""
    course_offering = forms.ModelChoiceField(
        queryset=CourseOffering.objects.none(),  # Will be set dynamically
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Course (Optional)')
    )
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by student name, ID, or email...')
        }),
        label=_('Search Students')
    )
    
    def __init__(self, *args, **kwargs):
        lecturer = kwargs.pop('lecturer', None)
        super().__init__(*args, **kwargs)
        
        if lecturer:
            # Set course offerings for this lecturer
            from .utils import get_lecturer_courses
            lecturer_courses = get_lecturer_courses(lecturer)
            self.fields['course_offering'].queryset = lecturer_courses


class AttendanceSessionForm(forms.ModelForm):
    """Form for creating attendance sessions."""
    class Meta:
        model = AttendanceSession
        fields = ['date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class CollegeCalendarForm(forms.ModelForm):
    """Form for managing college calendar."""
    class Meta:
        model = CollegeCalendar
        fields = ['date', 'is_working_day', 'is_holiday', 'holiday_name', 'academic_year', 'semester']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'holiday_name': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control'}),
            'semester': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BulkAttendanceForm(forms.Form):
    """Form for bulk attendance marking."""
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('Date')
    )
    course_offering = forms.ModelChoiceField(
        queryset=CourseOffering.objects.none(),  # Will be set dynamically
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Course')
    )
    present_students = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),  # Will be set dynamically
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label=_('Present Students')
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        label=_('Notes')
    )
    
    def __init__(self, *args, **kwargs):
        course_queryset = kwargs.pop('course_queryset', CourseOffering.objects.all())
        student_queryset = kwargs.pop('student_queryset', User.objects.filter(is_student=True))
        super().__init__(*args, **kwargs)
        self.fields['course_offering'].queryset = course_queryset
        self.fields['present_students'].queryset = student_queryset


class AttendanceSearchForm(forms.Form):
    """Form for searching attendance records in admin view."""
    student_search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search students by name or ID...')
        }),
        label=_('Search Students')
    )
    course_offering = forms.ModelChoiceField(
        queryset=CourseOffering.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Course (Optional)')
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('Start Date')
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('End Date')
    )


class AttendanceCalculationForm(forms.Form):
    """Form for calculating attendance percentage in admin view."""
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(is_student=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Student')
    )
    course_offering = forms.ModelChoiceField(
        queryset=CourseOffering.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Course')
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('Start Date')
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_('End Date')
    )


class StudentFeedbackForm(forms.ModelForm):
    class Meta:
        model = StudentFeedback
        fields = ['lecturer', 'rating', 'message']
        widgets = {
            'lecturer': forms.Select(attrs={'class': 'form-control'}),
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Please provide your improvement suggestions...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active lecturers
        self.fields['lecturer'].queryset = User.objects.filter(is_lecturer=True, is_active=True).order_by('first_name', 'last_name')

class BulkFeedbackForm(forms.Form):
    """Form for collecting feedback for multiple lecturers at once"""
    
    def __init__(self, *args, **kwargs):
        lecturers = kwargs.pop('lecturers', None)
        super().__init__(*args, **kwargs)
        
        if lecturers:
            for lecturer in lecturers:
                # Rating field for each lecturer (MANDATORY)
                self.fields[f'rating_{lecturer.id}'] = forms.ChoiceField(
                    choices=[('', 'Select rating')] + [(i, f"{i} {'★' * i}") for i in range(1, 6)],
                    label=f"Rate {lecturer.get_full_name} *",
                    widget=forms.Select(attrs={'class': 'form-control rating-select'}),
                    required=True,
                    error_messages={'required': f'Rating is required for {lecturer.get_full_name}'}
                )
                
                # Message field for each lecturer (MANDATORY)
                self.fields[f'message_{lecturer.id}'] = forms.CharField(
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 3,
                        'placeholder': f'Please provide improvement suggestions for {lecturer.get_full_name}...'
                    }),
                    label=f"Suggestions for {lecturer.get_full_name} *",
                    required=True,
                    error_messages={'required': f'Improvement suggestions are required for {lecturer.get_full_name}'}
                )

class FeedbackFilterForm(forms.Form):
    """Form for filtering feedback in admin view"""
    lecturer = forms.ModelChoiceField(
        queryset=User.objects.filter(is_lecturer=True, is_active=True).order_by('first_name', 'last_name'),
        required=False,
        empty_label="All Lecturers",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    rating = forms.ChoiceField(
        choices=[('', 'All Ratings')] + [(i, f"{i} {'★' * i}") for i in range(1, 6)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['lecturer', 'teacher_rating', 'comments']
        widgets = {
            'lecturer': forms.Select(attrs={'class': 'form-control'}),
            'teacher_rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'class': 'form-control'}),
            'comments': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def clean_teacher_rating(self):
        rating = self.cleaned_data.get("teacher_rating")
        if rating is None:
            raise forms.ValidationError("Rating is required.")
        if not (1 <= rating <= 5):
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating
