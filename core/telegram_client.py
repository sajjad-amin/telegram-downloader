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
        self.client = TelegramClient(session_path, aid, api_hash, loop=loop)
        try:
            self.loop = loop or asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    async def connect(self):
        await self.client.connect()

    async def is_authorized(self):
        return await self.client.is_user_authorized()

    async def send_code(self, phone):
        return await self.client.send_code_request(phone)

    async def sign_in(self, phone, code):
        return await self.client.sign_in(phone, code)

    async def get_message(self, chat_id, message_id):
        return await self.client.get_messages(chat_id, ids=message_id)

    async def download_media(self, message, file_path, progress_callback=None, pause_flag=None, cancel_flag=None):
        """
        Downloads media with support for pause and cancel.
        """
        # Accurate Total Size Detection
        total_size = 0
        if message.document: total_size = message.document.size
        elif message.photo: total_size = message.photo.sizes[-1].size
        elif message.audio: total_size = message.audio.size
        elif message.video: total_size = message.video.size
        
        downloaded_bytes = 0
        if os.path.exists(file_path):
            downloaded_bytes = os.path.getsize(file_path)

        # If file is already fully downloaded
        if total_size > 0 and downloaded_bytes >= total_size:
            if progress_callback: await progress_callback(total_size, total_size)
            return file_path

        # Determine mode: 'ab' if resuming, 'wb' if starting fresh
        mode = 'ab' if downloaded_bytes > 0 else 'wb'

        with open(file_path, mode) as f:
            async for chunk in self.client.iter_download(message.media, offset=downloaded_bytes):
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

    async def iter_channel_messages(self, entity, min_id=0, max_id=0, limit=None, filter_types=None):
        """
        Iterates over messages in a channel and yields those matching the filters.
        filter_types: list of strings ('video', 'audio', 'document', 'photo')
        """
        # Sanitization: Force everything to clean integers. Telethon uses 0 as 'unset'.
        try:
            m_min = int(min_id) if min_id is not None else 0
        except:
            m_min = 0
            
        try:
            m_max = int(max_id) if max_id is not None else 0
        except:
            m_max = 0
        
        # In Telethon, if we WANT everything until the end, max_id should be 0 OR min_id should be 0.
        # To avoid the None > 0 crash in some telethon versions, we pass integers.
        # If max_id is 0, we'll swap it to None ONLY if min_id is also handled.
        # ACTUALLY, the safest way is to avoid passing max_id=None if min_id=0.
        
        p_max = m_max if m_max > 0 else None
        p_min = m_min if m_min > 0 else None
        
        # Final safety check: never pass one None and one Int if they might be compared.
        if p_max is None and p_min is None:
            # Full scan
            iterator = self.client.iter_messages(entity, limit=limit)
        elif p_max is None:
            # Newer scan
            iterator = self.client.iter_messages(entity, min_id=p_min, limit=limit)
        elif p_min is None:
            # Older scan
            iterator = self.client.iter_messages(entity, max_id=p_max, limit=limit)
        else:
            # Range scan
            iterator = self.client.iter_messages(entity, min_id=p_min, max_id=p_max, limit=limit)

        async for message in iterator:
            if not message or not message.media:
                continue
            
            # Type Detection
            media_type = 'file'
            if message.video: media_type = 'video'
            elif message.audio or message.voice: media_type = 'audio'
            elif message.photo: media_type = 'photo'
            elif message.document:
                mime = (message.document.mime_type or '').lower()
                if 'video' in mime: media_type = 'video'
                elif 'audio' in mime: media_type = 'audio'
                else: media_type = 'file'

            if filter_types and media_type not in filter_types:
                continue
            
            yield message, media_type

    def get_extension(self, media):
        return utils.get_extension(media)
