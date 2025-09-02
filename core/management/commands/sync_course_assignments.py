from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import CourseOffering, Batch
from course.models import CourseAllocation
from accounts.models import User


class Command(BaseCommand):
    help = 'Sync existing course allocations to CourseOfferings for attendance system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if CourseOfferings already exist',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting course assignment synchronization...')
        
        with transaction.atomic():
            # Get all existing course allocations
            allocations = CourseAllocation.objects.select_related('lecturer', 'session').prefetch_related('courses', 'courses__program').all()
            
            created_count = 0
            skipped_count = 0
            
            for allocation in allocations:
                try:
                    # Get all courses for this allocation
                    for course in allocation.courses.all():
                        # Check if CourseOffering already exists
                        existing_offering = CourseOffering.objects.filter(
                            course=course,
                            lecturer=allocation.lecturer,
                            program=course.program
                        ).first()
                        
                        if existing_offering and not options['force']:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Skipped: {course.title} -> {allocation.lecturer.get_full_name} (already exists)'
                                )
                            )
                            skipped_count += 1
                            continue
                        
                        # Get or create a default batch for this program
                        batch, batch_created = Batch.objects.get_or_create(
                            title=f"Default {course.program.title}",
                            program=course.program
                        )
                        
                        if batch_created:
                            self.stdout.write(f'Created batch: {batch.title}')
                        
                        # Create the CourseOffering
                        offering, created = CourseOffering.objects.get_or_create(
                            course=course,
                            lecturer=allocation.lecturer,
                            program=course.program,
                            defaults={
                                'batch': batch,
                                'lectures_per_week': 3
                            }
                        )
                        
                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Created: {course.title} -> {allocation.lecturer.get_full_name}'
                                )
                            )
                            created_count += 1
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Updated: {course.title} -> {allocation.lecturer.get_full_name}'
                                )
                            )
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error syncing allocation for {allocation.lecturer.get_full_name}: {e}'
                        )
                    )
            
            # Also sync CourseOfferings back to AllocatedCourse for completeness
            offerings = CourseOffering.objects.select_related('course', 'lecturer').all()
            
                        for offering in offerings:
                try:
                    # Check if CourseAllocation already exists for this lecturer
                    allocation = CourseAllocation.objects.filter(
                        lecturer=offering.lecturer
                    ).first()
                    
                    if allocation:
                        # Add course to existing allocation if not already there
                        if offering.course not in allocation.courses.all():
                            allocation.courses.add(offering.course)
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Added course to existing CourseAllocation: {offering.course.title} -> {offering.lecturer.get_full_name}'
                                )
                            )
                    else:
                        # Create new CourseAllocation
                        allocation = CourseAllocation.objects.create(
                            lecturer=offering.lecturer
                        )
                        allocation.courses.add(offering.course)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Created new CourseAllocation: {offering.course.title} -> {offering.lecturer.get_full_name}'
                            )
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Error creating CourseAllocation for {offering.course.title} -> {offering.lecturer.get_full_name}: {e}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSync completed! Created: {created_count}, Skipped: {skipped_count}'
            )
        )
