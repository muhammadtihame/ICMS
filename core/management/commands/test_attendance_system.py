from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import CourseOffering, StudentEnrollment, Attendance, AttendanceSession
from core.utils import get_lecturer_courses, get_lecturer_enrolled_students, mark_attendance_for_course
from datetime import date
import traceback

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the attendance management system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing attendance management system...'))
        
        # Test 1: Check if lecturers have courses
        lecturers = User.objects.filter(is_lecturer=True)
        self.stdout.write(f'Found {lecturers.count()} lecturers')
        
        for lecturer in lecturers[:3]:  # Test first 3 lecturers
            courses = get_lecturer_courses(lecturer)
            self.stdout.write(f'  - {lecturer.get_full_name}: {courses.count()} courses')
            
            if courses.exists():
                course = courses.first()
                enrolled_students = get_lecturer_enrolled_students(lecturer, course)
                self.stdout.write(f'    Course "{course.course.title}": {enrolled_students.count()} enrolled students')
                
                # Test marking attendance
                if enrolled_students.exists():
                    present_students = list(enrolled_students[:2])  # Mark first 2 as present
                    try:
                        attendance_records, session = mark_attendance_for_course(
                            course, date.today(), present_students, lecturer, "Test attendance"
                        )
                        self.stdout.write(f'    ✅ Successfully marked attendance for {len(attendance_records)} students')
                        
                        # Verify attendance records were created
                        attendance_count = Attendance.objects.filter(
                            course_offering=course,
                            date=date.today()
                        ).count()
                        self.stdout.write(f'    ✅ Created {attendance_count} attendance records')
                        
                        # Verify session was created
                        session_count = AttendanceSession.objects.filter(
                            course_offering=course,
                            date=date.today()
                        ).count()
                        self.stdout.write(f'    ✅ Created {session_count} attendance session')
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'    ❌ Error marking attendance: {e}'))
                        self.stdout.write(self.style.ERROR(f'    ❌ Traceback: {traceback.format_exc()}'))
        
        # Test 2: Check student enrollments
        total_enrollments = StudentEnrollment.objects.count()
        self.stdout.write(f'Total student enrollments: {total_enrollments}')
        
        # Test 3: Check attendance records
        total_attendance = Attendance.objects.count()
        self.stdout.write(f'Total attendance records: {total_attendance}')
        
        # Test 4: Check attendance sessions
        total_sessions = AttendanceSession.objects.count()
        self.stdout.write(f'Total attendance sessions: {total_sessions}')
        
        self.stdout.write(self.style.SUCCESS('Attendance system test completed!'))
