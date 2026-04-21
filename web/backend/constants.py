import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".telegram_video_downloader")
DOWNLOAD_BASE = os.getenv('DOWNLOAD_PATH', './downloads')
STATIC_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '../dist'))

if not os.path.isabs(DOWNLOAD_BASE):
    DOWNLOAD_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '../', DOWNLOAD_BASE))

if not os.path.exists(DOWNLOAD_BASE):
    os.makedirs(DOWNLOAD_BASE)

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

def get_profile_paths(name):
    cd = os.path.join(CONFIG_DIR, name) if name and name != "Default" else CONFIG_DIR
    return cd, os.path.join(cd, "settings.ini"), os.path.join(cd, "my_account"), os.path.join(cd, "downloads.db")

def get_safe_path(rel_path):
    if not rel_path: return DOWNLOAD_BASE
    abs_path = os.path.abspath(os.path.join(DOWNLOAD_BASE, rel_path))
    if not abs_path.startswith(os.path.abspath(DOWNLOAD_BASE)):
        return DOWNLOAD_BASE
    return abs_path
