"""
API blueprint for AJAX operations
"""
from flask import Blueprint

bp = Blueprint('api', __name__)

from app.api import routes