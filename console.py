import asyncio
import time
import os
import sys
import configparser
import select
import random
import argparse
import shutil
from datetime import datetime
from core.telegram_client import TelegramDownloader
from core.utils import parse_telegram_link

# Setup config directory - Perfectly aligned with GUI
HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".telegram_video_downloader")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

ACTIVE_PROFILE_FILE = os.path.join(CONFIG_DIR, "active_profile")

def get_active_profile_name():
    if os.path.exists(ACTIVE_PROFILE_FILE):
        with open(ACTIVE_PROFILE_FILE, "r") as f:
            return f.read().strip()
    return None

def set_active_profile(name):
    with open(ACTIVE_PROFILE_FILE, "w") as f:
        f.write(name)

def get_clean_phone(phone):
    """Strips + from phone numbers for universal directory naming."""
    return phone.replace("+", "")

def get_all_profiles():
    """Returns a list of folders in CONFIG_DIR that consist of digits."""
    if not os.path.exists(CONFIG_DIR): return []
    return sorted([d for d in os.listdir(CONFIG_DIR) 
                  if os.path.isdir(os.path.join(CONFIG_DIR, d)) and d.isdigit()])

def get_config_paths():
    """Determines the current active folder and returns file paths."""
    active_p = get_active_profile_name()
    
    # Auto-trigger profile selection if root is empty and no active profile set
    root_configured = os.path.exists(os.path.join(CONFIG_DIR, "settings.ini")) and \
                      os.path.exists(os.path.join(CONFIG_DIR, "my_account.session"))
    
    if not active_p and not root_configured:
        profiles = get_all_profiles()
        if profiles:
            print("\n[!] No active profile set and root is empty.")
            print("Please select an existing profile account:")
            for i, p in enumerate(profiles, 1): print(f"{i}. {p}")
            choice = input("\nSelect profile number: ").strip()
            try:
                sel = profiles[int(choice)-1]
                set_active_profile(sel)
                active_p = sel
                print(f"Profile {sel} activated.\n")
            except: pass # Will fall back to root/setup

    curr_dir = os.path.join(CONFIG_DIR, active_p) if active_p else CONFIG_DIR
    return curr_dir, \
           os.path.join(curr_dir, "settings.ini"), \
           os.path.join(curr_dir, "my_account"), \
           os.path.join(curr_dir, "downloads.db")

CURRENT_CONFIG_DIR, SETTINGS_FILE, SESSION_FILE, DB_FILE = get_config_paths()
DEFAULT_DOWNLOAD_PATH = os.path.join(HOME_DIR, "tgdl")

def show_documentation():
    name = get_active_profile_name() or "Default (Root)"
    print("\n" + "="*60)
    print("       TELEGRAM DOWNLOADER - COMMAND LINE INTERFACE")
    print(f"       ACTIVE PROFILE: {name}")
    print("="*60)
    print("USAGE:")
    print("  python console.py [URL]              Download single file")
    print("  python console.py links.txt          Download all links in file")
    print("  python console.py --path [DIR]       Set download directory")
    print("  python console.py --profile          Switch/Manage Profiles")
    print("  python console.py --add-account      Login to a new account")
    print("\nDOWNLOAD SHORTCUTS:")
    print("  [P] + [Enter]   Pause/Resume current download")
    print("  [Ctrl+C]        Cancel and Exit")
    print("\nPROFILE INFO:")
    print("  Config Directory: " + CURRENT_CONFIG_DIR)
    print("="*60 + "\n")

# Load configuration from settings.ini (shared with GUI)
config = configparser.ConfigParser()
config.optionxform = str 
if os.path.exists(SETTINGS_FILE):
    config.read(SETTINGS_FILE)

if 'General' not in config.sections():
    config.add_section('General')

# API Inheritance
if not config.get('General', 'api_id', fallback=None):
    root_settings = os.path.join(CONFIG_DIR, "settings.ini")
    if os.path.exists(root_settings) and root_settings != SETTINGS_FILE:
        tmp_cfg = configparser.ConfigParser(); tmp_cfg.read(root_settings)
        aid = tmp_cfg.get('General', 'api_id', fallback=None)
        ahash = tmp_cfg.get('General', 'api_hash', fallback=None)
        if aid and ahash: config.set('General', 'api_id', aid); config.set('General', 'api_hash', ahash)

api_id = config.get('General', 'api_id', fallback=None)
api_hash = config.get('General', 'api_hash', fallback=None)

if not api_id or not api_hash:
    print("=== Telegram Downloader Setup ===")
    print("Credentials not found. Please provide them once.")
    api_id = input("Enter API ID: ").strip()
    api_hash = input("Enter API HASH: ").strip()
    if not api_id or not api_hash:
        print("Error: API ID and Hash are required."); sys.exit(1)
    config.set('General', 'api_id', api_id)
    config.set('General', 'api_hash', api_hash)
    if not os.path.exists(CURRENT_CONFIG_DIR): os.makedirs(CURRENT_CONFIG_DIR)
    with open(SETTINGS_FILE, 'w') as f: config.write(f)

# Global state
start_time = None
is_paused = False
start_bytes = 0

async def progress_callback(current, total):
    global start_time, is_paused, start_bytes
    if start_time is None: start_time = time.time()
    elapsed_time = time.time() - start_time
    if elapsed_time <= 0: elapsed_time = 0.001
    
    # Calculate bytes downloaded in THIS session for accurate speed
    newly_downloaded = current - start_bytes
    if newly_downloaded < 0: newly_downloaded = 0
    
    if total:
        percent = (current / total) * 100
        current_mb, total_mb = current / 1048576, total / 1048576
        speed_mbps = (newly_downloaded / elapsed_time) / 1048576
        if not is_paused:
            print(f'\rDownloading: {percent:.2f}%  ({current_mb:.2f} / {total_mb:.2f} MB) | {speed_mbps:.2f} MB/s | [P] Pause ', end='', flush=True)

def check_pause_flag():
    global is_paused
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        if 'p' in line.lower():
            is_paused = not is_paused
            if is_paused: print("\n\n--- PAUSED --- Press 'P' + Enter to Resume.")
            else: print("--- RESUMING ---\n")
    return is_paused

async def download_single(downloader, url, dest_dir, custom_name=None, is_batch=False):
    global start_time, is_paused, start_bytes
    chat_id, message_id = parse_telegram_link(url)
    if not chat_id or not message_id:
        print(f"Invalid Link: {url}"); return False

    try:
        msg = await downloader.get_message(chat_id, message_id)
        if not msg or not msg.media:
            print(f"No media found for {url}"); return False

        ext = downloader.get_extension(msg.media)
        if not custom_name:
            filename = f"DL_{msg.id}{ext}"
        else:
            expanded_custom = os.path.expanduser(custom_name)
            if os.path.sep in expanded_custom or os.path.isdir(expanded_custom):
                if expanded_custom.endswith(os.path.sep) or os.path.isdir(expanded_custom):
                    dest_dir = expanded_custom
                    filename = f"DL_{msg.id}{ext}"
                else:
                    dest_dir = os.path.dirname(expanded_custom)
                    filename = os.path.basename(expanded_custom)
                    if not filename.lower().endswith(ext.lower()): filename += ext
            else:
                filename = custom_name if custom_name.lower().endswith(ext.lower()) else f"{custom_name}{ext}"
        
        if not os.path.exists(dest_dir): os.makedirs(dest_dir)
        final_path = os.path.join(dest_dir, filename)

        print(f"\nProcessing: {filename}")
        if os.path.exists(final_path):
            current_size = os.path.getsize(final_path)
            print(f"Resuming existing file ({current_size/1048576:.1f} MB)...")
            start_bytes = current_size
        else:
            start_bytes = 0

        start_time = None
        await downloader.download_media(msg, final_path, progress_callback, check_pause_flag)
        print(f"\nFinished: {final_path}")
        
        if not is_batch:
            config.set('General', 'last_single_url', url)
            config.set('General', 'last_single_fp', final_path)
            with open(SETTINGS_FILE, 'w') as f: config.write(f)
        return True
    except Exception as e:
        print(f"\nError downloading {url}: {e}"); return False

async def main():
    parser = argparse.ArgumentParser(description="Telegram Downloader Console")
    parser.add_argument("input", nargs="?", help="Link or file.txt")
    parser.add_argument("--path", help="Download directory")
    parser.add_argument("--profile", action="store_true", help="Manage or Switch Profiles")
    parser.add_argument("--add-account", action="store_true", help="Login to a new account")
    args = parser.parse_args()

    # Use global config and SETTINGS_FILE already initialized at top
    global config
    
    # Update global variables if profile was switched
    global SETTINGS_FILE
    curr_config_dir, settings_file, session_file, db_file = get_config_paths()
    SETTINGS_FILE = settings_file
    if os.path.exists(SETTINGS_FILE):
        config.read(SETTINGS_FILE)

    # API Inheritance
    if not config.get('General', 'api_id', fallback=None):
        root_settings = os.path.join(CONFIG_DIR, "settings.ini")
        if os.path.exists(root_settings) and root_settings != settings_file:
            tmp_cfg = configparser.ConfigParser(); tmp_cfg.read(root_settings)
            aid = tmp_cfg.get('General', 'api_id', fallback=None)
            ahash = tmp_cfg.get('General', 'api_hash', fallback=None)
            if aid and ahash: config.set('General', 'api_id', aid); config.set('General', 'api_hash', ahash)

    api_id = config.get('General', 'api_id', fallback=None)
    api_hash = config.get('General', 'api_hash', fallback=None)

    if not api_id or not api_hash:
        print("=== Telegram Downloader Setup ===")
        print("Credentials not found. Please provide them once.")
        api_id = input("Enter API ID: ").strip()
        api_hash = input("Enter API HASH: ").strip()
        if not api_id or not api_hash:
            print("Error: API ID and Hash are required."); sys.exit(1)
        config.set('General', 'api_id', api_id)
        config.set('General', 'api_hash', api_hash)
        if not os.path.exists(curr_config_dir): os.makedirs(curr_config_dir)
        with open(SETTINGS_FILE, 'w') as f: config.write(f)

    # Initialize downloader with active session inside the loop
    downloader = TelegramDownloader(session_file, api_id, api_hash)

    # Documentation if no arguments
    if len(sys.argv) == 1:
        show_documentation()

    # Determine initial Download Directory
    saved_path = config.get('General', 'last_download_dir_cli', fallback=DEFAULT_DOWNLOAD_PATH)
    dest_dir = args.path if args.path else saved_path
    dest_dir = os.path.expanduser(dest_dir)

    # PROFILE SWITCHER
    if args.profile:
        profiles = ["Default (Root)"] + get_all_profiles()
        print("\n--- Available Profiles ---")
        for i, p in enumerate(profiles, 1): 
            tag = " [ACTIVE]" if (p == "Default (Root)" and not get_active_profile_name()) or (p == get_active_profile_name()) else ""
            print(f"{i}. {p}{tag}")
        print("R. Remove a Profile")
        print("0. Close")
        c = input("\nSelect profile (or 'R'): ").strip().upper()
        if c == "0" or not c: return
        
        if c == 'R':
            c_rem = input("Select number to REMOVE: ").strip()
            try:
                sel_rem = profiles[int(c_rem)-1]
                if sel_rem == "Default (Root)":
                    print("Cannot remove Default profile."); return
                confirm = input(f"Are you sure you want to delete profile {sel_rem}? (y/n): ").lower()
                if confirm == 'y':
                    shutil.rmtree(os.path.join(CONFIG_DIR, sel_rem))
                    if get_active_profile_name() == sel_rem:
                        if os.path.exists(ACTIVE_PROFILE_FILE): os.remove(ACTIVE_PROFILE_FILE)
                    print(f"Profile {sel_rem} removed.")
                return
            except: print("Invalid choice."); return

        try:
            sel = profiles[int(c)-1]
            if sel == "Default (Root)":
                if os.path.exists(ACTIVE_PROFILE_FILE): os.remove(ACTIVE_PROFILE_FILE)
            else:
                set_active_profile(sel)
            
            print(f"\nSuccessfully switched to profile {sel}.")
            print("Please run the script again to initialize.")
            return
        except: print("Invalid choice."); return

    try:
        await downloader.connect()
    except Exception as e:
        if "database is locked" in str(e).lower():
            print("\n[!] Error: Database locked. Please close GUI.\n"); return
        print(f"Connection Error: {e}"); return
    
    # LOGIN LOGIC & PROFILE SYNC
    if args.add_account or not await downloader.is_authorized():
        if args.add_account:
            print("Logging into a NEW account...")
            temp_session_name = os.path.join(CONFIG_DIR, "temp_account")
            if os.path.exists(temp_session_name + ".session"): os.remove(temp_session_name + ".session")
            
            temp_downloader = TelegramDownloader(temp_session_name, api_id, api_hash)
            await temp_downloader.connect()
            ph = input("New Phone: ").strip()
            await temp_downloader.send_code(ph)
            cd = input("Code: ").strip(); await temp_downloader.sign_in(ph, cd)
            
            me = await temp_downloader.client.get_me()
            phone = me.phone or ph
            clean_p = get_clean_phone(phone)
            
            profile_dir = os.path.join(CONFIG_DIR, clean_p)
            if not os.path.exists(profile_dir): os.makedirs(profile_dir)
            
            shutil.move(temp_session_name + ".session", os.path.join(profile_dir, "my_account.session"))
            shutil.copy2(os.path.join(CONFIG_DIR, "settings.ini"), os.path.join(profile_dir, "settings.ini"))
            
            choice = input(f"\nAccount {clean_p} logged in. Set as DEFAULT active account? (y/n): ").lower()
            if choice == 'y':
                set_active_profile(clean_p)
                print("Default account updated! Please restart.")
            else:
                print(f"Saved to profiles/{clean_p}. Switch anytime using --profile.")
            return
        else:
            # First time login prompt handled by telethon flow
            # If authorized just now, set it as active if it's in a folder
            pass

    # Handle Input
    try:
        target = args.input if args.input else input("\nEnter Link or filename.txt: ").strip()
    except EOFError: return 
    if not target: return

    if os.path.isfile(target):
        config.set('General', 'last_download_dir_cli', dest_dir)
        with open(SETTINGS_FILE, 'w') as f: config.write(f)
        print(f"Batch mode: Reading from {target}\nFound links. Target: {dest_dir}")
        with open(target, 'r') as f:
            links = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        for i, url in enumerate(links):
            await download_single(downloader, url, dest_dir, is_batch=True)
            if i < len(links) - 1:
                delay = random.randint(5, 10)
                for r in range(delay, 0, -1):
                    print(f"\rWaiting {r}s (Batch anti-block)...    ", end='', flush=True); await asyncio.sleep(1)
                print("\r" + " " * 60 + "\r", end='', flush=True)
        print("\nBatch download complete.")
    else:
        custom_input = input(f"Enter file name (blank for default, saving to {dest_dir}): ").strip()
        if custom_input:
            exp = os.path.expanduser(custom_input)
            if os.path.isdir(exp) or exp.endswith(os.path.sep): config.set('General', 'last_download_dir_cli', exp)
            elif os.path.sep in exp: config.set('General', 'last_download_dir_cli', os.path.dirname(exp))
        else: config.set('General', 'last_download_dir_cli', dest_dir)
        with open(SETTINGS_FILE, 'w') as f: config.write(f)
        await download_single(downloader, target, dest_dir, custom_input if custom_input else None)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nExiting...")
        sys.exit(0)
