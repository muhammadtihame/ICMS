from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg
from django.contrib.auth import get_user_model
from django.utils import timezone


NEWS = _("News")
EVENTS = _("Event")

POST = (
    (NEWS, _("News")),
    (EVENTS, _("Event")),
)

# Updated semester choices to match settings
FIRST = "1st"
SECOND = "2nd"
THIRD = "3rd"
FOURTH = "4th"
FIFTH = "5th"
SIXTH = "6th"
SEVENTH = "7th"
EIGHTH = "8th"

SEMESTER = (
    (FIRST, _("1st Semester")),
    (SECOND, _("2nd Semester")),
    (THIRD, _("3rd Semester")),
    (FOURTH, _("4th Semester")),
    (FIFTH, _("5th Semester")),
    (SIXTH, _("6th Semester")),
    (SEVENTH, _("7th Semester")),
    (EIGHTH, _("8th Semester")),
)


class NewsAndEventsQuerySet(models.query.QuerySet):
    def search(self, query):
        lookups = (
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(posted_as__icontains=query)
        )
        return self.filter(lookups).distinct()


class NewsAndEventsManager(models.Manager):
    def get_queryset(self):
        return NewsAndEventsQuerySet(self.model, using=self._db)

    def all(self):
        return self.get_queryset()

    def get_by_id(self, id):
        qs = self.get_queryset().filter(
            id=id
        )  # NewsAndEvents.objects == self.get_queryset()
        if qs.count() == 1:
            return qs.first()
        return None

    def search(self, query):
        return self.get_queryset().search(query)


class NewsAndEvents(models.Model):
    title = models.CharField(max_length=200, null=True)
    summary = models.TextField(max_length=200, blank=True, null=True)
    posted_as = models.CharField(choices=POST, max_length=10)
    updated_date = models.DateTimeField(auto_now=True, auto_now_add=False, null=True)
    upload_time = models.DateTimeField(auto_now=False, auto_now_add=True, null=True)

    objects = NewsAndEventsManager()

    def __str__(self):
        return f"{self.title}"


class Session(models.Model):
    session = models.CharField(max_length=200, unique=True)
    is_current_session = models.BooleanField(default=False, blank=True, null=True)
    next_session_begins = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.session}"


class Semester(models.Model):
    semester = models.CharField(max_length=10, choices=SEMESTER, blank=True)
    is_current_semester = models.BooleanField(default=False, blank=True, null=True)
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, blank=True, null=True
    )
    next_semester_begins = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['semester']

    def __str__(self):
        return f"{self.semester}"

    @property
    def semester_number(self):
        """Extract numeric value from semester string (e.g., '1st' -> 1)"""
        if self.semester:
            return int(self.semester.replace('st', '').replace('nd', '').replace('rd', '').replace('th', ''))
        return 0

    @property
    def is_odd_semester(self):
        """Check if semester is odd (1st, 3rd, 5th, 7th)"""
        return self.semester_number % 2 == 1

    @property
    def is_even_semester(self):
        """Check if semester is even (2nd, 4th, 6th, 8th)"""
        return self.semester_number % 2 == 0

    def save(self, *args, **kwargs):
        """Override save to ensure only one semester type (odd or even) is active at a time"""
        if self.is_current_semester:
            # If this semester is being set as current, deactivate others of the same type
            if self.is_odd_semester:
                # Deactivate all other odd semesters
                Semester.objects.filter(
                    is_current_semester=True
                ).exclude(pk=self.pk).update(is_current_semester=False)
            else:
                # Deactivate all other even semesters
                Semester.objects.filter(
                    is_current_semester=True
                ).exclude(pk=self.pk).update(is_current_semester=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current_odd_semester(cls):
        """Get the currently active odd semester"""
        return cls.objects.filter(
            is_current_semester=True,
            semester__in=[FIRST, THIRD, FIFTH, SEVENTH]
        ).first()

    @classmethod
    def get_current_even_semester(cls):
        """Get the currently active even semester"""
        return cls.objects.filter(
            is_current_semester=True,
            semester__in=[SECOND, FOURTH, SIXTH, EIGHTH]
        ).first()

    @classmethod
    def get_active_semesters(cls):
        """Get all currently active semesters (should be 0, 1, or 2)"""
        return cls.objects.filter(is_current_semester=True)

    @classmethod
    def can_activate_semester(cls, semester_value, current_semester_pk=None):
        """Check if a semester can be activated without conflicts"""
        if not semester_value:
            return False
        
        # Extract semester number
        semester_num = int(semester_value.replace('st', '').replace('nd', '').replace('rd', '').replace('th', ''))
        is_odd = semester_num % 2 == 1
        
        # Check if there's already an active semester of the same type
        if is_odd:
            existing = cls.objects.filter(
                is_current_semester=True,
                semester__in=[FIRST, THIRD, FIFTH, SEVENTH]
            )
        else:
            existing = cls.objects.filter(
                is_current_semester=True,
                semester__in=[SECOND, FOURTH, SIXTH, EIGHTH]
            )
        
        # If we're editing an existing semester, exclude it from the conflict check
        if current_semester_pk:
            existing = existing.exclude(pk=current_semester_pk)
        
        # Can activate if no conflicts exist
        return not existing.exists()


class ActivityLog(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.created_at}]{self.message}"


class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class StudentMetrics(models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE)
    attendance_percent = models.FloatField(default=0.0)
    course_grades_avg = models.FloatField(default=0.0)
    grade_avg = models.FloatField(default=0.0)
    credit_hours = models.FloatField(default=0.0)
    age_at_enroll = models.FloatField(default=0.0)
    days_since_last_login = models.FloatField(default=0.0)
    risk_score = models.FloatField(default=0.0)
    residency = models.CharField(max_length=32, blank=True, null=True)
    financial_aid = models.CharField(max_length=32, blank=True, null=True)
    pandemic_effect = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"Metrics({self.user.username})"


class PredictionLog(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    requested_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='pred_requested')
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=32)
    predicted_marks = models.FloatField()
    features_snapshot = models.JSONField()

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"Pred({self.user.username}) {self.category} {self.predicted_marks:.2f} at {self.created_at}"


# -----------------------------
# Timetabling domain
# -----------------------------


class Batch(models.Model):
    title = models.CharField(max_length=64)
    program = models.ForeignKey('course.Program', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} ({self.program.title})"


class Classroom(models.Model):
    name = models.CharField(max_length=64, unique=True)
    capacity = models.PositiveIntegerField(default=40)

    def __str__(self):
        return self.name


class CourseOffering(models.Model):
    program = models.ForeignKey('course.Program', on_delete=models.CASCADE)
    course = models.ForeignKey('course.Course', on_delete=models.CASCADE)
    lecturer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, limit_choices_to={'is_lecturer': True})
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    lectures_per_week = models.PositiveIntegerField(default=3)

    def __str__(self):
        return f"{self.program.title} - {self.course.title} - {self.batch.title}"
    
    def get_enrolled_students(self):
        """Get all students enrolled in this course offering."""
        User = get_user_model()
        return User.objects.filter(
            is_student=True,
            studentenrollment__course_offering=self,
            studentenrollment__is_active=True
        ).order_by('first_name', 'last_name')
    
    def get_total_working_days(self, start_date=None, end_date=None):
        """Get total working days for this course between dates."""
        from datetime import date
        if not start_date:
            start_date = date.today().replace(month=1, day=1)  # Start of year
        if not end_date:
            end_date = date.today()
        
        working_days = CollegeCalendar.objects.filter(
            date__range=[start_date, end_date],
            is_working_day=True
        ).count()
        return working_days
    
    def get_scheduled_classes(self, start_date=None, end_date=None):
        """Get total scheduled classes for this course between dates."""
        from datetime import date
        if not start_date:
            start_date = date.today().replace(month=1, day=1)  # Start of year
        if not end_date:
            end_date = date.today()
        
        # Calculate based on lectures per week and working days
        working_days = self.get_total_working_days(start_date, end_date)
        weeks = working_days / 5  # Assuming 5 working days per week
        return int(weeks * self.lectures_per_week)


class TimetableSlot(models.Model):
    DAY_CHOICES = (
        (0, 'Mon'), (1, 'Tue'), (2, 'Wed'), (3, 'Thu'), (4, 'Fri'), (5, 'Sat')
    )
    day = models.PositiveSmallIntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE)

    class Meta:
        unique_together = (
            ('day', 'start_time', 'classroom'),  # room clash
            ('day', 'start_time', 'offering'),   # offering/lecturer clash
        )

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time}-{self.end_time} {self.classroom} {self.offering}"


# -----------------------------
# Student Enrollment System
# -----------------------------

class StudentEnrollment(models.Model):
    """Model to track student enrollment in specific course offerings."""
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, limit_choices_to={'is_student': True})
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE)
    enrolled_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'course_offering')
        ordering = ['student__first_name', 'course_offering__course__title']

    def __str__(self):
        return f"{self.student.get_full_name} - {self.course_offering.course.title} ({self.course_offering.batch.title})"


# -----------------------------
# Attendance Management System
# -----------------------------

class Attendance(models.Model):
    """Model to track student attendance for specific courses and batches."""
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, limit_choices_to={'is_student': True})
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE)
    date = models.DateField()
    is_present = models.BooleanField(default=False)
    marked_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='attendance_marked', limit_choices_to={'is_lecturer': True})
    marked_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'course_offering', 'date')
        ordering = ['-date', 'student__first_name']

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student.get_full_name} - {self.course_offering.course.title} - {self.date} - {status}"
    
    @property
    def attendance_percentage(self):
        """Calculate attendance percentage for this student in this course."""
        from .utils import get_attendance_percentage
        from datetime import date
        return get_attendance_percentage(self.student, self.course_offering, start_date=None, end_date=date.today())


class AttendanceSession(models.Model):
    """Model to track when attendance sessions are conducted."""
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE)
    date = models.DateField()
    conducted_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE, limit_choices_to={'is_lecturer': True})
    conducted_at = models.DateTimeField(auto_now_add=True)
    total_students = models.PositiveIntegerField(default=0)
    present_students = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('course_offering', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.course_offering.course.title} - {self.date} - {self.present_students}/{self.total_students}"


class CollegeCalendar(models.Model):
    """Model to track college working days and holidays."""
    date = models.DateField(unique=True)
    is_working_day = models.BooleanField(default=True)
    is_holiday = models.BooleanField(default=False)
    holiday_name = models.CharField(max_length=100, blank=True, null=True)
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    semester = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        if self.is_holiday:
            return f"{self.date} - {self.holiday_name} (Holiday)"
        return f"{self.date} - {'Working Day' if self.is_working_day else 'Non-working Day'}"


class StudentFeedback(models.Model):
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='feedback_given')
    lecturer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='feedback_received', limit_choices_to={'is_lecturer': True})
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="Rating from 1 to 5 stars")
    message = models.TextField(help_text="Improvement suggestions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'lecturer']
        ordering = ['-created_at']
        verbose_name = "Student Feedback"
        verbose_name_plural = "Student Feedback"
    
    def __str__(self):
        return f"Feedback from {self.student} to {self.lecturer} - {self.rating} stars"
    
    @property
    def rating_stars(self):
        """Return rating as stars for display"""
        return "★" * self.rating + "☆" * (5 - self.rating)
    
    @classmethod
    def get_average_rating_for_lecturer(cls, lecturer):
        """Get average rating for a specific lecturer"""
        feedback = cls.objects.filter(lecturer=lecturer)
        if feedback.exists():
            return round(feedback.aggregate(Avg('rating'))['rating__avg'], 1)
        return 0
    
    @classmethod
    def get_feedback_count_for_lecturer(cls, lecturer):
        """Get total feedback count for a specific lecturer"""
        return cls.objects.filter(lecturer=lecturer).count()


class Lecturer(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    subject = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['subject']),
        ]

    def __str__(self):
        return self.name


class Feedback(models.Model):
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE)
    teacher_rating = models.IntegerField()
    comments = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.student.username} for {self.lecturer.name}"


class TuitionFee(models.Model):
    """Tuition fee configuration for semesters"""
    semester = models.IntegerField(choices=[(i, f'Semester {i}') for i in range(1, 9)])
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['semester']
        ordering = ['semester']

    def __str__(self):
        return f"Semester {self.semester} - Due: {self.due_date}"

class StudentTuitionFee(models.Model):
    """Individual student tuition fee records"""
    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='tuition_fees')
    semester = models.IntegerField(choices=[(i, f'Semester {i}') for i in range(1, 9)])
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    is_overdue = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'semester']
        ordering = ['student', 'semester']

    def __str__(self):
        return f"{self.student.username} - Semester {self.semester}"

    def save(self, *args, **kwargs):
        # Check if payment is overdue
        if not self.is_paid and self.due_date < timezone.now().date():
            self.is_overdue = True
        else:
            self.is_overdue = False
        
        # Mark as paid if amount is greater than 0
        if self.amount_paid > 0:
            self.is_paid = True
            if not self.payment_date:
                self.payment_date = timezone.now().date()
        
        super().save(*args, **kwargs)

    @property
    def status(self):
        if self.is_paid:
            return "Paid"
        elif self.is_overdue:
            return "Overdue"
        else:
            return "Pending"

    @property
    def status_color(self):
        if self.is_paid:
            return "success"
        elif self.is_overdue:
            return "danger"
        else:
            return "warning"
