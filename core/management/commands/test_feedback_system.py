from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Student
from core.models import StudentFeedback
from django.db.models import Avg, Count

User = get_user_model()


class Command(BaseCommand):
    help = 'Test the student feedback system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Student Feedback System...'))
        
        # Get all active lecturers
        lecturers = User.objects.filter(is_lecturer=True, is_active=True)
        students = Student.objects.all()
        
        self.stdout.write(f'Found {lecturers.count()} active lecturers')
        self.stdout.write(f'Found {students.count()} students')
        
        # Check existing feedback
        existing_feedback = StudentFeedback.objects.all()
        self.stdout.write(f'Existing feedback count: {existing_feedback.count()}')
        
        # Test feedback creation for each student-lecturer combination
        feedback_created = 0
        for student in students:
            for lecturer in lecturers:
                # Check if feedback already exists
                if not StudentFeedback.objects.filter(student=student, lecturer=lecturer).exists():
                    # Create sample feedback
                    rating = 4  # Sample rating
                    message = f"Sample feedback from {student.student.get_full_name} to {lecturer.get_full_name}"
                    
                    StudentFeedback.objects.create(
                        student=student,
                        lecturer=lecturer,
                        rating=rating,
                        message=message
                    )
                    feedback_created += 1
        
        self.stdout.write(f'Created {feedback_created} new feedback entries')
        
        # Test statistics
        total_feedback = StudentFeedback.objects.count()
        avg_rating = StudentFeedback.objects.aggregate(Avg('rating'))['rating__avg'] or 0
        
        self.stdout.write(f'Total feedback: {total_feedback}')
        self.stdout.write(f'Average rating: {avg_rating:.1f}/5')
        
        # Test lecturer-specific statistics
        for lecturer in lecturers:
            lecturer_feedback = StudentFeedback.objects.filter(lecturer=lecturer)
            if lecturer_feedback.exists():
                avg = lecturer_feedback.aggregate(Avg('rating'))['rating__avg']
                count = lecturer_feedback.count()
                self.stdout.write(f'{lecturer.get_full_name}: {avg:.1f}/5 ({count} feedback)')
        
        # Test student feedback completion
        for student in students:
            student_feedback = StudentFeedback.objects.filter(student=student)
            lecturers_without_feedback = lecturers.exclude(
                id__in=student_feedback.values_list('lecturer_id', flat=True)
            )
            
            if lecturers_without_feedback.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'{student.student.get_full_name} still needs to provide feedback for {lecturers_without_feedback.count()} lecturers'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{student.student.get_full_name} has provided feedback for all lecturers'
                    )
                )
        
        self.stdout.write(self.style.SUCCESS('Feedback system test completed!'))
