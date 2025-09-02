from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import CourseOffering, StudentEnrollment, Batch, Session
from course.models import CourseAllocation
from accounts.models import Student, Parent

User = get_user_model()


class Command(BaseCommand):
    help = 'Set up the attendance management system for all existing data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of all enrollments',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting attendance system setup...'))
        
        force = options['force']
        
        # 1. Create student profiles for existing students
        self.stdout.write('Creating student profiles...')
        students_created = 0
        for user in User.objects.filter(is_student=True):
            student, created = Student.objects.get_or_create(
                student=user,
                defaults={
                    'level': getattr(user, 'level', None),
                    'program': getattr(user, 'program', None),
                    'semester': getattr(user, 'semester', None),
                }
            )
            if created:
                students_created += 1
        
        self.stdout.write(f'Created {students_created} student profiles')
        
        # 2. Create parent profiles for existing parents
        self.stdout.write('Creating parent profiles...')
        parents_created = 0
        for user in User.objects.filter(is_parent=True):
            parent, created = Parent.objects.get_or_create(
                user=user,
                defaults={
                    'phone': getattr(user, 'phone', ''),
                    'address': getattr(user, 'address', ''),
                }
            )
            if created:
                parents_created += 1
        
        self.stdout.write(f'Created {parents_created} parent profiles')
        
        # 3. Auto-assign courses to lecturers without courses
        self.stdout.write('Auto-assigning courses to lecturers...')
        lecturers_updated = 0
        for user in User.objects.filter(is_lecturer=True):
            has_course_offerings = CourseOffering.objects.filter(lecturer=user).exists()
            has_course_allocations = CourseAllocation.objects.filter(lecturer=user).exists()
            
            if not has_course_offerings and not has_course_allocations:
                # Assign available courses
                available_courses = CourseOffering.objects.filter(lecturer__isnull=True)
                if available_courses.exists():
                    courses_to_assign = available_courses[:2]
                    for course in courses_to_assign:
                        course.lecturer = user
                        course.save()
                    
                    # Create CourseAllocation records
                    for course_offering in CourseOffering.objects.filter(lecturer=user):
                        CourseAllocation.objects.get_or_create(
                            lecturer=user,
                            course=course_offering.course,
                            session=course_offering.session,
                            defaults={'is_active': True}
                        )
                    
                    lecturers_updated += 1
                    self.stdout.write(f'  - Assigned courses to {user.get_full_name}')
        
        self.stdout.write(f'Updated {lecturers_updated} lecturers')
        
        # 4. Enroll all students in their batch courses
        self.stdout.write('Enrolling students in batch courses...')
        enrollments_created = 0
        
        if force:
            # Remove all existing enrollments
            StudentEnrollment.objects.all().delete()
            self.stdout.write('  - Removed all existing enrollments')
        
        for user in User.objects.filter(is_student=True, batch__isnull=False):
            course_offerings = CourseOffering.objects.filter(batch=user.batch)
            
            for offering in course_offerings:
                enrollment, created = StudentEnrollment.objects.get_or_create(
                    student=user,
                    course_offering=offering,
                    defaults={'is_active': True}
                )
                if created:
                    enrollments_created += 1
        
        self.stdout.write(f'Created {enrollments_created} student enrollments')
        
        # 5. Sync CourseAllocation and CourseOffering systems
        self.stdout.write('Syncing course allocation systems...')
        sync_count = 0
        
        # Create CourseOfferings for CourseAllocations that don't have them
        for allocation in CourseAllocation.objects.all():
            for course in allocation.courses.all():
                # Get or create a batch for this course
                batch = Batch.objects.filter(program=course.program).first()
                if not batch:
                    batch = Batch.objects.first()  # Fallback to any batch
                
                if batch:
                    offering, created = CourseOffering.objects.get_or_create(
                        lecturer=allocation.lecturer,
                        course=course,
                        batch=batch,
                        defaults={
                            'program': course.program,
                            'lectures_per_week': 3
                        }
                    )
                    if created:
                        sync_count += 1
        
        # Create CourseAllocations for CourseOfferings that don't have them
        for offering in CourseOffering.objects.all():
            # Get or create session
            session = Session.objects.filter(is_current_session=True).first()
            if not session:
                session = Session.objects.first()
            
            if session:
                allocation, created = CourseAllocation.objects.get_or_create(
                    lecturer=offering.lecturer,
                    session=session,
                    defaults={'is_active': True}
                )
                if created:
                    sync_count += 1
                
                # Add course to allocation if not already there
                if offering.course not in allocation.courses.all():
                    allocation.courses.add(offering.course)
                    sync_count += 1
        
        self.stdout.write(f'Synced {sync_count} course allocations')
        
        # 6. Generate summary statistics
        self.stdout.write('\n' + '='*50)
        self.stdout.write('ATTENDANCE SYSTEM SETUP SUMMARY')
        self.stdout.write('='*50)
        
        total_students = User.objects.filter(is_student=True).count()
        total_lecturers = User.objects.filter(is_lecturer=True).count()
        total_courses = CourseOffering.objects.count()
        total_enrollments = StudentEnrollment.objects.count()
        total_batches = Batch.objects.count()
        
        self.stdout.write(f'Total Students: {total_students}')
        self.stdout.write(f'Total Lecturers: {total_lecturers}')
        self.stdout.write(f'Total Course Offerings: {total_courses}')
        self.stdout.write(f'Total Student Enrollments: {total_enrollments}')
        self.stdout.write(f'Total Batches: {total_batches}')
        
        # Check for any issues
        students_without_batch = User.objects.filter(is_student=True, batch__isnull=True).count()
        courses_without_lecturer = CourseOffering.objects.filter(lecturer__isnull=True).count()
        batches_without_courses = Batch.objects.filter(courseoffering__isnull=True).count()
        
        if students_without_batch > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  {students_without_batch} students without batch assignment'))
        
        if courses_without_lecturer > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  {courses_without_lecturer} courses without lecturer assignment'))
        
        if batches_without_courses > 0:
            self.stdout.write(self.style.WARNING(f'⚠️  {batches_without_courses} batches without course offerings'))
        
        if students_without_batch == 0 and courses_without_lecturer == 0 and batches_without_courses == 0:
            self.stdout.write(self.style.SUCCESS('✅ All systems are properly configured!'))
        
        self.stdout.write(self.style.SUCCESS('\nAttendance system setup completed successfully!'))
        self.stdout.write('The system is now ready for automatic attendance management.')
