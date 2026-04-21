import os
import sys

# Production Networking Fix: Monkey patch BEFORE other imports
if sys.platform != 'darwin':
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        pass

# macOS asyncio compatibility
if sys.platform == 'darwin':
    import asyncio
    import selectors
    if hasattr(selectors, 'KqueueSelector'):
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

import json
from flask import Flask, session, jsonify, request, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
from dotenv import load_dotenv

# Shared resources
from backend.constants import STATIC_FOLDER
from backend.tasks import socketio, background_tasks

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret')
CORS(app, supports_credentials=True)

# SocketIO Init
async_mode = 'threading' if sys.platform == 'darwin' else 'eventlet'
socketio.init_app(app, 
    cors_allowed_origins="*", 
    async_mode=async_mode,
    ping_timeout=60,
    ping_interval=25
)

# Register Blueprints (Routes)
from backend.routes.auth import auth_bp
from backend.routes.profiles import profiles_bp
from backend.routes.downloads import downloads_bp, single_download_bp
from backend.routes.bulk import bulk_bp
from backend.routes.tasks import tasks_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(profiles_bp, url_prefix='/api/profiles')
app.register_blueprint(single_download_bp, url_prefix='/api/download') # /api/download/single & /api/download/<action>
app.register_blueprint(downloads_bp, url_prefix='/api/downloads')      # /api/downloads?path=...
app.register_blueprint(bulk_bp, url_prefix='/api/bulk')
app.register_blueprint(tasks_bp, url_prefix='/api/tasks')

# Global Middleware
@app.before_request
def check_auth():
    if not request.path.startswith('/api/'): return
    if request.path.startswith('/api/auth') or request.method == 'OPTIONS': return
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

# SPA Routing Fallback
@app.errorhandler(404)
def not_found(e):
    # If it's an API call, return actual 404
    if request.path.startswith('/api/'):
        return jsonify({"error": "Not Found"}), 404
    # Otherwise serve index.html for React Router
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
