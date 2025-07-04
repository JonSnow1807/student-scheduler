from app import create_app, db
from app.models.models import Student, Course, TimeSlot, CoursePreference
from datetime import time
import random

def seed_database():
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create students
        students = []
        for i in range(500):
            student = Student(
                student_id=f'S{i:04d}',
                name=f'Student {i}',
                email=f'student{i}@university.edu'
            )
            students.append(student)
            db.session.add(student)
        
        # Create courses
        courses = []
        course_data = [
            ('CS101', 'Introduction to Computer Science'),
            ('CS201', 'Data Structures'),
            ('CS301', 'Algorithms'),
            ('MATH101', 'Calculus I'),
            ('MATH201', 'Linear Algebra'),
            ('PHY101', 'Physics I'),
            ('ENG101', 'English Composition'),
            ('HIST101', 'World History'),
            ('BIO101', 'Biology I'),
            ('CHEM101', 'Chemistry I')
        ]
        
        for code, name in course_data:
            course = Course(
                course_code=code,
                name=name,
                capacity=random.randint(30, 60),
                instructor=f'Dr. {code}'
            )
            courses.append(course)
            db.session.add(course)
        
        # Create time slots
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        time_ranges = [
            (time(8, 0), time(9, 30)),
            (time(10, 0), time(11, 30)),
            (time(13, 0), time(14, 30)),
            (time(15, 0), time(16, 30))
        ]
        
        for day_idx, day in enumerate(days):
            for start, end in time_ranges:
                for room in ['Room 101', 'Room 102', 'Room 201', 'Room 202']:
                    timeslot = TimeSlot(
                        day=day_idx,
                        start_time=start,
                        end_time=end,
                        room=room
                    )
                    db.session.add(timeslot)
        
        db.session.commit()
        
        # Create course preferences
        for student in students:
            # Each student selects 3-5 courses
            num_courses = random.randint(3, 5)
            selected_courses = random.sample(courses, num_courses)
            
            for idx, course in enumerate(selected_courses):
                pref = CoursePreference(
                    student_id=student.id,
                    course_id=course.id,
                    priority=idx + 1
                )
                db.session.add(pref)
        
        db.session.commit()
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
