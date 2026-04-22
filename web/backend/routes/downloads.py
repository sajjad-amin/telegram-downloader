import os
import sys
import time
import shutil
import asyncio
import threading
from flask import Blueprint, request, jsonify, send_file
from backend.constants import DOWNLOAD_BASE, get_safe_path
from backend.tasks import background_tasks, emit_progress, loop
from backend.common import get_downloader

# Path fix for core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from core.utils import parse_telegram_link

downloads_bp = Blueprint('downloads', __name__) # For /api/downloads (File Manager)
single_download_bp = Blueprint('single_download', __name__) # For /api/download (Media)

@downloads_bp.route('/tree', methods=['GET'])
def get_tree():
    """Returns a flat list of all directories under DOWNLOAD_BASE."""
    dirs = [''] # Root
    for root, subdirs, files in os.walk(DOWNLOAD_BASE):
        for d in subdirs:
            full_path = os.path.join(root, d)
            rel_path = os.path.relpath(full_path, DOWNLOAD_BASE)
            dirs.append(rel_path)
    return jsonify(dirs)

@downloads_bp.route('', methods=['GET'])
def list_downloads():
    path = request.args.get('path', '')
    abs_path = get_safe_path(path)
    if not os.path.exists(abs_path): return jsonify([])
    
    items = []
    for d in os.listdir(abs_path):
        full = os.path.join(abs_path, d)
        stat = os.stat(full)
        items.append({
            "name": d,
            "is_dir": os.path.isdir(full),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "path": os.path.join(path, d) if path else d
        })
    return jsonify(items)

@downloads_bp.route('/file/<path:filename>')
def get_file(filename):
    abs_path = get_safe_path(filename)
    if not os.path.exists(abs_path): return "Not Found", 404
    return send_file(abs_path)

@downloads_bp.route('/mkdir', methods=['POST'])
def mkdir():
    data = request.json
    parent = data.get('parent', '')
    name = data.get('name', 'New Folder')
    target = os.path.join(get_safe_path(parent), name)
    os.makedirs(target, exist_ok=True)
    return jsonify({"success": True})

@downloads_bp.route('/delete-bulk', methods=['POST'])
def delete_bulk():
    data = request.json
    paths = data.get('paths', [])
    for p in paths:
        abs_p = get_safe_path(p)
        if os.path.exists(abs_p):
            if os.path.isdir(abs_p): shutil.rmtree(abs_p)
            else: os.remove(abs_p)
    return jsonify({"success": True})

@downloads_bp.route('/<path:path>', methods=['DELETE'])
def delete_single(path):
    abs_p = get_safe_path(path)
    if os.path.exists(abs_p):
        if os.path.isdir(abs_p): shutil.rmtree(abs_p)
        else: os.remove(abs_p)
        return jsonify({"success": True})
    return jsonify({"error": "Not Found"}), 404

@downloads_bp.route('/rename', methods=['POST'])
def rename():
    data = request.json
    old_path = get_safe_path(data.get('old_path'))
    new_name = data.get('new_name')
    if not old_path or not new_name: return jsonify({"error": "Missing params"}), 400
    new_path = os.path.join(os.path.dirname(old_path), new_name)
    os.rename(old_path, new_path)
    return jsonify({"success": True})

@downloads_bp.route('/move', methods=['POST'])
def move_items():
    data = request.json
    items = data.get('items', [])
    target_dir = get_safe_path(data.get('target', ''))
    if not os.path.isdir(target_dir): return jsonify({"error": "Target is not a directory"}), 400
    for it in items:
        source = get_safe_path(it)
        if os.path.exists(source):
            shutil.move(source, os.path.join(target_dir, os.path.basename(source)))
    return jsonify({"success": True})

@downloads_bp.route('/copy', methods=['POST'])
def copy_items():
    data = request.json
    items = data.get('items', [])
    target_dir = get_safe_path(data.get('target', ''))
    if not os.path.isdir(target_dir): return jsonify({"error": "Target is not a directory"}), 400
    for it in items:
        source = get_safe_path(it)
        if os.path.exists(source):
            dst = os.path.join(target_dir, os.path.basename(source))
            if os.path.isdir(source):
                shutil.copytree(source, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(source, dst)
    return jsonify({"success": True})

@single_download_bp.route('/single', methods=['POST'])
def single_download():
    data = request.json
    url = data.get('url')
    profile = data.get('profile')
    if not url or not profile: return jsonify({"error": "URL and Profile required"}), 400
    
    task_id = f"single_{int(time.time())}"
    background_tasks[task_id] = {
        "status": "running", "progress": 0, "text": "Initializing...", "profile": profile,
        "pause_event": threading.Event(), "cancel_event": threading.Event()
    }
    
    asyncio.run_coroutine_threadsafe(handle_single(task_id, url, profile), loop)
    return jsonify({"task_id": task_id})

@single_download_bp.route('/<action>', methods=['POST'])
def control_task(action):
    task_id = request.json.get('task_id')
    if task_id not in background_tasks: return jsonify({"error": "Task not found"}), 404
    
    if action == 'pause': background_tasks[task_id]['pause_event'].set()
    elif action == 'resume': background_tasks[task_id]['pause_event'].clear()
    elif action == 'cancel': background_tasks[task_id]['cancel_event'].set()
    
    return jsonify({"success": True})

async def handle_single(task_id, url, profile):
    try:
        downloader = await get_downloader(profile)
        if not downloader: raise Exception("Failed to initialize telegram client")
        
        chat_id, message_id = parse_telegram_link(url)
        if not chat_id:
            emit_progress(task_id, 0, "Error: Invalid Link", status='failed')
            return

        m = await downloader.get_message(chat_id, message_id)
        if hasattr(m, '__iter__') and not hasattr(m, 'media'):
            m = m[0] if len(m) > 0 else None
            
        if not m or not m.media:
            emit_progress(task_id, 0, "No media found in message", status='failed')
            return

        ext = downloader.get_extension(m.media)
        filename = f"DL_{m.id}{ext}"
        path = os.path.join(DOWNLOAD_BASE, filename)
        
        last_emit = time.time()
        last_c = 0
        async def cb(c, t):
            nonlocal last_emit, last_c
            now = time.time()
            dt = now - last_emit
            if dt < 0.5 and c < t: return
            
            p = (c/t)*100 if t else 0
            speed = (c - last_c) / dt if dt > 0 else 0
            
            last_emit = now
            last_c = c
            
            # Format sizes and speed
            c_mb = c / (1024*1024)
            t_mb = t / (1024*1024)
            s_mb = speed / (1024*1024)
            
            size_text = f"{c_mb:.1f}/{t_mb:.1f} MB"
            speed_text = f"{s_mb:.2f} MB/s"
            text = f"Downloading: {filename} | {size_text} | {speed_text}"
            
            emit_progress(task_id, p, text)

        await downloader.download_media(m, path, progress_callback=cb,
            pause_flag=background_tasks[task_id]['pause_event'].is_set,
            cancel_flag=background_tasks[task_id]['cancel_event'].is_set
        )
        emit_progress(task_id, 100, f"Done: {filename}", status='done')
    except Exception as e:
        emit_progress(task_id, 0, f"Error: {str(e)}", status='failed')
