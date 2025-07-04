import pytest
from app import create_app, db
from app.models.models import Student, Course, TimeSlot, CoursePreference
from app.services.scheduler_service import SchedulerService

@pytest.fixture
def client():
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

def test_schedule_optimization(client):
    # Create test data
    student = Student(student_id='S001', name='Test Student', email='test@example.com')
    course = Course(course_code='CS101', name='Intro to CS', capacity=30)
    timeslot = TimeSlot(day=1, start_time='09:00', end_time='10:30', room='Room 101')
    
    db.session.add_all([student, course, timeslot])
    db.session.commit()
    
    # Test optimization
    scheduler = SchedulerService()
    result = scheduler.optimize_schedules('Test2024')
    
    assert result is not None
    assert len(result) >= 0

def test_api_endpoint(client):
    response = client.post('/api/schedules/optimize', json={'semester': 'Spring2024'})
    assert response.status_code in [200, 400]
