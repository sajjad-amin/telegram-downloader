import asyncio
import os
import time
from telethon import TelegramClient, utils

class TelegramDownloader:
    def __init__(self, session_path, api_id, api_hash, loop=None):
        self.session_path = session_path
        self.api_id = api_id
        self.api_hash = api_hash
        try:
            aid = int(api_id) if api_id else 0
        except ValueError:
            aid = 0
            
        self.loop = loop
        self.client = TelegramClient(session_path, aid, api_hash, loop=self.loop)
        
        if not self.loop:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

    async def connect(self):
        await self.client.connect()

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    async def is_authorized(self):
        return await self.client.is_user_authorized()

    async def send_code(self, phone):
        return await self.client.send_code_request(phone)

    async def sign_in(self, phone, code):
        return await self.client.sign_in(phone, code)

    async def get_message(self, chat_id, message_id):
        # Convert numeric strings to int for Telethon compatibility
        try:
            if isinstance(chat_id, str) and (chat_id.startswith('-') or chat_id.isdigit()):
                chat_id = int(chat_id)
        except: pass
        return await self.client.get_messages(chat_id, ids=message_id)

    async def download_media(self, message, file_path, progress_callback=None, pause_flag=None, cancel_flag=None):
        """
        Downloads media with support for pause and cancel.
        """
        # Accurate Total Size Detection
        total_size = 0
        if message.document: 
            total_size = message.document.size
        elif message.photo:
            # Get the largest size
            if hasattr(message.photo, 'sizes') and message.photo.sizes:
                largest = message.photo.sizes[-1]
                # Some sizes have .size, some have a list of bytes
                total_size = getattr(largest, 'size', 0)
                if not total_size and hasattr(largest, 'sizes'): 
                    total_size = largest.sizes[-1]
                if not total_size and hasattr(message.photo, 'large_size'):
                    total_size = message.photo.large_size
        elif hasattr(message, 'audio') and message.audio:
            total_size = getattr(message.document, 'size', 0)
        elif hasattr(message, 'video') and message.video:
            total_size = getattr(message.document, 'size', 0)
        
        # Fallback to general file size if detected via Telethon utils
        if not total_size and message.file:
            total_size = message.file.size

        # Fallback if still 0 but media exists
        if total_size == 0 and message.media:
            if hasattr(message.media, 'document') and message.media.document:
                total_size = message.media.document.size
            elif hasattr(message.media, 'photo') and message.media.photo:
                try: total_size = message.media.photo.sizes[-1].size
                except: total_size = 0
        
        downloaded_bytes = 0
        if os.path.exists(file_path):
            downloaded_bytes = os.path.getsize(file_path)

        # If file is already fully downloaded
        if total_size > 0 and downloaded_bytes >= total_size:
            if progress_callback: await progress_callback(total_size, total_size)
            return file_path

        # Determine mode: 'ab' if resuming, 'wb' if starting fresh
        mode = 'ab' if downloaded_bytes > 0 else 'wb'

        # Telethon's iter_download works best when passed the specific media object (Photo/Document)
        # rather than the MessageMedia wrapper in some edge cases.
        target = message.media 
        if message.photo: target = message.photo
        elif message.document: target = message.document

        with open(file_path, mode) as f:
            async for chunk in self.client.iter_download(target, offset=downloaded_bytes):
                # Check for cancel
                if cancel_flag and cancel_flag():
                    break
                
                # Handle Pause: wait here instead of breaking
                while pause_flag and pause_flag():
                    if cancel_flag and cancel_flag(): break
                    await asyncio.sleep(0.5)

                f.write(chunk)
                downloaded_bytes += len(chunk)
                if progress_callback:
                    await progress_callback(downloaded_bytes, total_size)

        return file_path

    async def iter_channel_messages(self, entity, limit=None, min_id=0, max_id=0, filter_types=None):
        """
        Iterates over messages in a channel and yields those matching the filters.
        filter_types: list of strings ('video', 'audio', 'document', 'photo')
        """
        m_min = int(min_id) if min_id else 0
        m_max = int(max_id) if max_id else 0

        iterator = self.client.iter_messages(
            entity,
            limit=limit,
            min_id=m_min,
            max_id=m_max
        )

        async for message in iterator:
            if not message or not message.media:
                continue
            
            # Type Detection
            media_type = self.get_media_type(message)

            if filter_types and media_type not in filter_types:
                continue
            
            yield message, media_type

    def get_media_type(self, message):
        if not message or not message.media: return None
        media_type = 'file'
        if message.video: media_type = 'video'
        elif message.audio or message.voice: media_type = 'audio'
        elif message.photo: media_type = 'photo'
        elif message.document:
            mime = (message.document.mime_type or '').lower()
            if 'video' in mime: media_type = 'video'
            elif 'audio' in mime: media_type = 'audio'
            else: media_type = 'file'
        return media_type

    def get_extension(self, media):
        if not media: return ""
        ext = utils.get_extension(media)
        if not ext:
            if hasattr(media, 'photo') or (hasattr(media, 'sizes') and not hasattr(media, 'document')):
                return ".jpg" # Default for photos if detection fails
            return ".bin" # Fallback
        return ext
