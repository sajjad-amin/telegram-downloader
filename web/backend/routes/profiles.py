import os
import shutil
import asyncio
from flask import Blueprint, request, jsonify
from backend.constants import CONFIG_DIR, get_profile_paths
from backend.tasks import login_sessions, loop
from backend.common import get_downloader

profiles_bp = Blueprint('profiles', __name__)

@profiles_bp.route('', methods=['GET'])
def get_profiles():
    if not os.path.exists(CONFIG_DIR): return jsonify([])
    profiles = sorted([d for d in os.listdir(CONFIG_DIR) 
                  if os.path.isdir(os.path.join(CONFIG_DIR, d)) and d.isdigit()])
    return jsonify(profiles)

@profiles_bp.route('/<phone>', methods=['DELETE'])
def delete_profile(phone):
    profile_dir = os.path.join(CONFIG_DIR, phone)
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir)
        return jsonify({"success": True})
    return jsonify({"error": "Profile not found"}), 404

@profiles_bp.route('/login/start', methods=['POST'])
def login_start():
    data = request.json
    phone = data.get('phone', '').strip().replace(' ', '').replace('-', '').replace('+', '')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    
    if not phone: return jsonify({"error": "Phone required"}), 400
    
    final_id = api_id or os.getenv('API_ID')
    final_hash = api_hash or os.getenv('API_HASH')
    
    if not final_id or not final_hash:
        return jsonify({"error": "API credentials missing"}), 400

    session_dir = os.path.join(CONFIG_DIR, phone)
    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, 'my_account')
    
    from core.telegram_client import TelegramDownloader
    downloader = TelegramDownloader(session_path, final_id, final_hash, loop=loop)
    
    async def do_start():
        await downloader.connect()
        return await downloader.client.send_code_request(phone)

    try:
        sent_code = asyncio.run_coroutine_threadsafe(do_start(), loop).result()
        login_sessions[phone] = {
            'downloader': downloader,
            'phone': phone,
            'phone_code_hash': sent_code.phone_code_hash
        }
        return jsonify({"success": True, "phone": phone})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@profiles_bp.route('/login/verify', methods=['POST'])
def login_verify():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    password = data.get('password')
    
    if phone not in login_sessions:
        return jsonify({"error": "Session expired"}), 400
    
    sess = login_sessions[phone]
    downloader = sess['downloader']
    
    async def do_verify():
        try:
            await downloader.client.sign_in(phone, code, phone_code_hash=sess['phone_code_hash'])
        except Exception as e:
            if "password" in str(e).lower() and password:
                await downloader.client.sign_in(password=password)
            else: raise e
        return True

    try:
        asyncio.run_coroutine_threadsafe(do_verify(), loop).result()
        # Save credentials to profile local settings
        cd, settings_file, _, _ = get_profile_paths(phone)
        import configparser
        config = configparser.ConfigParser()
        config['General'] = {'API_ID': str(downloader.api_id), 'API_HASH': downloader.api_hash}
        with open(settings_file, 'w') as f: config.write(f)
        
        del login_sessions[phone]
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
