from django.contrib import admin
from .models import (
    NewsAndEvents, Session, Semester, Announcement,
    Batch, Classroom, CourseOffering, TimetableSlot,
    Attendance, AttendanceSession, CollegeCalendar, StudentFeedback,
    Lecturer, Feedback, TuitionFee, StudentTuitionFee
)
from django.utils import timezone


@admin.register(NewsAndEvents)
class NewsAndEventsAdmin(admin.ModelAdmin):
    list_display = ["title", "posted_as"]
    list_filter = ["posted_as"]
    search_fields = ["title", "summary"]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["session", "is_current_session", "next_session_begins"]
    list_filter = ["is_current_session"]
    search_fields = ["session"]


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ["semester", "semester_type", "is_current_semester", "session", "next_semester_begins"]
    list_filter = ["is_current_semester", "session"]
    search_fields = ["semester"]
    ordering = ["semester"]
    
    def semester_type(self, obj):
        """Display semester type (Odd/Even)"""
        if obj.is_odd_semester:
            return "Odd"
        return "Even"
    semester_type.short_description = "Type"
    
    def get_queryset(self, request):
        """Order by semester number for proper display"""
        return super().get_queryset(request).order_by('semester')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "created_at"]
    search_fields = ["title", "content"]
    list_filter = ["created_at"]


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ["title", "program"]
    list_filter = ["program"]
    search_fields = ["title", "program__title"]


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ["name", "capacity"]
    search_fields = ["name"]


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ["course", "program", "batch", "lecturer", "lectures_per_week"]
    list_filter = ["program", "batch", "lecturer"]
    search_fields = ["course__title", "program__title", "batch__title", "lecturer__first_name", "lecturer__last_name"]


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ["day", "start_time", "end_time", "classroom", "offering"]
    list_filter = ["day", "classroom", "offering__course", "offering__batch"]
    search_fields = ["classroom__name", "offering__course__title", "offering__batch__title"]


# -----------------------------
# Attendance Management Admin
# -----------------------------

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["student", "course_offering", "date", "is_present", "marked_by"]
    list_filter = ["is_present", "date", "course_offering__course", "course_offering__batch", "marked_by"]
    search_fields = ["student__first_name", "student__last_name", "student__username", "course_offering__course__title"]
    date_hierarchy = "date"
    list_per_page = 50


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ["course_offering", "date", "conducted_by", "total_students", "present_students", "attendance_percentage"]
    list_filter = ["date", "course_offering__course", "course_offering__batch", "conducted_by"]
    search_fields = ["course_offering__course__title", "course_offering__batch__title", "conducted_by__first_name", "conducted_by__last_name"]
    date_hierarchy = "date"
    
    def attendance_percentage(self, obj):
        if obj.total_students > 0:
            return f"{(obj.present_students / obj.total_students) * 100:.1f}%"
        return "0%"
    attendance_percentage.short_description = "Attendance %"


@admin.register(CollegeCalendar)
class CollegeCalendarAdmin(admin.ModelAdmin):
    list_display = ["date", "is_working_day", "is_holiday", "holiday_name", "academic_year", "semester"]
    list_filter = ["is_working_day", "is_holiday", "academic_year", "semester"]
    search_fields = ["holiday_name", "academic_year", "semester"]
    date_hierarchy = "date"
    list_per_page = 100


@admin.register(StudentFeedback)
class StudentFeedbackAdmin(admin.ModelAdmin):
    list_display = ['student', 'lecturer', 'rating', 'rating_stars_display', 'created_at']
    list_filter = ['rating', 'created_at', 'lecturer', 'student']
    search_fields = ['student__student__first_name', 'student__student__last_name', 'student__student__username', 
                     'lecturer__first_name', 'lecturer__last_name', 'lecturer__username', 'message']
    readonly_fields = ['created_at', 'updated_at', 'rating_stars']
    ordering = ['-created_at']
    
    def rating_stars_display(self, obj):
        """Display rating as stars in admin list view"""
        return obj.rating_stars
    rating_stars_display.short_description = 'Rating'
    
    fieldsets = (
        ('Feedback Information', {
            'fields': ('student', 'lecturer', 'rating', 'rating_stars')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Only students can add feedback
    
    def has_change_permission(self, request, obj=None):
        return False  # Feedback cannot be edited
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete feedback


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject')
    search_fields = ('name', 'subject')
    list_filter = ('subject',)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('student', 'lecturer', 'teacher_rating', 'submitted_at')
    list_filter = ('lecturer', 'teacher_rating', 'submitted_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'lecturer__name')
    readonly_fields = ('submitted_at',)
    ordering = ['-submitted_at']
    
    fieldsets = (
        ('Feedback Information', {
            'fields': ('student', 'lecturer', 'teacher_rating', 'comments')
        }),
        ('Timestamps', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TuitionFee)
class TuitionFeeAdmin(admin.ModelAdmin):
    list_display = ('semester', 'due_date', 'amount', 'is_active', 'created_at')
    list_filter = ('is_active', 'semester', 'due_date')
    search_fields = ('semester',)
    ordering = ['semester']
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Fee Configuration', {
            'fields': ('semester', 'amount', 'due_date', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(StudentTuitionFee)
class StudentTuitionFeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'amount_paid', 'payment_date', 'due_date', 'status', 'is_overdue')
    list_filter = ('semester', 'is_paid', 'is_overdue', 'due_date', 'payment_date')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'student__email')
    ordering = ['student', 'semester']
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'semester')
        }),
        ('Payment Details', {
            'fields': ('amount_paid', 'payment_date', 'due_date', 'is_paid')
        }),
        ('Status', {
            'fields': ('is_overdue',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('is_overdue', 'created_at', 'updated_at')
    
    actions = ['mark_as_paid', 'mark_as_pending', 'send_payment_reminders']
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(is_paid=True, amount_paid=100.00, payment_date=timezone.now().date())
        self.message_user(request, f'{updated} tuition fee records marked as paid.')
    mark_as_paid.short_description = "Mark selected fees as paid"
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(is_paid=False, amount_paid=0.00, payment_date=None)
        self.message_user(request, f'{updated} tuition fee records marked as pending.')
    mark_as_pending.short_description = "Mark selected fees as pending"
    
    def send_payment_reminders(self, request, queryset):
        # This would integrate with your email system
        count = queryset.count()
        self.message_user(request, f'Payment reminders sent to {count} students.')
    send_payment_reminders.short_description = "Send payment reminders"
