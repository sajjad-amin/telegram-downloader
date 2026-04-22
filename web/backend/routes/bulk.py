import os
import sys
import time
import asyncio
import threading
import random
from flask import Blueprint, request, jsonify, send_file
from backend.constants import get_profile_paths, get_safe_path
from backend.tasks import background_tasks, emit_progress, loop, socketio
from backend.common import get_downloader

# Core imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from core.database import Database
from core.utils import parse_channel_entity

bulk_bp = Blueprint('bulk', __name__)

@bulk_bp.route('/delete', methods=['POST', 'DELETE'], strict_slashes=False)
@bulk_bp.route('/clear', methods=['POST', 'DELETE'], strict_slashes=False)
def delete_bulk_items_db():
    # Support both JSON body and Query Params
    data = request.get_json(silent=True) or {}
    profile = data.get('profile') or request.args.get('profile')
    
    # Get IDs from body or comma-separated string in URL
    ids = data.get('ids', [])
    if not ids and request.args.get('ids'):
        ids = [int(x) for x in request.args.get('ids').split(',') if x.isdigit()]
    
    if not profile: 
        return jsonify({"error": "Profile required"}), 400
        
    _, _, _, db_file = get_profile_paths(profile)
    db = Database(db_file)
    
    if ids:
        db.delete_items(ids)
        return jsonify({"success": True, "deleted": len(ids)})
    else:
        db.clear_all()
        return jsonify({"success": True, "cleared": True})

@bulk_bp.route('/status', methods=['POST'])
def update_bulk_status():
    data = request.json
    profile = data.get('profile')
    ids = data.get('ids', [])
    status = data.get('status', 'pending')
    
    if not profile or not ids: 
        return jsonify({"error": "Profile and IDs required"}), 400
        
    _, _, _, db_file = get_profile_paths(profile)
    db = Database(db_file)
    db.update_items_status(ids, status)
    return jsonify({"success": True, "updated": len(ids)})

@bulk_bp.route('/export/txt', methods=['GET'])
def export_txt():
    profile = request.args.get('profile')
    arg_ids = request.args.get('ids')
    if not profile: return "Profile required", 400
    
    _, _, _, db_file = get_profile_paths(profile)
    db = Database(db_file)
    
    # If IDs provided, fetch only those. Otherwise fetch all.
    if arg_ids:
        ids = [int(x) for x in arg_ids.split(',') if x.isdigit()]
        items = db.get_items_by_id(ids)
    else:
        items = db.get_items_paged(10000, 0)
    
    output = []
    for it in items:
        ch = str(it[1])
        if ch.startswith('-100'): ch = f"c/{ch[4:]}"
        output.append(f"https://t.me/{ch}/{it[2]}")
        
    from io import BytesIO
    mem = BytesIO()
    mem.write("\n".join(output).encode())
    mem.seek(0)
    return send_file(mem, mimetype='text/plain', as_attachment=True, download_name=f"links_{profile}.txt")

@bulk_bp.route('/export/json', methods=['GET'])
def export_json():
    profile = request.args.get('profile')
    arg_ids = request.args.get('ids')
    if not profile: return "Profile required", 400
    
    _, _, _, db_file = get_profile_paths(profile)
    db = Database(db_file)
    
    if arg_ids:
        ids = [int(x) for x in arg_ids.split(',') if x.isdigit()]
        items = db.get_items_by_id(ids)
    else:
        items = db.get_items_paged(10000, 0)
    
    data = []
    for it in items:
        data.append({
            "channel": it[1], "message_id": it[2], "date": it[3],
            "type": it[4], "name": it[5], "size": it[6], "status": it[7]
        })
        
    import json
    from io import BytesIO
    mem = BytesIO()
    mem.write(json.dumps(data, indent=2).encode())
    mem.seek(0)
    return send_file(mem, mimetype='application/json', as_attachment=True, download_name=f"dump_{profile}.json")

@bulk_bp.route('/import', methods=['POST'])
def import_json():
    profile = request.args.get('profile')
    if not profile: return jsonify({"error": "Profile required"}), 400
    if 'file' not in request.files: return jsonify({"error": "No file"}), 400
    
    file = request.files['file']
    import json
    try:
        data = json.load(file)
        _, _, _, db_file = get_profile_paths(profile)
        db = Database(db_file)
        for it in data:
            db.add_item(it['channel'], it['message_id'], it['date'], it['type'], it['name'], it['size'])
        return jsonify({"success": True, "count": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bulk_bp.route('/items', methods=['GET'])
def get_bulk_items():
    profile = request.args.get('profile')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    sort = request.args.get('sort', 'message_id')
    order = request.args.get('order', 'DESC')
    status = request.args.get('status', 'All')
    mtype = request.args.get('type', 'All')

    if not profile: return jsonify({"items": [], "total": 0})
    _, _, _, db_file = get_profile_paths(profile)
    db = Database(db_file)
    
    # Map filters to database method requirements
    sf = None if status == 'All' else status
    tf = None if mtype == 'All' else mtype
    
    items = db.get_items_paged(limit, offset, sort, order, sf, tf)
    total = db.get_total_count(sf, tf)
    
    clean_items = []
    for it in items:
        clean_items.append({
            "id": it[0], "channel": it[1], "message_id": it[2], "date": it[3],
            "type": it[4], "name": it[5], "size": it[6], "status": it[7], "path": it[8]
        })
    return jsonify({"items": clean_items, "total": total})

@bulk_bp.route('/scan', methods=['POST'])
def bulk_scan():
    data = request.json
    profile = data.get('profile')
    channel = data.get('channel')
    filters = data.get('filters', [])
    direction = data.get('direction', 'forward')
    start_point = data.get('start_point', '')

    if not profile or not channel: return jsonify({"error": "Missing params"}), 400
    
    task_id = f"scan_{int(time.time())}"
    background_tasks[task_id] = {
        "status": "running", "progress": 0, "text": "Starting scan...", "profile": profile,
        "pause_event": threading.Event(), "cancel_event": threading.Event()
    }
    
    asyncio.run_coroutine_threadsafe(handle_scan(task_id, profile, channel, filters, direction, start_point), loop)
    return jsonify({"task_id": task_id})

async def handle_scan(task_id, profile, channel_input, filter_list, direction, start_point):
    print(f"DEBUG: Starting desktop-sync scan for {channel_input}")
    try:
        downloader = await get_downloader(profile)
        if not downloader: raise Exception("Client not ready")
            
        _, _, _, db_file = get_profile_paths(profile)
        db = Database(db_file)
        
        from core.utils import parse_telegram_link
        chat_id, ch_msg_id = parse_channel_entity(channel_input)
        target = chat_id or channel_input
        
        # Desktop Logic: Manual ID vs DB ID
        manual_id = None
        if start_point:
            if str(start_point).isdigit(): manual_id = int(start_point)
            else:
                _, mid = parse_telegram_link(start_point)
                manual_id = mid
        
        m_min, m_max = 0, 0
        if direction == 'new': # Newer
            m_min = manual_id if manual_id is not None else db.get_max_message_id(target)
        else: # Older/Backward
            mn_db = db.get_min_message_id(target)
            m_max = manual_id if manual_id is not None else (mn_db - 1 if mn_db is not None else 0)

        count = 0
        async for m, m_type in downloader.iter_channel_messages(target, min_id=int(m_min or 0), max_id=int(m_max or 0), filter_types=filter_list):
            if background_tasks[task_id]['cancel_event'].is_set(): break
            
            # Desktop Naming: YYYYMMDD_HHMMSS_ID
            f_name = f"{m.date.strftime('%Y%m%d_%H%M%S')}_{m.id}"
            
            # Desktop Size Logic
            f_sz = 0
            if hasattr(m.media, 'document') and m.media.document:
                f_sz = m.media.document.size
            elif hasattr(m.media, 'photo') and m.media.photo:
                try: f_sz = m.media.photo.sizes[-1].size
                except: f_sz = 0
            
            # Desktop Date: Integer Timestamp
            db.add_item(target, m.id, int(m.date.timestamp()), m_type, f_name, f_sz)
            count += 1
            
            if count % 25 == 0:
                emit_progress(task_id, 0, f"Discovered {count} items...")
            
        emit_progress(task_id, 100, f"Scan complete. Found {count} items.", status='done')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        emit_progress(task_id, 0, f"Scan Fail: {str(e)}", status='failed')

@bulk_bp.route('/start', methods=['POST'])
def bulk_start():
    data = request.json
    profile = data.get('profile')
    ids = data.get('ids', [])
    location = data.get('location', '')
    delay = data.get('delay', [5, 15])

    if not profile: return jsonify({"error": "Profile required"}), 400
    
    task_id = f"bulk_{int(time.time())}"
    background_tasks[task_id] = {
        "status": "running", "progress": 0, "text": "Preparing...", "profile": profile,
        "pause_event": threading.Event(), "cancel_event": threading.Event()
    }
    
    asyncio.run_coroutine_threadsafe(handle_bulk_download(task_id, profile, list(ids), location, delay), loop)
    return jsonify({"task_id": task_id})

async def handle_bulk_download(task_id, profile, ids, location, delay):
    try:
        downloader = await get_downloader(profile)
        _, _, _, db_file = get_profile_paths(profile)
        db = Database(db_file)
        
        abs_loc = get_safe_path(location)
        os.makedirs(abs_loc, exist_ok=True)
        
        queue = list(ids)
        
        while True:
            if background_tasks[task_id]['cancel_event'].is_set(): break
            p = db.get_pending_items(queue if queue else None)
            if not p: break
            
            to_proc = [it for it in p if it[7] != 'completed']
            if not to_proc: break
            
            for it in to_proc:
                if background_tasks[task_id]['cancel_event'].is_set(): break
                while background_tasks[task_id]['pause_event'].is_set(): await asyncio.sleep(1)
                
                try:
                    m = await downloader.get_message(it[1], it[2])
                    if not m or not m.media:
                        db.update_status(it[1], it[2], 'failed'); continue
                    
                    # Desktop Logic: Extension is appended here, not stored in DB
                    ext = downloader.get_extension(m.media)
                    fp = os.path.join(abs_loc, f"{it[5]}{ext}")
                    
                    db.update_status(it[1], it[2], 'downloading')
                    
                    last_emit = time.time()
                    last_c = 0
                    async def cb(c, t):
                        nonlocal last_emit, last_c
                        now = time.time()
                        dt = now - last_emit
                        if dt < 0.5 and c < t: return
                        
                        p_val = (c/t)*100 if t else 0
                        speed = (c - last_c) / dt if dt > 0 else 0
                        
                        last_emit = now
                        last_c = c
                        
                        # Format sizes and speed
                        c_mb = c / (1024*1024)
                        t_mb = t / (1024*1024)
                        s_mb = speed / (1024*1024)
                        
                        size_text = f"{c_mb:.1f}/{t_mb:.1f} MB"
                        speed_text = f"{s_mb:.2f} MB/s"
                        text = f"Downloading: {it[5]} | {size_text} | {speed_text}"
                        
                        emit_progress(task_id, p_val, text)
                    
                    await downloader.download_media(m, fp, cb,
                        pause_flag=background_tasks[task_id]['pause_event'].is_set,
                        cancel_flag=background_tasks[task_id]['cancel_event'].is_set)
                    
                    if not background_tasks[task_id]['cancel_event'].is_set() and not background_tasks[task_id]['pause_event'].is_set():
                        db.update_status(it[1], it[2], 'completed', fp)
                        if it[0] in queue: queue.remove(it[0])
                        emit_progress(task_id, 100, f"Finished: {it[5]}", status='running')
                        socketio.emit('bulk_item_done', {'id': it[0], 'profile': profile})
                        
                        mi, mx = delay
                        wait_s = random.randint(min(mi, mx), max(mi, mx))
                        for rem in range(wait_s, 0, -1):
                            if background_tasks[task_id]['cancel_event'].is_set() or background_tasks[task_id]['pause_event'].is_set(): break
                            emit_progress(task_id, 100, f"Next download in {rem}s...")
                            await asyncio.sleep(1)
                    else: db.update_status(it[1], it[2], 'pending')
                    
                except Exception: db.update_status(it[1], it[2], 'failed'); await asyncio.sleep(2)
                
            if not queue or not to_proc: break
            
        emit_progress(task_id, 100, "Bulk download process finished.", status='done')
    except Exception as e:
        background_tasks[task_id]['status'] = 'failed'
        emit_progress(task_id, 0, f"Bulk Error: {str(e)}")
