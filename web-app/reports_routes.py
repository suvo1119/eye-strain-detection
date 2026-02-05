"""
Reports Routes for Eye Strain Monitoring App
Handles saving and retrieving user-specific eye strain reports
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func

from database import db, EyeStrainReport

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@reports_bp.route('', methods=['GET'])
@jwt_required()
def get_reports():
    """Get user's historical reports with pagination"""
    user_id = int(get_jwt_identity())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # Max 100 per page
    
    # Date filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = EyeStrainReport.query.filter_by(user_id=user_id)
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(EyeStrainReport.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(EyeStrainReport.created_at <= end)
        except ValueError:
            pass
    
    # Order by most recent first
    query = query.order_by(EyeStrainReport.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reports': [report.to_dict() for report in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }), 200


@reports_bp.route('/save', methods=['POST'])
@jwt_required()
def save_report():
    """Save a new eye strain report"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    report = EyeStrainReport(
        user_id=user_id,
        blinks_per_min=data.get('blinks_per_min', 0),
        perclos=data.get('perclos', 0),
        avg_ear=data.get('avg_ear', 0),
        avg_blink_duration_ms=data.get('avg_blink_duration_ms', 0),
        strain_level=data.get('strain_level', 'Unknown'),
        session_duration_seconds=data.get('session_duration_seconds', 0),
        total_blinks=data.get('total_blinks', 0)
    )
    
    db.session.add(report)
    db.session.commit()
    
    return jsonify({
        'message': 'Report saved successfully',
        'report': report.to_dict()
    }), 201


@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get dashboard summary with weekly/monthly stats"""
    user_id = int(get_jwt_identity())
    
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Weekly stats
    weekly_reports = EyeStrainReport.query.filter(
        EyeStrainReport.user_id == user_id,
        EyeStrainReport.created_at >= week_ago
    ).all()
    
    # Monthly stats
    monthly_reports = EyeStrainReport.query.filter(
        EyeStrainReport.user_id == user_id,
        EyeStrainReport.created_at >= month_ago
    ).all()
    
    # Calculate averages
    def calc_stats(reports):
        if not reports:
            return {
                'avg_blinks_per_min': 0,
                'avg_perclos': 0,
                'avg_strain_time': 0,
                'total_sessions': 0,
                'total_time_seconds': 0,
                'strain_distribution': {'Low': 0, 'Mild': 0, 'High': 0}
            }
        
        total = len(reports)
        return {
            'avg_blinks_per_min': round(sum(r.blinks_per_min for r in reports) / total, 2),
            'avg_perclos': round(sum(r.perclos for r in reports) / total, 2),
            'total_sessions': total,
            'total_time_seconds': sum(r.session_duration_seconds for r in reports),
            'strain_distribution': {
                'Low': sum(1 for r in reports if r.strain_level == 'Low'),
                'Mild': sum(1 for r in reports if r.strain_level == 'Mild'),
                'High': sum(1 for r in reports if r.strain_level == 'High')
            }
        }
    
    # Daily breakdown for charts (last 7 days)
    daily_data = []
    for i in range(7):
        day = now - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_reports = [r for r in weekly_reports 
                       if day_start <= r.created_at < day_end]
        
        if day_reports:
            avg_blinks = sum(r.blinks_per_min for r in day_reports) / len(day_reports)
            avg_perclos = sum(r.perclos for r in day_reports) / len(day_reports)
            total_time = sum(r.session_duration_seconds for r in day_reports)
        else:
            avg_blinks = 0
            avg_perclos = 0
            total_time = 0
        
        daily_data.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'day': day_start.strftime('%a'),
            'avg_blinks_per_min': round(avg_blinks, 2),
            'avg_perclos': round(avg_perclos, 2),
            'total_time_minutes': round(total_time / 60, 1),
            'sessions': len(day_reports)
        })
    
    return jsonify({
        'weekly': calc_stats(weekly_reports),
        'monthly': calc_stats(monthly_reports),
        'daily_data': daily_data,
        'last_updated': now.isoformat()
    }), 200


@reports_bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_sessions():
    """Get reports grouped by session with summary per session"""
    user_id = int(get_jwt_identity())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = min(per_page, 50)
    
    # Date filter
    date_filter = request.args.get('date')  # Format: YYYY-MM-DD
    
    # Get distinct session IDs for the user
    query = db.session.query(
        EyeStrainReport.session_id,
        func.min(EyeStrainReport.created_at).label('start_time'),
        func.max(EyeStrainReport.created_at).label('end_time'),
        func.avg(EyeStrainReport.blinks_per_min).label('avg_blinks'),
        func.avg(EyeStrainReport.perclos).label('avg_perclos'),
        func.avg(EyeStrainReport.avg_ear).label('avg_ear'),
        func.sum(EyeStrainReport.session_duration_seconds).label('total_duration'),
        func.max(EyeStrainReport.total_blinks).label('total_blinks'),
        func.count(EyeStrainReport.id).label('data_points')
    ).filter(
        EyeStrainReport.user_id == user_id,
        EyeStrainReport.session_id.isnot(None)
    ).group_by(EyeStrainReport.session_id)
    
    if date_filter:
        try:
            filter_date = datetime.fromisoformat(date_filter)
            day_start = filter_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            query = query.having(func.min(EyeStrainReport.created_at) >= day_start)
            query = query.having(func.min(EyeStrainReport.created_at) < day_end)
        except ValueError:
            pass
    
    query = query.order_by(func.max(EyeStrainReport.created_at).desc())
    
    # Get total count for pagination
    total_sessions = query.count()
    total_pages = (total_sessions + per_page - 1) // per_page
    
    # Apply pagination
    sessions = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Determine dominant strain level for each session
    sessions_data = []
    for session in sessions:
        # Get strain level distribution for this session
        strain_counts = db.session.query(
            EyeStrainReport.strain_level,
            func.count(EyeStrainReport.id)
        ).filter(
            EyeStrainReport.session_id == session.session_id
        ).group_by(EyeStrainReport.strain_level).all()
        
        strain_dist = {level: count for level, count in strain_counts}
        dominant_strain = max(strain_dist, key=strain_dist.get) if strain_dist else 'Unknown'
        
        sessions_data.append({
            'session_id': session.session_id,
            'start_time': session.start_time.isoformat() if session.start_time else None,
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'avg_blinks_per_min': round(session.avg_blinks or 0, 2),
            'avg_perclos': round(session.avg_perclos or 0, 2),
            'avg_ear': round(session.avg_ear or 0, 4),
            'total_duration_seconds': session.total_duration or 0,
            'total_blinks': session.total_blinks or 0,
            'data_points': session.data_points,
            'dominant_strain': dominant_strain,
            'strain_distribution': strain_dist
        })
    
    return jsonify({
        'sessions': sessions_data,
        'total': total_sessions,
        'pages': total_pages,
        'current_page': page,
        'per_page': per_page,
        'has_next': page < total_pages,
        'has_prev': page > 1
    }), 200


@reports_bp.route('/latest', methods=['GET'])
@jwt_required()
def get_latest_report():
    """Get the most recent report"""
    user_id = int(get_jwt_identity())
    
    report = EyeStrainReport.query.filter_by(user_id=user_id)\
        .order_by(EyeStrainReport.created_at.desc())\
        .first()
    
    if not report:
        return jsonify({'report': None}), 200
    
    return jsonify({'report': report.to_dict()}), 200


# Function to save report from monitoring (used by flask_api.py)
def save_eye_strain_data(user_id, metrics, session_id=None):
    """Save eye strain data from monitoring session"""
    report = EyeStrainReport(
        user_id=user_id,
        session_id=session_id,
        blinks_per_min=metrics.get('blinks_per_min', 0),
        perclos=metrics.get('perclos', 0),
        avg_ear=metrics.get('avg_ear', 0),
        avg_blink_duration_ms=metrics.get('avg_blink_duration_ms', 0),
        strain_level=metrics.get('strain_level', 'Unknown'),
        total_blinks=metrics.get('total_blinks', 0),
        session_duration_seconds=30  # Reports saved every 30 seconds
    )
    
    db.session.add(report)
    db.session.commit()
    return report
