from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib import messages
from .models import CourseOffering, Batch, StudentEnrollment
from course.models import Course, CourseAllocation
from accounts.models import User


@receiver(post_save, sender=User)
def auto_enroll_student_in_courses(sender, instance, created, **kwargs):
    """
    Automatically enroll students in course offerings when they're added to a batch.
    This ensures students appear in attendance lists for their assigned courses.
    """
    if created and instance.is_student and instance.batch:
        try:
            # Get all course offerings for this student's batch
            course_offerings = CourseOffering.objects.filter(batch=instance.batch)
            
            for offering in course_offerings:
                # Create enrollment if it doesn't exist
                StudentEnrollment.objects.get_or_create(
                    student=instance,
                    course_offering=offering,
                    defaults={'is_active': True}
                )
            
            print(f"Auto-enrolled {instance.get_full_name} in {course_offerings.count()} courses")
            
        except Exception as e:
            print(f"Error auto-enrolling student {instance.get_full_name}: {e}")


@receiver(post_save, sender=CourseOffering)
def auto_enroll_batch_students_in_new_course(sender, instance, created, **kwargs):
    """
    Automatically enroll all students from a batch in a new course offering.
    """
    if created:
        try:
            # Get all students in this batch
            batch_students = User.objects.filter(is_student=True, batch=instance.batch)
            
            for student in batch_students:
                # Create enrollment if it doesn't exist
                StudentEnrollment.objects.get_or_create(
                    student=student,
                    course_offering=instance,
                    defaults={'is_active': True}
                )
            
            print(f"Auto-enrolled {batch_students.count()} students in {instance.course.title}")
            
        except Exception as e:
            print(f"Error auto-enrolling batch students: {e}")


@receiver(post_save, sender=CourseAllocation)
def sync_course_allocation_to_offering(sender, instance, created, **kwargs):
    """
    Automatically create CourseOffering when a course is allocated to a lecturer.
    This ensures synchronization between the old and new systems.
    """
    try:
        # Get all courses for this allocation
        for course in instance.courses.all():
            # Check if a CourseOffering already exists for this combination
            existing_offering = CourseOffering.objects.filter(
                course=course,
                lecturer=instance.lecturer,
                program=course.program
            ).first()
            
            if not existing_offering:
                # Get or create a default batch for this program
                batch, batch_created = Batch.objects.get_or_create(
                    title=f"Default {course.program.title}",
                    program=course.program
                )
                
                # Create the CourseOffering
                CourseOffering.objects.create(
                    program=course.program,
                    course=course,
                    lecturer=instance.lecturer,
                    batch=batch,
                    lectures_per_week=3  # Default value
                )
                
                print(f"Created CourseOffering: {course.title} -> {instance.lecturer.get_full_name}")
            
    except Exception as e:
        print(f"Error syncing course allocation: {e}")


@receiver(post_delete, sender=CourseAllocation)
def remove_course_offering_on_deallocation(sender, instance, **kwargs):
    """
    Remove CourseOffering when a course is deallocated from a lecturer.
    """
    try:
        # Remove all CourseOfferings for this lecturer
        CourseOffering.objects.filter(lecturer=instance.lecturer).delete()
        
        print(f"Removed all CourseOfferings for: {instance.lecturer.get_full_name}")
        
    except Exception as e:
        print(f"Error removing course offerings: {e}")


@receiver(post_save, sender=CourseOffering)
def sync_offering_to_allocation(sender, instance, created, **kwargs):
    """
    Automatically create CourseAllocation when a CourseOffering is created.
    This ensures backward compatibility.
    """
    if created:
        try:
            # Check if CourseAllocation already exists for this lecturer
            existing_allocation = CourseAllocation.objects.filter(
                lecturer=instance.lecturer
            ).first()
            
            if existing_allocation:
                # Add course to existing allocation if not already there
                if instance.course not in existing_allocation.courses.all():
                    existing_allocation.courses.add(instance.course)
                    print(f"Added course to existing allocation: {instance.course.title} -> {instance.lecturer.get_full_name}")
            else:
                # Create new CourseAllocation
                allocation = CourseAllocation.objects.create(
                    lecturer=instance.lecturer
                )
                allocation.courses.add(instance.course)
                print(f"Created new CourseAllocation: {instance.course.title} -> {instance.lecturer.get_full_name}")
                
        except Exception as e:
            print(f"Error syncing offering to allocation: {e}")


@receiver(post_delete, sender=CourseOffering)
def remove_allocation_on_offering_delete(sender, instance, **kwargs):
    """
    Remove AllocatedCourse when a CourseOffering is deleted.
    """
    try:
        # Find and delete the corresponding CourseAllocation
        CourseAllocation.objects.filter(
            course=instance.course,
            lecturer=instance.lecturer
        ).delete()
        
        print(f"Removed CourseAllocation: {instance.course.title} -> {instance.lecturer.get_full_name}")
        
    except Exception as e:
        print(f"Error removing allocation: {e}")
