import asyncio
import threading
from flask_socketio import SocketIO

# Global state
loop = asyncio.new_event_loop()
background_tasks = {}
active_profiles = {}
login_sessions = {}

# Extension holder (initialized in app_instance)
socketio = SocketIO()

def run_asyncio_loop(loop):
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except Exception as e:
        print(f"Asyncio loop error: {e}")

threading.Thread(target=run_asyncio_loop, args=(loop,), daemon=True).start()

def emit_progress(task_id, percent, text, status=None):
    if task_id in background_tasks:
        background_tasks[task_id].update({"progress": percent, "text": text})
        if status: background_tasks[task_id]['status'] = status
        current_status = background_tasks[task_id].get('status', 'running')
    else:
        current_status = status or "running"
        
    profile = background_tasks[task_id].get('profile') if task_id in background_tasks else None
    socketio.emit('progress', {
        "task_id": task_id, 
        "progress": percent, 
        "text": text, 
        "status": current_status, 
        "profile": profile
    })
