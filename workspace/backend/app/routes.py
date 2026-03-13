from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

routes_bp = Blueprint("routes", __name__)

@routes_bp.route("/protected")
@jwt_required()
def protected():
    user = get_jwt_identity()
    return jsonify({"message": f"Welcome {user}!"})
