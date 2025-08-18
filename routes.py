from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Admin
import jwt
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__)
SECRET_KEY = os.getenv("SECRET_KEY")


@auth_bp.route("/api/admin/register", methods=["POST"])
def register_admin():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Taarifa zote zinahitajika"}), 400

    existing = Admin.query.filter_by(username=username).first()
    if existing:
        return jsonify({"error": "Admin huyu tayari yupo"}), 400

    hashed = generate_password_hash(password)
    new_admin = Admin(username=username, password=hashed)
    db.session.add(new_admin)
    db.session.commit()

    return jsonify({"message": "Admin ameongezwa"}), 201


@auth_bp.route("/api/admin/login", methods=["POST"])
def login_admin():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    admin = Admin.query.filter_by(username=username).first()
    if not admin or not check_password_hash(admin.password, password):
        return jsonify({"error": "Taarifa sio sahihi"}), 401

    token = jwt.encode(
        {
            "id": admin.id,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        },
        SECRET_KEY,
        algorithm="HS256",
    )

    return jsonify({"token": token}), 200


@auth_bp.route('/api/admin/change-password', methods=['POST'])
def change_admin_password():
    data = request.json
    old = data.get('oldPassword')
    new = data.get('newPassword')

    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({'error': 'Unauthorized'}), 401

    admin = db.session.get(Admin, admin_id)
    if not admin or not check_password_hash(admin.password_hash, old):
        return jsonify({'error': 'Old password is incorrect'}), 400

    admin.password_hash = generate_password_hash(new)
    db.session.commit()
    return jsonify({'message': 'Password changed successfully'})
