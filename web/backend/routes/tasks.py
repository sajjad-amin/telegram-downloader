from flask import Blueprint, jsonify, request
from backend.tasks import background_tasks

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('', methods=['GET'])
def get_tasks():
    clean = {}
    for tid, t in background_tasks.items():
        clean[tid] = {
            "progress": t.get("progress", 0),
            "text": t.get("text", ""),
            "status": t.get("status", "running"),
            "profile": t.get("profile")
        }
    return jsonify(clean)

@tasks_bp.route('/clear', methods=['POST'])
def clear_tasks():
    to_delete = [tid for tid, t in background_tasks.items() 
                 if t.get('status') in ['done', 'failed', 'cancelled']]
    for tid in to_delete:
        del background_tasks[tid]
    return jsonify({"success": True, "cleared": len(to_delete)})

@tasks_bp.route('/remove/<task_id>', methods=['DELETE', 'POST'])
def remove_task(task_id):
    if task_id in background_tasks:
        del background_tasks[task_id]
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

@tasks_bp.route('/control/<action>', methods=['POST'])
def control_task(action):
    task_id = request.json.get('task_id')
    if task_id not in background_tasks: return jsonify({"error": "Task not found"}), 404
    
    if action == 'pause': background_tasks[task_id]['pause_event'].set()
    elif action == 'resume': background_tasks[task_id]['pause_event'].clear()
    elif action == 'cancel': background_tasks[task_id]['cancel_event'].set()
    
    return jsonify({"success": True})
