import os
import sys

# Production Networking Fix: Monkey patch BEFORE other imports
if sys.platform != 'darwin':
    try:
        import eventlet
        eventlet.monkey_patch()
    except ImportError:
        pass

import asyncio
import threading

# macOS asyncio/eventlet compatibility fix
if sys.platform == 'darwin':
    import selectors
    # Force SelectSelector as KqueueSelector conflicts with eventlet on macOS
    if hasattr(selectors, 'KqueueSelector'):
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

# Create the background loop EARLY
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop) # Set as default loop for the main thread

def run_asyncio_loop(loop):
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except Exception as e:
        print(f"Asyncio loop error: {e}")

threading.Thread(target=run_asyncio_loop, args=(loop,), daemon=True).start()

# Global store for pending logins (mirrors GUI/CLI state management)
login_sessions = {}

import time
import json
import shutil
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv

# Import existing core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from core.telegram_client import TelegramDownloader
from core.database import Database
from core.utils import parse_telegram_link, parse_channel_entity

# Load environment variables from root
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Static folder configuration
STATIC_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dist'))
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret')
CORS(app, supports_credentials=True)
# Use 'threading' on macOS for better stability with asyncio/Telethon
async_mode = 'threading' if sys.platform == 'darwin' else 'eventlet'
socketio = SocketIO(app, 
    cors_allowed_origins="*", 
    async_mode=async_mode,
    ping_timeout=60,
    ping_interval=25,
    engineio_logger=False # Set to True if still having issues
)

# Global Constants
HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".telegram_video_downloader")
DOWNLOAD_BASE = os.getenv('DOWNLOAD_PATH', './downloads')
if not os.path.isabs(DOWNLOAD_BASE):
    DOWNLOAD_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../', DOWNLOAD_BASE))

if not os.path.exists(DOWNLOAD_BASE):
    os.makedirs(DOWNLOAD_BASE)

# State Management
active_profiles = {} # {profile_name: TelegramDownloader}
background_tasks = {} # {task_id: {"status": "running/paused/done", "progress": 0, "text": "", "pause_event": threading.Event(), "cancel_event": threading.Event()}}

def get_profile_paths(name):
    cd = os.path.join(CONFIG_DIR, name) if name and name != "Default" else CONFIG_DIR
    return cd, os.path.join(cd, "settings.ini"), os.path.join(cd, "my_account"), os.path.join(cd, "downloads.db")

async def get_downloader(profile_name):
    if profile_name in active_profiles:
        return active_profiles[profile_name]
    
    cd, settings_file, session_file, db_file = get_profile_paths(profile_name)
    
    # Read settings
    import configparser
    config = configparser.ConfigParser()
    if os.path.exists(settings_file):
        config.read(settings_file)
    
    api_id = config.get('General', 'API_ID', fallback=None)
    api_hash = config.get('General', 'API_HASH', fallback=None)
    
    if not api_id or not api_hash:
        # Check root
        root_settings = os.path.join(CONFIG_DIR, "settings.ini")
        if os.path.exists(root_settings):
            config.read(root_settings)
            api_id = config.get('General', 'API_ID', fallback=None)
            api_hash = config.get('General', 'API_HASH', fallback=None)

    if not api_id or not api_hash:
        print(f"DEBUG: Profile {profile_name} is missing API_ID or API_HASH")
        return None
        
    print(f"DEBUG: Initializing TelegramClient for {profile_name} using session {session_file}")
    downloader = TelegramDownloader(session_file, api_id, api_hash, loop=loop)
    await downloader.connect()
    active_profiles[profile_name] = downloader
    return downloader

# Middleware for auth
@app.before_request
def check_auth():
    # Only protect API routes, allow static files and root to pass
    if not request.path.startswith('/api/'):
        return
    # Skip auth for authentication endpoints
    if request.path.startswith('/api/auth') or request.method == 'OPTIONS':
        return
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == os.getenv('WEB_USERNAME') and data.get('password') == os.getenv('WEB_PASSWORD'):
        session['user'] = data['username']
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/api/auth/me', methods=['GET'])
def me():
    if 'user' in session:
        return jsonify({"user": session['user']})
    return jsonify({"error": "Not logged in"}), 401

@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    if not os.path.exists(CONFIG_DIR): return jsonify([])
    profiles = sorted([d for d in os.listdir(CONFIG_DIR) 
                  if os.path.isdir(os.path.join(CONFIG_DIR, d)) and d.isdigit()])
    return jsonify(profiles)

@app.route('/api/profiles/<phone>', methods=['DELETE'])
def delete_profile(phone):
    profile_dir = os.path.join(CONFIG_DIR, phone)
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
        return jsonify({"success": True})
    return jsonify({"error": "Profile not found"}), 404

@app.route('/api/profiles/login/start', methods=['POST'])
def login_start():
    data = request.json
    phone = data.get('phone', '').strip().replace(' ', '').replace('-', '').replace('+', '')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    
    if not phone: return jsonify({"error": "Phone required"}), 400
    
    # Priority: 1. UI Input, 2. Env Var
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    final_id = api_id or os.getenv('API_ID')
    final_hash = api_hash or os.getenv('API_HASH')
    
    if not final_id or not final_hash:
        return jsonify({"error": "API credentials missing. Please enter your API ID and Hash."}), 400

    # Persist NEW credentials to .env if provided
    if api_id and api_hash:
        env_path = os.path.join(os.path.dirname(__file__), '../.env')
        try:
            with open(env_path, 'r') as f: lines = f.readlines()
            with open(env_path, 'w') as f:
                f_id = f_hash = False
                for line in lines:
                    if line.startswith('API_ID='):
                        f.write(f'API_ID={api_id}\n'); f_id = True
                    elif line.startswith('API_HASH='):
                        f.write(f'API_HASH={api_hash}\n'); f_hash = True
                    else: f.write(line)
                if not f_id: f.write(f'API_ID={api_id}\n')
                if not f_hash: f.write(f'API_HASH={api_hash}\n')
        except: pass

    # Client Factory
    session_dir = os.path.join(CONFIG_DIR, phone)
    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, 'my_account')

    try:
        async def factory():
            c = TelegramDownloader(session_path, final_id, final_hash, loop=loop)
            await c.connect()
            res = await c.send_code(phone)
            return c, res.phone_code_hash

        future = asyncio.run_coroutine_threadsafe(factory(), loop)
        client, ph_hash = future.result(timeout=25)
        
        login_sessions[phone] = {"client": client, "phone_code_hash": ph_hash}
        return jsonify({"success": True, "phone": phone})
    except Exception as e:
        print(f"Login Start Error: {e}")
        return jsonify({"error": f"Login Error: {str(e)}"}), 400

@app.route('/api/profiles/login/verify', methods=['POST'])
def login_verify():
    data = request.json
    phone = data.get('phone', '').strip().replace('+', '')
    code = data.get('code')
    password = data.get('password')
    
    session_data = login_sessions.get(phone)
    if not session_data: return jsonify({"error": "Session expired or invalid. Please restart login."}), 400
    
    client = session_data['client']
    
    try:
        async def process():
            try:
                await client.sign_in(phone, code)
            except Exception as e:
                if "SessionPasswordNeededError" in str(e) or "two-step" in str(e).lower():
                    if not password: return "NEED_PASS"
                    await client.client.sign_in(password=password)
                else: raise e
            
            # Sync session to disk and disconnect
            await client.disconnect()
            return "SUCCESS"

        future = asyncio.run_coroutine_threadsafe(process(), loop)
        res = future.result(timeout=30)
        
        if res == "NEED_PASS":
            return jsonify({"status": "need_password"})
        
        if phone in login_sessions: del login_sessions[phone]
        return jsonify({"success": True})
    except Exception as e:
        print(f"Login Verify Error: {e}")
        return jsonify({"error": f"Verification Error: {str(e)}"}), 400

def get_safe_path(rel_path):
    if not rel_path: return DOWNLOAD_BASE
    safe_path = os.path.abspath(os.path.join(DOWNLOAD_BASE, rel_path))
    if not safe_path.startswith(DOWNLOAD_BASE):
        raise ValueError("Directory traversal attempt")
    return safe_path

@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    rel_path = request.args.get('path', '')
    try:
        abs_path = get_safe_path(rel_path)
    except ValueError: return jsonify({"error": "Invalid path"}), 400
    
    if not os.path.exists(abs_path): return jsonify([])
    
    items = []
    for f in os.listdir(abs_path):
        if f.startswith('.'): continue
        path = os.path.join(abs_path, f)
        stats = os.stat(path)
        items.append({
            "name": f,
            "path": os.path.relpath(path, DOWNLOAD_BASE),
            "is_dir": os.path.isdir(path),
            "size": stats.st_size if os.path.isfile(path) else 0,
            "date": datetime.fromtimestamp(stats.st_mtime, tz=timezone.utc).isoformat()
        })
    return jsonify(sorted(items, key=lambda x: (not x['is_dir'], x['date']), reverse=True))

@app.route('/api/downloads/tree', methods=['GET'])
def get_directory_tree():
    # Returns only directories for the move/copy selector
    tree = []
    for root, dirs, files in os.walk(DOWNLOAD_BASE):
        rel_root = os.path.relpath(root, DOWNLOAD_BASE)
        if rel_root == ".": rel_root = ""
        # Filter out hidden dirs
        if any(part.startswith('.') for part in rel_root.split(os.sep)): continue
        tree.append(rel_root)
    return jsonify(sorted(tree))

@app.route('/api/downloads/mkdir', methods=['POST'])
def create_directory():
    data = request.json
    try:
        path = get_safe_path(os.path.join(data.get('parent', ''), data.get('name', '')))
        os.makedirs(path, exist_ok=True)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/downloads/move', methods=['POST'])
def move_item():
    data = request.json
    try:
        src = get_safe_path(data.get('src'))
        dst = os.path.join(get_safe_path(data.get('dst')), os.path.basename(src))
        shutil.move(src, dst)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/downloads/copy', methods=['POST'])
def copy_item():
    data = request.json
    try:
        src = get_safe_path(data.get('src'))
        dst = os.path.join(get_safe_path(data.get('dst')), os.path.basename(src))
        if os.path.isdir(src): shutil.copytree(src, dst)
        else: shutil.copy2(src, dst)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/downloads/delete-bulk', methods=['POST'])
def delete_bulk():
    data = request.json
    paths = data.get('paths', [])
    success_count = 0
    errors = []
    
    for rel_path in paths:
        try:
            abs_path = get_safe_path(rel_path)
            if os.path.exists(abs_path):
                if os.path.isdir(abs_path): shutil.rmtree(abs_path)
                else: os.remove(abs_path)
                success_count += 1
        except Exception as e:
            errors.append(str(e))
            
    return jsonify({"success": True, "count": success_count, "errors": errors})

@app.route('/api/downloads/<path:filename>', methods=['GET'])
def download_file(filename):
    # Support subdirectories in GET
    as_attachment = request.args.get('view') != 'true'
    return send_from_directory(DOWNLOAD_BASE, filename, as_attachment=as_attachment)

@app.route('/api/downloads/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        path = get_safe_path(filename)
        if os.path.isdir(path): shutil.rmtree(path)
        else: os.remove(path)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 400

# SocketIO Progress Handlers
def emit_progress(task_id, percent, text):
    status = "running"
    if task_id in background_tasks:
        background_tasks[task_id].update({"progress": percent, "text": text})
        status = background_tasks[task_id].get('status', 'running')
    socketio.emit('progress', {"task_id": task_id, "progress": percent, "text": text, "status": status})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"success": True})

# Business Logic

# Download Logic
@app.route('/api/download/single', methods=['POST'])
def start_single():
    data = request.json
    url = data.get('url')
    profile = data.get('profile')
    
    if not profile or profile == "Default":
        # Check if Default actually has settings (rare in new structure)
        cd, settings_file, _, _ = get_profile_paths(profile)
        if not os.path.exists(settings_file):
            return jsonify({"error": "Please select a valid account profile"}), 400

    print(f"DEBUG: Start Single Download - URL: {url}, Profile: {profile}")
    
    task_id = f"single_{int(datetime.now().timestamp())}"
    background_tasks[task_id] = {
        "status": "running", 
        "progress": 0, 
        "text": "Starting...",
        "profile": profile,
        "pause_event": threading.Event(),
        "cancel_event": threading.Event()
    }
    
    asyncio.run_coroutine_threadsafe(handle_single(task_id, url, profile), loop)
    return jsonify({"task_id": task_id, "status": "success"})

@app.route('/api/download/pause', methods=['POST'])
def pause_task():
    task_id = request.json.get('task_id')
    if task_id in background_tasks:
        background_tasks[task_id]['pause_event'].set()
        background_tasks[task_id]['status'] = 'paused'
        return jsonify({"success": True})
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/download/resume', methods=['POST'])
def resume_task():
    task_id = request.json.get('task_id')
    if task_id in background_tasks:
        background_tasks[task_id]['pause_event'].clear()
        background_tasks[task_id]['status'] = 'running'
        return jsonify({"success": True})
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/download/cancel', methods=['POST'])
def cancel_task():
    task_id = request.json.get('task_id')
    if task_id in background_tasks:
        background_tasks[task_id]['cancel_event'].set()
        background_tasks[task_id]['status'] = 'cancelled'
        return jsonify({"success": True})
    return jsonify({"error": "Task not found"}), 404

async def handle_single(task_id, url, profile):
    print(f"DEBUG: Task {task_id} starting in background thread")
    try:
        print(f"DEBUG: Fetching downloader for profile: {profile}")
        downloader = await get_downloader(profile)
        if not downloader:
            print(f"DEBUG: Task {task_id} failed - No Downloader")
            emit_progress(task_id, 0, "Error: Missing API Credentials")
            return

        print(f"DEBUG: Parsing link: {url}")
        chat_id, message_id = parse_telegram_link(url)
        if not chat_id or not message_id:
            print(f"DEBUG: Task {task_id} failed - Invalid link")
            emit_progress(task_id, 0, "Error: Invalid Link")
            return

        print(f"DEBUG: Fetching message {message_id} from {chat_id}")
        msg = await downloader.get_message(chat_id, message_id)
        if not msg or not msg.media:
            print(f"DEBUG: Task {task_id} failed - No media found")
            emit_progress(task_id, 0, "Error: No Media")
            return

        ext = downloader.get_extension(msg.media)
        filename = f"DL_{msg.id}{ext}"
        path = os.path.join(DOWNLOAD_BASE, filename)
        
        print(f"DEBUG: Task {task_id} - Starting download to {path}")

        async def cb(c, t):
            p = (c/t)*100 if t else 0
            emit_progress(task_id, p, f"{p:.1f}% | {c/1048576:.1f}/{t/1048576:.1f}MB")

        await downloader.download_media(
            msg, 
            path, 
            progress_callback=cb,
            pause_flag=background_tasks[task_id]['pause_event'].is_set,
            cancel_flag=background_tasks[task_id]['cancel_event'].is_set
        )
        print(f"DEBUG: Task {task_id} - Download Complete")
        emit_progress(task_id, 100, f"Done: {filename}")
        background_tasks[task_id]['status'] = 'done'
    except Exception as e:
        print(f"DEBUG: Task {task_id} - Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        if task_id in background_tasks:
            background_tasks[task_id]['status'] = 'failed'
        emit_progress(task_id, 0, f"Error: {str(e)}")

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    # Filter out non-serializable objects
    clean_tasks = {}
    for tid, tdata in background_tasks.items():
        clean_tasks[tid] = {k: v for k, v in tdata.items() if not k.endswith('_event')}
    return jsonify(clean_tasks)

# Catch-all route to serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # If the path looks like an API route but wasn't matched, return 404
    if path.startswith('api/'):
        return jsonify({"error": "Not Found"}), 404
        
    # If requested path is a file in static folder, serve it
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    
    # Otherwise, serve index.html for React Router
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    if not request.path.startswith('/api/'):
        return app.send_static_file('index.html')
    return jsonify({"error": "Not Found"}), 404

if __name__ == '__main__':
    port = int(os.getenv('WEB_BACKEND_PORT', 5000))
    is_dev = os.getenv('NODE_ENV') != 'production'
    # Disabling debug in production prevents the Werkzeug "unsafe server" error
    socketio.run(app, host='0.0.0.0', port=port, debug=is_dev, allow_unsafe_werkzeug=not is_dev)
