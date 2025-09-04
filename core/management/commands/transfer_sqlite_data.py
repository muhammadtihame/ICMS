from django.core.management.base import BaseCommand
import sqlite3
from django.contrib.auth import get_user_model
from core.models import Lecturer, Feedback, TuitionFee, StudentTuitionFee

User = get_user_model()

class Command(BaseCommand):
    help = 'Transfer data from SQLite to PostgreSQL'

    def handle(self, *args, **options):
        self.stdout.write('Starting data transfer from SQLite to PostgreSQL...')
        
        try:
            # Connect to SQLite
            sqlite_conn = sqlite3.connect('db.sqlite3.backup')
            sqlite_cursor = sqlite_conn.cursor()
            
            # Transfer Users
            self.transfer_users(sqlite_cursor)
            
            # Transfer other models
            self.transfer_lecturers(sqlite_cursor)
            self.transfer_feedback(sqlite_cursor)
            self.transfer_tuition_fees(sqlite_cursor)
            
            sqlite_conn.close()
            self.stdout.write(self.style.SUCCESS('Data transfer completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during data transfer: {str(e)}'))
    
    def transfer_users(self, cursor):
        self.stdout.write('Transferring users...')
        try:
            cursor.execute("SELECT * FROM accounts_user")
            users = cursor.fetchall()
            
            for user_data in users:
                try:
                    # Handle date fields properly
                    date_joined = None
                    if user_data[7]:  # date_joined field
                        try:
                            if isinstance(user_data[7], str):
                                from datetime import datetime
                                date_joined = datetime.fromisoformat(user_data[7].replace('Z', '+00:00'))
                            else:
                                date_joined = user_data[7]
                        except:
                            date_joined = None
                    
                    # Create user if doesn't exist
                    user, created = User.objects.get_or_create(
                        username=user_data[1],  # username field
                        defaults={
                            'email': user_data[2] or '',  # email field
                            'first_name': user_data[3] or '',  # first_name field
                            'last_name': user_data[4] or '',  # last_name field
                            'is_staff': bool(user_data[5]),  # is_staff field
                            'is_active': bool(user_data[6]),  # is_active field
                            'date_joined': date_joined or '2025-01-01',  # date_joined field with fallback
                        }
                    )
                    if created:
                        self.stdout.write(f'Created user: {user.username}')
                except Exception as e:
                    self.stdout.write(f'Error creating user: {str(e)}')
        except Exception as e:
            self.stdout.write(f'Error accessing users table: {str(e)}')
    
    def transfer_lecturers(self, cursor):
        self.stdout.write('Transferring lecturers...')
        try:
            cursor.execute("SELECT * FROM core_lecturer")
            lecturers = cursor.fetchall()
            
            for lecturer_data in lecturers:
                try:
                    lecturer, created = Lecturer.objects.get_or_create(
                        name=lecturer_data[1],  # name field
                        defaults={
                            'subject': lecturer_data[2] or '',  # subject field
                        }
                    )
                    if created:
                        self.stdout.write(f'Created lecturer: {lecturer.name}')
                except Exception as e:
                    self.stdout.write(f'Error creating lecturer: {str(e)}')
        except Exception as e:
            self.stdout.write(f'No lecturers table found or error: {str(e)}')
    
    def transfer_feedback(self, cursor):
        self.stdout.write('Transferring feedback...')
        try:
            cursor.execute("SELECT * FROM core_feedback")
            feedbacks = cursor.fetchall()
            
            for feedback_data in feedbacks:
                try:
                    # Get student and lecturer
                    student = User.objects.filter(username=feedback_data[1]).first()
                    lecturer = Lecturer.objects.filter(name=feedback_data[2]).first()
                    
                    if student and lecturer:
                        feedback, created = Feedback.objects.get_or_create(
                            student=student,
                            lecturer=lecturer,
                            defaults={
                                'teacher_rating': feedback_data[3],  # teacher_rating field
                                'comments': feedback_data[4] or '',  # comments field
                                'submitted_at': feedback_data[5],  # submitted_at field
                            }
                        )
                        if created:
                            self.stdout.write(f'Created feedback for {student.username} -> {lecturer.name}')
                except Exception as e:
                    self.stdout.write(f'Error creating feedback: {str(e)}')
        except Exception as e:
            self.stdout.write(f'No feedback table found or error: {str(e)}')
    
    def transfer_tuition_fees(self, cursor):
        self.stdout.write('Transferring tuition fees...')
        try:
            # Create default tuition fee structure for 8 semesters
            for semester in range(1, 9):
                tuition_fee, created = TuitionFee.objects.get_or_create(
                    semester=semester,
                    defaults={
                        'due_date': '2025-12-31',  # Default due date
                        'amount': 1000.00,  # Default amount
                        'is_active': True,
                    }
                )
                if created:
                    self.stdout.write(f'Created tuition fee for semester {semester}')
            
            # Create student tuition fee records for existing students
            students = User.objects.filter(is_staff=False, is_superuser=False)
            for student in students:
                for semester in range(1, 9):
                    student_fee, created = StudentTuitionFee.objects.get_or_create(
                        student=student,
                        semester=semester,
                        defaults={
                            'amount_paid': 0.00,
                            'due_date': '2025-12-31',
                            'is_paid': False,
                            'is_overdue': False,
                        }
                    )
                    if created:
                        self.stdout.write(f'Created tuition fee record for {student.username} semester {semester}')
                        
        except Exception as e:
            self.stdout.write(f'Error creating tuition fees: {str(e)}')
