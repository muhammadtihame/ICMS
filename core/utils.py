import random
import string
from django.utils.text import slugify
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from typing import Dict, List, Optional, Tuple
import os
import joblib
import numpy as np
import pandas as pd

from typing import Any  # avoid importing accounts at module import time
from .models import StudentMetrics, PredictionLog, TimetableSlot, CourseOffering, Classroom, Batch, Attendance, AttendanceSession
import datetime
try:
    import pulp
except Exception:
    pulp = None


# -----------------------------
# Prediction utilities
# -----------------------------

_CLASSIFIER = None
_REGRESSOR = None
_FEATURE_NAMES: Optional[List[str]] = None


def _load_models_if_needed() -> None:
    global _CLASSIFIER, _REGRESSOR, _FEATURE_NAMES
    if _CLASSIFIER is not None and _REGRESSOR is not None and _FEATURE_NAMES is not None:
        return

    base_dir = settings.BASE_DIR  # project root
    clf_path = os.path.join(base_dir, "lgb_classifier.pkl")
    reg_path = os.path.join(base_dir, "lgb_regressor.pkl")
    feat_path = os.path.join(base_dir, "feature_names.pkl")

    _CLASSIFIER = joblib.load(clf_path)
    _REGRESSOR = joblib.load(reg_path)
    _FEATURE_NAMES = joblib.load(feat_path)


def get_student_by_name(name: str):
    """Find a student by ID/username or full name fragments."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not name:
        return None
    name = name.strip()
    # Try primary key (numeric ID) or username exact first
    if name.isdigit():
        user = User.objects.filter(is_student=True, pk=int(name)).first()
        if user:
            return user
    user = User.objects.filter(is_student=True, username__iexact=name).first()
    if user:
        return user
    # Try first+last contains
    parts = name.split()
    if len(parts) >= 2:
        first, last = parts[0], parts[-1]
        user = (
            User.objects.filter(is_student=True, first_name__icontains=first, last_name__icontains=last)
            .order_by("-date_joined")
            .first()
        )
        if user:
            return user
    # Fallback any match on first or last
    user = (
        User.objects.filter(is_student=True)
        .filter(first_name__icontains=name)[:1]
        .first()
    ) or (
        User.objects.filter(is_student=True)
        .filter(last_name__icontains=name)[:1]
        .first()
    )
    return user


def build_feature_vector_for_student(user: Any) -> Dict[str, float]:
    """Build a features dict for a student aligned to training features.

    Strategy:
    - Start with ZERO defaults for every entry in feature_names.pkl
    - Optionally fill a few obvious fields if available later
    This guarantees no "Missing features" errors and preserves correct order.
    """
    _load_models_if_needed()
    assert _FEATURE_NAMES is not None

    # Start with zeros for all expected features to avoid missing keys
    features: Dict[str, float] = {name: 0.0 for name in _FEATURE_NAMES}

    # Map from StudentMetrics if present
    metrics = StudentMetrics.objects.filter(user=user).first()
    if metrics:
        mapping = {
            "Attendance (%)": metrics.attendance_percent,
            "CourseGradesAvg": metrics.course_grades_avg,
            "GradeAvg": metrics.grade_avg,
            "CreditHours": metrics.credit_hours,
            "AgeAtEnroll": metrics.age_at_enroll,
            "DaysSinceLastLogin": metrics.days_since_last_login,
            "RiskScore": metrics.risk_score,
        }
        for k, v in mapping.items():
            if k in features:
                features[k] = float(v)

        # one-hot categorical examples
        if metrics.residency:
            key = f"Residency_{metrics.residency}"
            if key in features:
                features[key] = 1.0
        if metrics.financial_aid:
            key = f"FinancialAid_{metrics.financial_aid}"
            if key in features:
                features[key] = 1.0
        if metrics.pandemic_effect:
            key = f"PandemicEffect_{metrics.pandemic_effect}"
            if key in features:
                features[key] = 1.0

    # major/program one-hot from Student.program.title if available
    try:
        program_title = getattr(getattr(user, "student", None), "program", None).title
        if program_title:
            one_hot_key = f"Major_{program_title}"
            if one_hot_key in features:
                features[one_hot_key] = 1.0
    except Exception:
        pass

    return features


def align_features(raw_features: Dict[str, float]) -> np.ndarray:
    """Align features to the training order from feature_names.pkl.

    Any absent feature keys are treated as 0.0 to prevent crashes until
    real data mapping is provided.
    """
    _load_models_if_needed()
    assert _FEATURE_NAMES is not None
    values = [raw_features.get(f, 0.0) for f in _FEATURE_NAMES]
    arr = np.asarray(values, dtype=float).reshape(1, -1)
    return arr


def predict_performance(raw_features: Dict[str, float]) -> Dict[str, object]:
    """Run classifier and regressor and return results."""
    _load_models_if_needed()
    X = align_features(raw_features)
    cls = _CLASSIFIER.predict(X)[0]
    reg = float(_REGRESSOR.predict(X)[0])
    # Ensure category mapping is textual
    if isinstance(cls, (int, np.integer)):
        mapping = {0: "Low", 1: "Average", 2: "High"}
        category = mapping.get(int(cls), str(cls))
    else:
        category = str(cls)
    return {"category": category, "marks": reg}


def log_prediction(target_user: Any, requested_by: Any, result: Dict[str, object], features: Dict[str, float]) -> None:
    try:
        PredictionLog.objects.create(
            user=target_user,
            requested_by=requested_by,
            category=str(result.get("category")),
            predicted_marks=float(result.get("marks", 0.0)),
            features_snapshot=features,
        )
    except Exception:
        # Do not break flow if logging fails
        pass


# -----------------------------
# Timetable generation (pulp-based)
# -----------------------------

def generate_comprehensive_timetable() -> Dict[str, int]:
    """
    Generate a comprehensive weekly timetable for all batches.
    Returns a dictionary with counts of created slots per batch.
    """
    # Clear all existing timetable slots
    TimetableSlot.objects.all().delete()

    # Get all course offerings grouped by batch
    offerings_by_batch = {}
    for offering in CourseOffering.objects.select_related('batch', 'course', 'lecturer', 'program').all():
        batch_key = f"{offering.batch.title}"
        if batch_key not in offerings_by_batch:
            offerings_by_batch[batch_key] = []
        offerings_by_batch[batch_key].append(offering)

    # Get all classrooms
    classrooms = list(Classroom.objects.all())
    if not classrooms:
        return {"error": "No classrooms available"}

    # Define time slots (similar to the photo)
    time_slots = [
        ("09:30", "10:15"),
        ("10:15", "11:00"),
        ("11:15", "12:00"),  # After tea break
        ("12:00", "12:45"),
        ("13:30", "14:15"),  # After lunch break
        ("14:15", "15:00"),
        ("15:00", "15:45"),
        ("15:45", "16:15"),
    ]

    # Define days (Monday to Friday)
    days = [0, 1, 2, 3, 4]  # Mon, Tue, Wed, Thu, Fri

    batch_results = {}

    for batch_name, offerings in offerings_by_batch.items():
        if not offerings:
            continue

        created_slots = 0

        # Distribute offerings across the week
        for day in days:
            # Shuffle offerings for variety
            day_offerings = offerings.copy()
            random.shuffle(day_offerings)

            # Assign slots for this day
            for i, offering in enumerate(day_offerings):
                if i >= len(time_slots):
                    break  # Don't exceed available time slots

                start_time_str, end_time_str = time_slots[i]
                start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()

                # Assign to a classroom (round-robin)
                classroom = classrooms[i % len(classrooms)]

                # Check for conflicts
                if not TimetableSlot.objects.filter(
                    day=day,
                    start_time=start_time,
                    classroom=classroom
                ).exists() and not TimetableSlot.objects.filter(
                    day=day,
                    start_time=start_time,
                    offering__lecturer=offering.lecturer
                ).exists():

                    slot = TimetableSlot.objects.create(
                        day=day,
                        start_time=start_time,
                        end_time=end_time,
                        classroom=classroom,
                        offering=offering,
                    )
                    created_slots += 1
                    print(f"Created slot for {batch_name}: {slot}")

        batch_results[batch_name] = created_slots

    return batch_results


def generate_timetable_for_day(selected_day=0, start_hour=9, end_hour=16, slot_minutes=60) -> int:
    """Generate timetable slots for all course offerings for a specific day.
    Returns count of created slots.
    """
    offerings = list(CourseOffering.objects.select_related('lecturer', 'course', 'batch', 'program'))
    rooms = list(Classroom.objects.all())
    if not offerings or not rooms:
        return 0

    # Clear existing timetable for this day only
    TimetableSlot.objects.filter(day=selected_day).delete()

    created = 0
    start_time = datetime.time(hour=start_hour, minute=0)

    for i, offering in enumerate(offerings):
        # Calculate time slot
        slot_hour = start_hour + (i % (end_hour - start_hour))
        if slot_hour >= end_hour:
            break

        start_t = datetime.time(hour=slot_hour, minute=0)
        end_t = (datetime.datetime.combine(datetime.date.today(), start_t) +
                datetime.timedelta(minutes=slot_minutes)).time()

        # Assign to a room (round-robin)
        room = rooms[i % len(rooms)]

        slot = TimetableSlot.objects.create(
            day=selected_day,
            start_time=start_t,
            end_time=end_t,
            classroom=room,
            offering=offering,
        )
        created += 1
        print(f"Created slot: {slot}")

    return created


def generate_timetable_for_batch(batch_id: int) -> int:
    """
    Generate timetable for a specific batch.
    Returns count of created slots.
    """
    try:
        batch = Batch.objects.get(id=batch_id)
    except Batch.DoesNotExist:
        return 0

    # Clear existing slots for this batch
    TimetableSlot.objects.filter(offering__batch=batch).delete()

    # Get offerings for this batch
    offerings = list(CourseOffering.objects.filter(batch=batch).select_related('lecturer', 'course', 'program'))
    classrooms = list(Classroom.objects.all())

    if not offerings or not classrooms:
        return 0

    # Define time slots
    time_slots = [
        ("09:30", "10:15"),
        ("10:15", "11:00"),
        ("11:15", "12:00"),
        ("12:00", "12:45"),
        ("13:30", "14:15"),
        ("14:15", "15:00"),
        ("15:00", "15:45"),
        ("15:45", "16:15"),
    ]

    days = [0, 1, 2, 3, 4]  # Mon to Fri
    created = 0

    for day in days:
        # Shuffle offerings for variety
        day_offerings = offerings.copy()
        random.shuffle(day_offerings)

        for i, offering in enumerate(day_offerings):
            if i >= len(time_slots):
                break

            start_time_str, end_time_str = time_slots[i]
            start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()
            end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()

            # Assign classroom
            classroom = classrooms[i % len(classrooms)]

            # Check for conflicts
            if not TimetableSlot.objects.filter(
                day=day,
                start_time=start_time,
                classroom=classroom
            ).exists() and not TimetableSlot.objects.filter(
                day=day,
                start_time=start_time,
                offering__lecturer=offering.lecturer
            ).exists():

                slot = TimetableSlot.objects.create(
                    day=day,
                    start_time=start_time,
                    end_time=end_time,
                    classroom=classroom,
                    offering=offering,
                )
                created += 1
                print(f"Created slot for {batch.title}: {slot}")

    return created


def get_timetable_data_for_batch(batch_id: int = None) -> Dict:
    """
    Get timetable data organized by batch and day.
    If batch_id is provided, returns data for that specific batch.
    """
    if batch_id:
        slots = TimetableSlot.objects.filter(
            offering__batch_id=batch_id
        ).select_related(
            'offering', 'offering__program', 'offering__course',
            'offering__batch', 'offering__lecturer', 'classroom'
        ).order_by('day', 'start_time')
    else:
        slots = TimetableSlot.objects.select_related(
            'offering', 'offering__program', 'offering__course',
            'offering__batch', 'offering__lecturer', 'classroom'
        ).order_by('offering__batch', 'day', 'start_time')

    # Organize by batch and day
    timetable_data = {}

    for slot in slots:
        batch_name = slot.offering.batch.title
        day = slot.day

        if batch_name not in timetable_data:
            timetable_data[batch_name] = {}

        if day not in timetable_data[batch_name]:
            timetable_data[batch_name][day] = []

        timetable_data[batch_name][day].append({
            'start_time': slot.start_time,
            'end_time': slot.end_time,
            'course': slot.offering.course.title,
            'lecturer': f"{slot.offering.lecturer.first_name} {slot.offering.lecturer.last_name}",
            'classroom': slot.classroom.name,
            'program': slot.offering.program.title,
        })

    return timetable_data


def get_all_batches_with_timetable() -> List[Dict]:
    """
    Get all batches with their timetable status.
    """
    batches = Batch.objects.select_related('program').all()
    result = []

    for batch in batches:
        slot_count = TimetableSlot.objects.filter(offering__batch=batch).count()
        result.append({
            'id': batch.id,
            'title': batch.title,
            'program': batch.program.title,
            'has_timetable': slot_count > 0,
            'slot_count': slot_count,
        })

    return result


def send_email(user, subject, msg):
    send_mail(
        subject,
        msg,
        settings.EMAIL_FROM_ADDRESS,
        [user.email],
        fail_silently=False,
    )


def send_html_email(subject, recipient_list, template, context):
    """A function responsible for sending HTML email"""
    # Render the HTML template
    html_message = render_to_string(template, context)

    # Generate plain text version of the email (optional)
    plain_message = strip_tags(html_message)

    # Send the email
    send_mail(
        subject,
        plain_message,
        settings.EMAIL_FROM_ADDRESS,
        recipient_list,
        html_message=html_message,
    )


def random_string_generator(size=10, chars=string.ascii_lowercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))


def unique_slug_generator(instance, new_slug=None):
    """
    Assumes the instance has a model with a slug field and a title
    character (char) field.
    """
    if new_slug is not None:
        slug = new_slug
    else:
        slug = slugify(instance.title)

    klass = instance.__class__
    qs_exists = klass.objects.filter(slug=slug).exists()
    if qs_exists:
        new_slug = f"{slug}-{random_string_generator(size=4)}"
        return unique_slug_generator(instance, new_slug=new_slug)
    return slug


def get_attendance_percentage(student, course_offering, start_date, end_date):
    """
    Calculate attendance percentage for a student in a specific course within a date range.
    """
    from .models import Attendance, CollegeCalendar
    from datetime import datetime, timedelta
    
    # Get all attendance records for the student in this course within the date range
    attendance_records = Attendance.objects.filter(
        student=student,
        course_offering=course_offering,
        date__range=[start_date, end_date]
    )
    
    # Count total classes conducted (working days)
    working_days = CollegeCalendar.objects.filter(
        date__range=[start_date, end_date],
        is_working_day=True
    ).count()
    
    # Count classes attended
    classes_attended = attendance_records.filter(is_present=True).count()
    
    # Calculate percentage
    if working_days > 0:
        percentage = (classes_attended / working_days) * 100
        return round(percentage, 2)
    else:
        return 0.0


def get_student_attendance_summary(student, course_offering=None, start_date=None, end_date=None):
    """
    Get comprehensive attendance summary for a student.
    """
    from .models import Attendance, CourseOffering
    from datetime import datetime, timedelta
    
    if not start_date:
        start_date = datetime.now().date() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now().date()
    
    if course_offering:
        # Single course summary
        attendance_records = Attendance.objects.filter(
            student=student,
            course_offering=course_offering,
            date__range=[start_date, end_date]
        )
        
        total_classes = attendance_records.count()
        classes_attended = attendance_records.filter(is_present=True).count()
        percentage = get_attendance_percentage(student, course_offering, start_date, end_date)
        
        return {
            'course': course_offering.course.title,
            'batch': course_offering.batch.title,
            'total_classes': total_classes,
            'classes_attended': classes_attended,
            'percentage': percentage,
            'start_date': start_date,
            'end_date': end_date
        }
    else:
        # All courses summary
        course_offerings = CourseOffering.objects.filter(batch__students=student)
        summary = []
        
        for offering in course_offerings:
            attendance_records = Attendance.objects.filter(
                student=student,
                course_offering=offering,
                date__range=[start_date, end_date]
            )
            
            total_classes = attendance_records.count()
            classes_attended = attendance_records.filter(is_present=True).count()
            percentage = get_attendance_percentage(student, offering, start_date, end_date)
            
            summary.append({
                'course': offering.course.title,
                'batch': offering.batch.title,
                'total_classes': total_classes,
                'classes_attended': classes_attended,
                'percentage': percentage
            })
        
        return summary


def get_batch_attendance_summary(batch, course_offering=None, start_date=None, end_date=None):
    """
    Get attendance summary for all students in a batch.
    """
    from .models import Attendance
    from django.contrib.auth import get_user_model
    from datetime import datetime, timedelta
    User = get_user_model()
    
    if not start_date:
        start_date = datetime.now().date() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now().date()
    
    students = User.objects.filter(is_student=True, batch=batch)
    summary = []
    
    for student in students:
        if course_offering:
            # Single course for all students
            student_summary = get_student_attendance_summary(student, course_offering, start_date, end_date)
        else:
            # All courses for student
            student_summaries = get_student_attendance_summary(student, None, start_date, end_date)
            student_summary = {
                'student': student.get_full_name,
                'student_id': student.username,
                'courses': student_summaries
            }
        
        summary.append(student_summary)
    
    return summary


def mark_bulk_attendance(course_offering, date, present_students, marked_by, notes=""):
    """
    Mark attendance for multiple students at once.
    """
    from .models import Attendance, AttendanceSession
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Get all students in the batch
    batch_students = User.objects.filter(is_student=True, batch=course_offering.batch)
    
    # Create or update attendance records
    attendance_records = []
    for student in batch_students:
        is_present = student in present_students
        
        attendance, created = Attendance.objects.get_or_create(
            student=student,
            course_offering=course_offering,
            date=date,
            defaults={
                'is_present': is_present,
                'marked_by': marked_by,
                'notes': notes
            }
        )
        
        if not created:
            attendance.is_present = is_present
            attendance.marked_by = marked_by
            attendance.notes = notes
            attendance.save()
        
        attendance_records.append(attendance)
    
    # Create or update attendance session
    session, created = AttendanceSession.objects.get_or_create(
        course_offering=course_offering,
        date=date,
        defaults={
            'conducted_by': marked_by,
            'total_students': len(batch_students),
            'present_students': len(present_students),
            'notes': notes
        }
    )
    
    if not created:
        session.conducted_by = marked_by
        session.total_students = len(batch_students)
        session.present_students = len(present_students)
        session.notes = notes
        session.save()
    
    return attendance_records, session


def get_lecturer_enrolled_students(lecturer, course_offering=None):
    """
    Get all students enrolled in courses taught by a lecturer.
    If course_offering is specified, return only students enrolled in that specific course.
    """
    from .models import StudentEnrollment
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if course_offering:
        # Return students enrolled in specific course
        return User.objects.filter(
            is_student=True,
            studentenrollment__course_offering=course_offering,
            studentenrollment__is_active=True
        ).order_by('first_name', 'last_name')
    else:
        # Return all students enrolled in lecturer's courses
        return User.objects.filter(
            is_student=True,
            studentenrollment__course_offering__lecturer=lecturer,
            studentenrollment__is_active=True
        ).distinct().order_by('first_name', 'last_name')


def calculate_attendance_percentage(student, course_offering, start_date=None, end_date=None):
    """
    Calculate attendance percentage for a student in a specific course.
    Takes into account:
    - Total classes scheduled for the course
    - Number of college working days
    - Number of classes the student attended
    """
    from datetime import date
    from .models import Attendance, CollegeCalendar, AttendanceSession
    
    if not start_date:
        start_date = date.today().replace(month=1, day=1)  # Start of year
    if not end_date:
        end_date = date.today()
    
    # Get total scheduled classes for this course
    total_scheduled = course_offering.get_scheduled_classes(start_date, end_date)
    
    # Get total working days in the period
    total_working_days = course_offering.get_total_working_days(start_date, end_date)
    
    # Get classes actually conducted (attendance sessions)
    conducted_sessions = AttendanceSession.objects.filter(
        course_offering=course_offering,
        date__range=[start_date, end_date]
    ).count()
    
    # Get student's attendance records
    attendance_records = Attendance.objects.filter(
        student=student,
        course_offering=course_offering,
        date__range=[start_date, end_date]
    )
    
    # Count present days
    present_days = attendance_records.filter(is_present=True).count()
    
    # Calculate percentage based on conducted sessions
    if conducted_sessions > 0:
        percentage = (present_days / conducted_sessions) * 100
    else:
        percentage = 0.0
    
    return {
        'student': student,
        'course': course_offering.course.title,
        'batch': course_offering.batch.title,
        'start_date': start_date,
        'end_date': end_date,
        'total_scheduled_classes': total_scheduled,
        'total_working_days': total_working_days,
        'conducted_sessions': conducted_sessions,
        'present_days': present_days,
        'absent_days': conducted_sessions - present_days,
        'percentage': round(percentage, 2),
        'attendance_records': attendance_records
    }


def search_enrolled_students(lecturer, query, course_offering=None):
    """
    Search for enrolled students by name, ID, or email.
    Returns only students enrolled in lecturer's courses.
    """
    from django.db.models import Q
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    enrolled_students = get_lecturer_enrolled_students(lecturer, course_offering)
    
    if not query:
        return enrolled_students
    
    return enrolled_students.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(username__icontains=query) |
        Q(email__icontains=query)
    )


def get_course_attendance_summary(course_offering, date=None):
    """
    Get attendance summary for a specific course on a specific date.
    """
    from datetime import date as today_date
    
    if not date:
        date = today_date.today()
    
    # Get all enrolled students
    enrolled_students = course_offering.get_enrolled_students()
    
    # Get attendance records for this date
    attendance_records = Attendance.objects.filter(
        course_offering=course_offering,
        date=date
    )
    
    # Create summary
    summary = {
        'course': course_offering.course.title,
        'batch': course_offering.batch.title,
        'date': date,
        'total_enrolled': enrolled_students.count(),
        'present_count': attendance_records.filter(is_present=True).count(),
        'absent_count': attendance_records.filter(is_present=False).count(),
        'not_marked': enrolled_students.count() - attendance_records.count(),
        'attendance_records': attendance_records,
        'enrolled_students': enrolled_students
    }
    
    # Calculate percentage
    if summary['total_enrolled'] > 0:
        summary['attendance_percentage'] = round(
            (summary['present_count'] / summary['total_enrolled']) * 100, 2
        )
    else:
        summary['attendance_percentage'] = 0.0
    
    return summary


def mark_attendance_for_course(course_offering, date, present_students, marked_by, notes=""):
    """
    Mark attendance for all enrolled students in a course.
    """
    from .models import Attendance, AttendanceSession
    
    enrolled_students = course_offering.get_enrolled_students()
    attendance_records = []
    
    for student in enrolled_students:
        is_present = student in present_students
        
        # Create or update attendance record
        attendance, created = Attendance.objects.get_or_create(
            student=student,
            course_offering=course_offering,
            date=date,
            defaults={
                'is_present': is_present,
                'marked_by': marked_by,
                'notes': notes
            }
        )
        
        if not created:
            attendance.is_present = is_present
            attendance.marked_by = marked_by
            attendance.notes = notes
            attendance.save()
        
        attendance_records.append(attendance)
    
    # Create or update attendance session
    session, created = AttendanceSession.objects.get_or_create(
        course_offering=course_offering,
        date=date,
        defaults={
            'conducted_by': marked_by,
            'total_students': len(enrolled_students),
            'present_students': len(present_students),
            'notes': notes
        }
    )
    
    if not created:
        session.conducted_by = marked_by
        session.total_students = len(enrolled_students)
        session.present_students = len(present_students)
        session.notes = notes
        session.save()
    
    return attendance_records, session


def get_lecturer_courses(user):
    """
    Get all courses assigned to a lecturer.
    """
    from .models import CourseOffering
    
    if user.is_superuser:
        return CourseOffering.objects.all()
    elif user.is_lecturer:
        return CourseOffering.objects.filter(lecturer=user)
    else:
        return CourseOffering.objects.none()


def search_students(query):
    """
    Search students by name or ID.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()
    
    if not query:
        return User.objects.filter(is_student=True)
    
    return User.objects.filter(
        is_student=True
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(username__icontains=query) |
        Q(email__icontains=query)
    )


def get_detention_list(threshold_percentage=75.0, start_date=None, end_date=None):
    """
    Get list of students with attendance below threshold.
    """
    from .models import CourseOffering
    from django.contrib.auth import get_user_model
    from datetime import datetime, timedelta
    User = get_user_model()
    
    if not start_date:
        start_date = datetime.now().date() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now().date()
    
    detention_list = []
    course_offerings = CourseOffering.objects.all()
    
    for offering in course_offerings:
        students = User.objects.filter(is_student=True, batch=offering.batch)
        
        for student in students:
            percentage = get_attendance_percentage(student, offering, start_date, end_date)
            
            if percentage < threshold_percentage:
                detention_list.append({
                    'student': student,
                    'course': offering.course.title,
                    'batch': offering.batch.title,
                    'percentage': percentage,
                    'threshold': threshold_percentage
                })
    
    return detention_list
