import asyncio
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from core.telegram_client import TelegramDownloader
from core.utils import parse_telegram_link

load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone_number = os.getenv('PHONE_NUMBER')

if not api_id or not api_hash or not phone_number:
    print("Error: Please set API_ID, API_HASH, and PHONE_NUMBER in your .env file.")
    exit(1)

# Setup config directory
HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".telegram_video_downloader")
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

SESSION_FILE = os.path.join(CONFIG_DIR, "my_account")

# Initialize TelegramDownloader
downloader = TelegramDownloader(SESSION_FILE, api_id, api_hash)
start_time = None

async def progress_callback(current, total):
    global start_time

    if start_time is None:
        start_time = time.time()

    elapsed_time = time.time() - start_time
    if elapsed_time == 0:
        elapsed_time = 0.001

    if total:
        percent = (current / total) * 100
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        speed_bps = current / elapsed_time
        speed_mbps = speed_bps / (1024 * 1024)

        print(
            f'\rDownloading: {percent:.2f}%  ({current_mb:.2f} MB / {total_mb:.2f} MB) | Speed: {speed_mbps:.2f} MB/s',
            end='', flush=True)

async def main():
    global start_time

    await downloader.connect()
    
    if not await downloader.is_authorized():
        await downloader.send_code(phone_number)
        code = input("Enter the code you received: ").strip()
        await downloader.sign_in(phone_number, code)

    url = input("Enter Telegram Message Link: ").strip()
    chat_id, message_id = parse_telegram_link(url)

    if not chat_id or not message_id:
        print("Invalid Telegram link format. Please try again.")
        return

    custom_name = input("Enter file name (leave blank to save by time): ").strip()

    print("Fetching media info...")

    try:
        message = await downloader.get_message(chat_id, message_id)

        if message and message.media:
            print("Media found! Downloading...")
            start_time = None
            ext = downloader.get_extension(message.media)

            if not custom_name:
                custom_name = datetime.now().strftime("%Y%m%d_%H%M%S")

            final_file_name = f"{custom_name}{ext}"

            path = await downloader.download_media(
                message,
                file_path=final_file_name,
                progress_callback=progress_callback
            )
            print(f"\n\nDownloaded successfully! Saved to: {path}")
        else:
            print("\nMedia not found or the message ID is incorrect!")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
