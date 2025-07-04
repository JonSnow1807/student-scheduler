from flask import Blueprint, jsonify
from app import db
from sqlalchemy import text

bp = Blueprint('health', __name__)

@bp.route('/health')
def health_check():
    return jsonify({'status': 'healthy'}), 200

@bp.route('/ready')
def readiness_check():
    try:
        # Check database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503
