from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from course.models import Course, CourseAllocation, Program
from core.models import Session, CourseOffering, Batch, StudentEnrollment

User = get_user_model()


@receiver(post_save, sender=User)
def auto_assign_courses_to_lecturer(sender, instance, created, **kwargs):
    """
    Automatically assign courses to new lecturers or lecturers without courses.
    This ensures lecturers appear in attendance management immediately.
    """
    if instance.is_lecturer and created:
        try:
            # Get available courses that don't have lecturers assigned
            available_courses = CourseOffering.objects.filter(lecturer__isnull=True)
            
            if available_courses.exists():
                # Assign up to 2 courses to the new lecturer
                courses_to_assign = available_courses[:2]
                for course in courses_to_assign:
                    course.lecturer = instance
                    course.save()
                    print(f"Auto-assigned {course.course.title} to {instance.get_full_name}")
            
            # Also create CourseAllocation records for backward compatibility
            from course.models import CourseAllocation
            existing_allocations = CourseAllocation.objects.filter(lecturer=instance)
            if not existing_allocations.exists():
                # Create allocations for the assigned courses
                for course_offering in CourseOffering.objects.filter(lecturer=instance):
                    CourseAllocation.objects.get_or_create(
                        lecturer=instance,
                        course=course_offering.course,
                        session=course_offering.session,
                        defaults={'is_active': True}
                    )
                    print(f"Created CourseAllocation for {course_offering.course.title}")
                    
        except Exception as e:
            print(f"Error auto-assigning courses to lecturer {instance.get_full_name}: {e}")


@receiver(post_save, sender=User)
def update_lecturer_course_assignments(sender, instance, created, **kwargs):
    """
    Update course assignments for existing lecturers who have no courses.
    """
    if instance.is_lecturer and not created:
        try:
            # Check if lecturer has any courses
            has_course_offerings = CourseOffering.objects.filter(lecturer=instance).exists()
            has_course_allocations = CourseAllocation.objects.filter(lecturer=instance).exists()
            
            if not has_course_offerings and not has_course_allocations:
                # Assign courses to lecturer without any courses
                available_courses = CourseOffering.objects.filter(lecturer__isnull=True)
                
                if available_courses.exists():
                    courses_to_assign = available_courses[:2]
                    for course in courses_to_assign:
                        course.lecturer = instance
                        course.save()
                        print(f"Auto-assigned {course.course.title} to existing lecturer {instance.get_full_name}")
                        
        except Exception as e:
            print(f"Error updating course assignments for lecturer {instance.get_full_name}: {e}")


@receiver(post_save, sender=User)
def auto_enroll_student_in_courses(sender, instance, created, **kwargs):
    """
    Automatically enroll students in course offerings when they're added to a batch.
    This ensures students appear in attendance lists for their assigned courses.
    """
    if created and instance.is_student and instance.batch:
        try:
            # Get all course offerings for this batch
            course_offerings = CourseOffering.objects.filter(batch=instance.batch)
            
            for offering in course_offerings:
                StudentEnrollment.objects.get_or_create(
                    student=instance,
                    course_offering=offering,
                    defaults={'is_active': True}
                )
            print(f"Auto-enrolled {instance.get_full_name} in {course_offerings.count()} courses")
            
        except Exception as e:
            print(f"Error auto-enrolling student {instance.get_full_name}: {e}")


@receiver(post_save, sender=User)
def auto_enroll_existing_student_in_new_courses(sender, instance, created, **kwargs):
    """
    Auto-enroll existing students in new courses when their batch gets new course offerings.
    """
    if not created and instance.is_student and instance.batch:
        try:
            # Get all course offerings for this batch
            course_offerings = CourseOffering.objects.filter(batch=instance.batch)
            
            # Get existing enrollments
            existing_enrollments = StudentEnrollment.objects.filter(
                student=instance,
                course_offering__in=course_offerings
            )
            
            # Enroll in courses that don't have enrollments yet
            for offering in course_offerings:
                if not existing_enrollments.filter(course_offering=offering).exists():
                    StudentEnrollment.objects.get_or_create(
                        student=instance,
                        course_offering=offering,
                        defaults={'is_active': True}
                    )
                    print(f"Auto-enrolled existing student {instance.get_full_name} in {offering.course.title}")
                    
        except Exception as e:
            print(f"Error auto-enrolling existing student {instance.get_full_name}: {e}")


@receiver(post_save, sender=CourseOffering)
def auto_enroll_batch_students_in_new_course(sender, instance, created, **kwargs):
    """
    Automatically enroll all students from a batch in a new course offering.
    This ensures when a new course is added to a batch, all students are automatically enrolled.
    """
    if created and instance.batch:
        try:
            batch_students = User.objects.filter(is_student=True, batch=instance.batch)
            
            for student in batch_students:
                StudentEnrollment.objects.get_or_create(
                    student=student,
                    course_offering=instance,
                    defaults={'is_active': True}
                )
            print(f"Auto-enrolled {batch_students.count()} students in {instance.course.title}")
            
        except Exception as e:
            print(f"Error auto-enrolling batch students: {e}")


@receiver(post_save, sender=CourseOffering)
def sync_course_offerings_on_allocation_change(sender, instance, created, **kwargs):
    """
    Sync CourseOfferings when CourseAllocation changes.
    This ensures both systems stay in sync.
    """
    if created:
        try:
            # Create corresponding CourseAllocation if it doesn't exist
            from course.models import CourseAllocation
            CourseAllocation.objects.get_or_create(
                lecturer=instance.lecturer,
                course=instance.course,
                session=instance.session,
                defaults={'is_active': True}
            )
            print(f"Created CourseAllocation for {instance.course.title}")
            
        except Exception as e:
            print(f"Error syncing CourseAllocation: {e}")


@receiver(post_save, sender=CourseAllocation)
def sync_course_allocations_on_offering_change(sender, instance, created, **kwargs):
    """
    Sync CourseOfferings when CourseAllocation changes.
    This ensures both systems stay in sync.
    """
    if created:
        try:
            # Create corresponding CourseOffering if it doesn't exist
            CourseOffering.objects.get_or_create(
                lecturer=instance.lecturer,
                course=instance.course,
                session=instance.session,
                defaults={'is_active': True}
            )
            print(f"Created CourseOffering for {instance.course.title}")
            
        except Exception as e:
            print(f"Error syncing CourseOffering: {e}")


@receiver(post_save, sender=User)
def create_student_parent_profiles(sender, instance, created, **kwargs):
    """
    Automatically create student and parent profiles when a new user is created.
    """
    if created:
        try:
            if instance.is_student:
                from accounts.models import Student
                Student.objects.get_or_create(
                    user=instance,
                    defaults={
                        'level': instance.level,
                        'program': instance.program,
                        'semester': instance.semester,
                        'batch': instance.batch,
                    }
                )
                print(f"Created student profile for {instance.get_full_name}")
                
            elif instance.is_parent:
                from accounts.models import Parent
                Parent.objects.get_or_create(
                    user=instance,
                    defaults={
                        'phone': instance.phone,
                        'address': instance.address,
                    }
                )
                print(f"Created parent profile for {instance.get_full_name}")
                
        except Exception as e:
            print(f"Error creating profile for {instance.get_full_name}: {e}")


@receiver(post_delete, sender=User)
def cleanup_related_data(sender, instance, **kwargs):
    """
    Clean up related data when a user is deleted.
    """
    try:
        if instance.is_student:
            # Remove student enrollments
            StudentEnrollment.objects.filter(student=instance).delete()
            print(f"Cleaned up enrollments for {instance.get_full_name}")
            
        elif instance.is_lecturer:
            # Unassign courses from lecturer
            CourseOffering.objects.filter(lecturer=instance).update(lecturer=None)
            CourseAllocation.objects.filter(lecturer=instance).delete()
            print(f"Cleaned up course assignments for {instance.get_full_name}")
            
    except Exception as e:
        print(f"Error cleaning up data for {instance.get_full_name}: {e}")


@receiver(post_save, sender=Batch)
def auto_enroll_batch_students_in_existing_courses(sender, instance, created, **kwargs):
    """
    When a new batch is created, enroll all existing students in that batch
    in any existing course offerings for that batch.
    """
    if created:
        try:
            # Get all students in this batch
            batch_students = User.objects.filter(is_student=True, batch=instance)
            
            # Get all course offerings for this batch
            course_offerings = CourseOffering.objects.filter(batch=instance)
            
            # Enroll each student in each course offering
            for student in batch_students:
                for offering in course_offerings:
                    StudentEnrollment.objects.get_or_create(
                        student=student,
                        course_offering=offering,
                        defaults={'is_active': True}
                    )
            
            if batch_students.exists() and course_offerings.exists():
                print(f"Auto-enrolled {batch_students.count()} students in {course_offerings.count()} courses for batch {instance.title}")
                
        except Exception as e:
            print(f"Error auto-enrolling batch students in existing courses: {e}")


@receiver(post_save, sender=User)
def auto_assign_batch_to_student(sender, instance, created, **kwargs):
    """
    When a student is created or updated, ensure they are enrolled in all courses
    for their batch, even if the batch was assigned later.
    """
    if instance.is_student and instance.batch:
        try:
            # Get all course offerings for this batch
            course_offerings = CourseOffering.objects.filter(batch=instance.batch)
            
            # Enroll student in all course offerings for their batch
            for offering in course_offerings:
                StudentEnrollment.objects.get_or_create(
                    student=instance,
                    course_offering=offering,
                    defaults={'is_active': True}
                )
            
            if course_offerings.exists():
                print(f"Ensured {instance.get_full_name} is enrolled in {course_offerings.count()} courses for batch {instance.batch.title}")
                
        except Exception as e:
            print(f"Error ensuring student enrollment: {e}")
