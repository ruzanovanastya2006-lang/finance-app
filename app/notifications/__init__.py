from flask import Blueprint

notifications = Blueprint('notifications', __name__, url_prefix='/notifications')

from . import routes
