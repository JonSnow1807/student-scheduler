from app import create_app, db
from app.models.models import Student, Course, Schedule
from app.services.scheduler_service import SchedulerService

app = create_app()
with app.app_context():
    # Clear previous schedules
    Schedule.query.delete()
    db.session.commit()
    
    # Get counts
    student_count = Student.query.count()
    course_count = Course.query.count()
    
    print(f"Testing with {student_count} students and {course_count} courses")
    
    # Try optimization
    scheduler = SchedulerService()
    
    # Test with first 50 students
    print("\nTesting with 50 students first...")
    
    # Temporarily limit students in the scheduler
    # (You'll need to modify the scheduler to accept a limit parameter)
    
    result = scheduler.optimize_schedules('TestRun')
    
    if result:
        print(f"Success! Created {len(result)} schedules")
    else:
        print("Failed - checking constraints...")
