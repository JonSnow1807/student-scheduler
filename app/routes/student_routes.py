from flask import Blueprint, jsonify, request
from app.models.models import Student, CoursePreference
from app import db

bp = Blueprint('students', __name__, url_prefix='/api/students')

@bp.route('/', methods=['POST'])
def create_student():
    data = request.get_json()
    
    student = Student(
        student_id=data['student_id'],
        name=data['name'],
        email=data['email']
    )
    
    db.session.add(student)
    db.session.commit()
    
    return jsonify({
        'id': student.id,
        'student_id': student.student_id,
        'name': student.name
    }), 201

@bp.route('/<int:student_id>/preferences', methods=['POST'])
def add_preferences(student_id):
    data = request.get_json()
    
    for pref in data['preferences']:
        preference = CoursePreference(
            student_id=student_id,
            course_id=pref['course_id'],
            priority=pref.get('priority', 1)
        )
        db.session.add(preference)
    
    db.session.commit()
    return jsonify({'status': 'success'}), 201
