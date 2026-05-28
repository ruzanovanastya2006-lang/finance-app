from flask import Blueprint

operations = Blueprint('operations', __name__, url_prefix='/operations')

from . import routes
