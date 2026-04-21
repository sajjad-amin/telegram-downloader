import os
import sys
import configparser
from backend.constants import CONFIG_DIR, get_profile_paths
from backend.tasks import active_profiles, loop

# Ensure core is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from core.telegram_client import TelegramDownloader

async def get_downloader(profile_name):
    if profile_name in active_profiles:
        return active_profiles[profile_name]
    
    cd, settings_file, session_file, db_file = get_profile_paths(profile_name)
    
    config = configparser.ConfigParser()
    if os.path.exists(settings_file):
        config.read(settings_file)
    
    api_id = config.get('General', 'API_ID', fallback=None)
    api_hash = config.get('General', 'API_HASH', fallback=None)
    
    if not api_id or not api_hash:
        root_settings = os.path.join(CONFIG_DIR, "settings.ini")
        if os.path.exists(root_settings):
            config.read(root_settings)
            api_id = config.get('General', 'API_ID', fallback=None)
            api_hash = config.get('General', 'API_HASH', fallback=None)

    if not api_id or not api_hash:
        return None
        
    downloader = TelegramDownloader(session_file, api_id, api_hash, loop=loop)
    await downloader.connect()
    active_profiles[profile_name] = downloader
    return downloader
