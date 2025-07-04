from flask import Blueprint, jsonify, request
from app.services.scheduler_service import SchedulerService
from app.models.models import Schedule, Student, Course
from app import db

bp = Blueprint('schedules', __name__, url_prefix='/api/schedules')

@bp.route('/optimize', methods=['POST'])
def optimize_schedules():
    data = request.get_json()
    semester = data.get('semester', 'Spring2024')
    
    scheduler = SchedulerService()
    result = scheduler.optimize_schedules(semester)
    
    if result:
        metrics = scheduler.calculate_metrics(semester)
        return jsonify({
            'status': 'success',
            'schedules_created': len(result),
            'metrics': metrics
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Optimization failed'}), 400

@bp.route('/student/<int:student_id>', methods=['GET'])
def get_student_schedule(student_id):
    schedules = Schedule.query.filter_by(student_id=student_id).all()
    
    result = []
    for schedule in schedules:
        result.append({
            'course': schedule.course.name,
            'course_code': schedule.course.course_code,
            'day': schedule.timeslot.day,
            'start_time': str(schedule.timeslot.start_time),
            'end_time': str(schedule.timeslot.end_time),
            'room': schedule.timeslot.room
        })
    
    return jsonify(result), 200

@bp.route('/metrics/<semester>', methods=['GET'])
def get_metrics(semester):
    scheduler = SchedulerService()
    metrics = scheduler.calculate_metrics(semester)
    return jsonify(metrics), 200
