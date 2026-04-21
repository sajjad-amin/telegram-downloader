import os
from flask import Blueprint, request, jsonify, session
from dotenv import load_dotenv

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == os.getenv('WEB_USERNAME') and data.get('password') == os.getenv('WEB_PASSWORD'):
        session['user'] = data['username']
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@auth_bp.route('/me', methods=['GET'])
def me():
    if 'user' in session:
        return jsonify({"user": session['user']})
    return jsonify({"error": "Not logged in"}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"success": True})
