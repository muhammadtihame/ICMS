from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Batch
from accounts.models import User, Student


class Command(BaseCommand):
    help = 'Assign students to batches based on their program'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reassignment even if students already have batches',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting student batch assignment...')
        
        with transaction.atomic():
            # Get all students
            students = User.objects.filter(is_student=True).select_related('student')
            
            assigned_count = 0
            skipped_count = 0
            
            for student in students:
                try:
                    # Get student's program
                    if hasattr(student, 'student') and student.student.program:
                        program = student.student.program
                        
                        # Get or create batch for this program
                        batch, batch_created = Batch.objects.get_or_create(
                            title=f"Default {program.title}",
                            program=program
                        )
                        
                        if batch_created:
                            self.stdout.write(f'Created batch: {batch.title}')
                        
                        # Check if student already has a batch
                        if hasattr(student, 'batch') and student.batch and not options['force']:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Skipped: {student.get_full_name} (already in batch: {student.batch.title})'
                                )
                            )
                            skipped_count += 1
                            continue
                        
                        # Assign student to batch
                        student.batch = batch
                        student.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Assigned: {student.get_full_name} -> {batch.title}'
                            )
                        )
                        assigned_count += 1
                        
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Skipped: {student.get_full_name} (no program assigned)'
                            )
                        )
                        skipped_count += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error assigning {student.get_full_name}: {e}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nAssignment completed! Assigned: {assigned_count}, Skipped: {skipped_count}'
            )
        )
