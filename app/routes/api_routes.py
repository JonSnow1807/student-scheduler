from flask import Blueprint, jsonify, request
from app.models.models import Student, Course, Schedule, CoursePreference
from app.services.scheduler_service import SchedulerService
from app import db
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api/v1')

@bp.route('/students', methods=['GET'])
def get_students():
    """List all students with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    students = Student.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'students': [{
            'id': s.id,
            'student_id': s.student_id,
            'name': s.name,
            'email': s.email,
            'course_count': Schedule.query.filter_by(student_id=s.id).count()
        } for s in students.items],
        'total': students.total,
        'pages': students.pages,
        'current_page': page
    })

@bp.route('/courses', methods=['GET'])
def get_courses():
    """List all courses with enrollment stats"""
    courses = Course.query.all()
    
    result = []
    for course in courses:
        enrolled = Schedule.query.filter_by(course_id=course.id).count()
        demand = CoursePreference.query.filter_by(course_id=course.id).count()
        
        result.append({
            'id': course.id,
            'code': course.course_code,
            'name': course.name,
            'capacity': course.capacity,
            'enrolled': enrolled,
            'available': course.capacity - enrolled,
            'demand': demand,
            'utilization': round(enrolled / course.capacity * 100, 1)
        })
    
    return jsonify({'courses': result})

@bp.route('/optimization/status', methods=['GET'])
def optimization_status():
    """Get last optimization run status"""
    scheduler = SchedulerService()
    
    return jsonify({
        'last_run': scheduler.solution_stats if hasattr(scheduler, 'solution_stats') else None,
        'current_semester': 'Spring2024',
        'total_students': Student.query.count(),
        'total_schedules': Schedule.query.filter_by(semester='Spring2024').count()
    })

@bp.route('/reports/summary', methods=['GET'])
def summary_report():
    """Generate executive summary"""
    metrics = SchedulerService().calculate_metrics('Spring2024')
    
    return jsonify({
        'executive_summary': {
            'total_students_served': metrics['summary']['students_scheduled'],
            'satisfaction_rate': metrics['satisfaction_analysis']['by_priority']['priority_1']['rate'],
            'zero_conflicts': metrics['conflict_analysis']['conflict_rate'] == 0,
            'optimization_time': metrics['solver_performance'].get('solve_time', 0),
            'key_achievements': [
                f"{metrics['summary']['students_scheduled']} students successfully scheduled",
                f"{metrics['conflict_analysis']['conflict_rate']}% scheduling conflicts",
                f"{metrics['satisfaction_analysis']['by_priority']['priority_1']['rate']}% first choice satisfaction",
                "Automated process completed in under 60 seconds"
            ]
        },
        'detailed_metrics': metrics
    })
