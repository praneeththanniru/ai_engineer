from flask import Blueprint, jsonify
from .models import Task

main_routes = Blueprint('main', __name__)

@main_routes.route('/')
def index():
    return jsonify({"message": "Antigravity Backend API is running!"})
