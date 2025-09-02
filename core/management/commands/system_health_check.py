from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import CourseOffering, StudentEnrollment, Attendance, AttendanceSession, Batch, Session, Semester
from course.models import Course, Program, CourseAllocation
from accounts.models import Student, Parent
from datetime import date

User = get_user_model()


class Command(BaseCommand):
    help = 'Comprehensive system health check for the college management system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix common issues automatically',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Starting Comprehensive System Health Check...'))
        self.stdout.write('=' * 60)
        
        fix_mode = options['fix']
        issues_found = []
        fixes_applied = []
        
        # 1. Check User Management
        self.stdout.write('\n👥 USER MANAGEMENT CHECK:')
        total_users = User.objects.count()
        students = User.objects.filter(is_student=True)
        lecturers = User.objects.filter(is_lecturer=True)
        parents = User.objects.filter(is_parent=True)
        
        self.stdout.write(f'  ✅ Total Users: {total_users}')
        self.stdout.write(f'  ✅ Students: {students.count()}')
        self.stdout.write(f'  ✅ Lecturers: {lecturers.count()}')
        self.stdout.write(f'  ✅ Parents: {parents.count()}')
        
        # Check for users without proper profiles
        students_without_profiles = students.exclude(student__isnull=False)
        if students_without_profiles.exists():
            issues_found.append(f'{students_without_profiles.count()} students without profiles')
            if fix_mode:
                for student in students_without_profiles:
                    Student.objects.get_or_create(user=student)
                fixes_applied.append(f'Created {students_without_profiles.count()} student profiles')
        
        # 2. Check Academic Structure
        self.stdout.write('\n📚 ACADEMIC STRUCTURE CHECK:')
        programs = Program.objects.count()
        courses = Course.objects.count()
        batches = Batch.objects.count()
        sessions = Session.objects.count()
        semesters = Semester.objects.count()
        
        self.stdout.write(f'  ✅ Programs: {programs}')
        self.stdout.write(f'  ✅ Courses: {courses}')
        self.stdout.write(f'  ✅ Batches: {batches}')
        self.stdout.write(f'  ✅ Sessions: {sessions}')
        self.stdout.write(f'  ✅ Semesters: {semesters}')
        
        # Check for missing current session/semester
        current_session = Session.objects.filter(is_current_session=True).first()
        if not current_session:
            issues_found.append('No current session set')
            if fix_mode:
                session = Session.objects.first()
                if session:
                    session.is_current_session = True
                    session.save()
                    fixes_applied.append('Set first session as current')
        
        current_semester = Semester.objects.filter(is_current_semester=True).first()
        if not current_semester:
            issues_found.append('No current semester set')
            if fix_mode:
                semester = Semester.objects.first()
                if semester:
                    semester.is_current_semester = True
                    semester.save()
                    fixes_applied.append('Set first semester as current')
        
        # 3. Check Course Management
        self.stdout.write('\n📖 COURSE MANAGEMENT CHECK:')
        course_offerings = CourseOffering.objects.count()
        course_allocations = CourseAllocation.objects.count()
        
        self.stdout.write(f'  ✅ Course Offerings: {course_offerings}')
        self.stdout.write(f'  ✅ Course Allocations: {course_allocations}')
        
        # Check for courses without lecturers
        courses_without_lecturers = CourseOffering.objects.filter(lecturer__isnull=True)
        if courses_without_lecturers.exists():
            issues_found.append(f'{courses_without_lecturers.count()} courses without lecturers')
        
        # 4. Check Student Enrollment
        self.stdout.write('\n🎓 STUDENT ENROLLMENT CHECK:')
        enrollments = StudentEnrollment.objects.count()
        active_enrollments = StudentEnrollment.objects.filter(is_active=True).count()
        
        self.stdout.write(f'  ✅ Total Enrollments: {enrollments}')
        self.stdout.write(f'  ✅ Active Enrollments: {active_enrollments}')
        
        # Check for students without enrollments
        students_without_enrollments = students.exclude(studentenrollment__isnull=False)
        if students_without_enrollments.exists():
            issues_found.append(f'{students_without_enrollments.count()} students without course enrollments')
        
        # 5. Check Attendance System
        self.stdout.write('\n📊 ATTENDANCE SYSTEM CHECK:')
        attendance_records = Attendance.objects.count()
        attendance_sessions = AttendanceSession.objects.count()
        
        self.stdout.write(f'  ✅ Attendance Records: {attendance_records}')
        self.stdout.write(f'  ✅ Attendance Sessions: {attendance_sessions}')
        
        # Test attendance marking functionality
        try:
            from core.utils import get_lecturer_courses, get_lecturer_enrolled_students, mark_attendance_for_course
            test_lecturer = lecturers.first()
            if test_lecturer:
                test_courses = get_lecturer_courses(test_lecturer)
                if test_courses.exists():
                    test_course = test_courses.first()
                    test_students = get_lecturer_enrolled_students(test_lecturer, test_course)
                    if test_students.exists():
                        # Test attendance marking
                        test_present = list(test_students[:1])
                        test_attendance_records, session = mark_attendance_for_course(
                            test_course, date.today(), test_present, test_lecturer, "Health check test"
                        )
                        self.stdout.write(f'  ✅ Attendance System: Working (tested with {len(test_attendance_records)} records)')
                    else:
                        issues_found.append('No enrolled students for attendance testing')
                else:
                    issues_found.append('No courses assigned for attendance testing')
            else:
                issues_found.append('No lecturers available for attendance testing')
        except Exception as e:
            issues_found.append(f'Attendance system error: {e}')
        
        # 6. Check Data Integrity
        self.stdout.write('\n🔒 DATA INTEGRITY CHECK:')
        
        # Check for orphaned records
        orphaned_enrollments = StudentEnrollment.objects.filter(student__isnull=True)
        if orphaned_enrollments.exists():
            issues_found.append(f'{orphaned_enrollments.count()} orphaned enrollments')
            if fix_mode:
                orphaned_enrollments.delete()
                fixes_applied.append(f'Deleted {orphaned_enrollments.count()} orphaned enrollments')
        
        orphaned_attendance = Attendance.objects.filter(student__isnull=True)
        if orphaned_attendance.exists():
            issues_found.append(f'{orphaned_attendance.count()} orphaned attendance records')
            if fix_mode:
                orphaned_attendance.delete()
                fixes_applied.append(f'Deleted {orphaned_attendance.count()} orphaned attendance records')
        
        # 7. Performance Check
        self.stdout.write('\n⚡ PERFORMANCE CHECK:')
        
        # Check for large datasets that might need optimization
        if students.count() > 1000:
            self.stdout.write('  ⚠️  Large student dataset detected (>1000 students)')
        
        if attendance_records > 10000:
            self.stdout.write('  ⚠️  Large attendance dataset detected (>10000 records)')
        
        # 8. Summary
        self.stdout.write('\n📋 SUMMARY:')
        self.stdout.write('=' * 60)
        
        if not issues_found:
            self.stdout.write(self.style.SUCCESS('🎉 All systems are healthy! No issues found.'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Found {len(issues_found)} issues:'))
            for issue in issues_found:
                self.stdout.write(f'  - {issue}')
        
        if fixes_applied:
            self.stdout.write(self.style.SUCCESS(f'🔧 Applied {len(fixes_applied)} fixes:'))
            for fix in fixes_applied:
                self.stdout.write(f'  - {fix}')
        
        # System Statistics
        self.stdout.write('\n📊 SYSTEM STATISTICS:')
        self.stdout.write(f'  • Total Users: {total_users}')
        self.stdout.write(f'  • Students: {students.count()}')
        self.stdout.write(f'  • Lecturers: {lecturers.count()}')
        self.stdout.write(f'  • Courses: {courses}')
        self.stdout.write(f'  • Course Offerings: {course_offerings}')
        self.stdout.write(f'  • Student Enrollments: {enrollments}')
        self.stdout.write(f'  • Attendance Records: {attendance_records}')
        self.stdout.write(f'  • Attendance Sessions: {attendance_sessions}')
        
        # Recommendations
        if issues_found:
            self.stdout.write('\n💡 RECOMMENDATIONS:')
            self.stdout.write('  • Run with --fix flag to automatically resolve common issues')
            self.stdout.write('  • Review and address any remaining issues manually')
            self.stdout.write('  • Consider running regular health checks')
        
        self.stdout.write('\n✅ System health check completed!')
