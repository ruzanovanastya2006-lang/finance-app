from flask import jsonify
from flask_login import login_required, current_user
from ..models import Notification
from .service import mark_all_read, get_unread_count
from . import notifications


@notifications.route('/unread-count')
@login_required
def unread_count():
    return jsonify({'count': get_unread_count(current_user.id)})


@notifications.route('/mark-read', methods=['POST'])
@login_required
def mark_read():
    mark_all_read(current_user.id)
    return jsonify({'ok': True})


@notifications.route('/list')
@login_required
def list_notifications():
    items = (Notification.query
             .filter_by(user_id=current_user.id)
             .order_by(Notification.created_at.desc())
             .limit(50)
             .all())
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'threshold': n.threshold,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%d.%m.%Y %H:%M'),
    } for n in items])
