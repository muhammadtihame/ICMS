from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import TuitionFee, StudentTuitionFee
from accounts.models import User


class Command(BaseCommand):
    help = 'Set up initial tuition fee configuration and create records for existing students'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing tuition fee records',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up tuition fee system...')
        
        # Create semester fee configuration
        self.stdout.write('Creating semester fee configuration...')
        for semester in range(1, 9):
            due_date = timezone.now().date() + timedelta(days=30 * semester)
            tuition_fee, created = TuitionFee.objects.get_or_create(
                semester=semester,
                defaults={
                    'due_date': due_date,
                    'amount': 1000.00,  # Default amount
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(f'  ✓ Created Semester {semester} configuration')
            else:
                self.stdout.write(f'  - Semester {semester} configuration already exists')
        
        # Create tuition fee records for existing students
        students = User.objects.filter(is_student=True)
        self.stdout.write(f'Found {students.count()} existing students')
        
        for student in students:
            self.stdout.write(f'Processing student: {student.username}')
            
            for semester in range(1, 9):
                # Get the semester configuration
                try:
                    semester_config = TuitionFee.objects.get(semester=semester)
                except TuitionFee.DoesNotExist:
                    self.stdout.write(f'  ⚠ Semester {semester} configuration not found, skipping')
                    continue
                
                # Create or update student tuition fee record
                student_fee, created = StudentTuitionFee.objects.get_or_create(
                    student=student,
                    semester=semester,
                    defaults={
                        'due_date': semester_config.due_date,
                        'amount_paid': 0.00,
                        'is_paid': False,
                        'is_overdue': False
                    }
                )
                
                if created:
                    self.stdout.write(f'  ✓ Created Semester {semester} record')
                else:
                    if options['force']:
                        # Update existing record with new due date
                        student_fee.due_date = semester_config.due_date
                        student_fee.save()
                        self.stdout.write(f'  ↻ Updated Semester {semester} record')
                    else:
                        self.stdout.write(f'  - Semester {semester} record already exists')
        
        self.stdout.write(self.style.SUCCESS('Tuition fee system setup completed successfully!'))
        
        # Display summary
        total_fees = StudentTuitionFee.objects.count()
        total_students = User.objects.filter(is_student=True).count()
        total_semesters = TuitionFee.objects.count()
        
        self.stdout.write('\nSummary:')
        self.stdout.write(f'  - Total students: {total_students}')
        self.stdout.write(f'  - Total semesters configured: {total_semesters}')
        self.stdout.write(f'  - Total tuition fee records: {total_fees}')
        self.stdout.write(f'  - Expected records: {total_students * 8}')
        
        if total_fees == total_students * 8:
            self.stdout.write(self.style.SUCCESS('  ✓ All records created successfully'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ Some records may be missing'))
