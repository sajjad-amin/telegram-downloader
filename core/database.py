import sqlite3
import os

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT,
                    message_id INTEGER,
                    message_date INTEGER,
                    file_type TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    status TEXT DEFAULT 'pending',
                    file_path TEXT,
                    UNIQUE(channel_id, message_id)
                )
            """)
            conn.commit()

    def add_item(self, channel_id, message_id, message_date, file_type, file_name, file_size):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO downloads 
                (channel_id, message_id, message_date, file_type, file_name, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(channel_id), message_id, message_date, file_type, file_name, file_size))
            conn.commit()

    def get_pending_items(self, only_ids=None):
        with sqlite3.connect(self.db_path) as conn:
            if only_ids:
                # If the user specifically selected files, we fetch them regardless of status
                placeholders = ','.join('?' for _ in only_ids)
                query = f"SELECT * FROM downloads WHERE id IN ({placeholders})"
                params = only_ids
            else:
                # Otherwise, stay with only pending ones
                query = "SELECT * FROM downloads WHERE status = 'pending'"
                params = []
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def get_items_by_id(self, item_ids):
        if not item_ids: return []
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' for _ in item_ids)
            query = f"SELECT * FROM downloads WHERE id IN ({placeholders})"
            cursor = conn.execute(query, item_ids)
            return cursor.fetchall()

    def update_status(self, channel_id, message_id, status, file_path=None):
        with sqlite3.connect(self.db_path) as conn:
            if file_path:
                conn.execute("UPDATE downloads SET status = ?, file_path = ? WHERE channel_id = ? AND message_id = ?",
                             (status, file_path, str(channel_id), message_id))
            else:
                conn.execute("UPDATE downloads SET status = ? WHERE channel_id = ? AND message_id = ?",
                             (status, str(channel_id), message_id))
            conn.commit()

    def delete_items(self, item_ids):
        if not item_ids: return
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' for _ in item_ids)
            conn.execute(f"DELETE FROM downloads WHERE id IN ({placeholders})", item_ids)
            conn.commit()

    def update_items_status(self, item_ids, status):
        if not item_ids: return
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' for _ in item_ids)
            conn.execute(f"UPDATE downloads SET status = ? WHERE id IN ({placeholders})", [status] + list(item_ids))
            conn.commit()

    def clear_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM downloads")
            conn.commit()

    def get_max_message_id(self, channel_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT MAX(message_id) FROM downloads WHERE channel_id = ?", (str(channel_id),))
            res = cursor.fetchone()
            return res[0] if res and res[0] else 0

    def get_min_message_id(self, channel_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT MIN(message_id) FROM downloads WHERE channel_id = ?", (str(channel_id),))
            res = cursor.fetchone()
            return res[0] if res and res[0] else None

    def get_items_paged(self, limit=100, offset=0, sort_by='message_id', order='DESC', status_filter=None, type_filter=None):
        sort_map = {
            'message_id': 'message_id', 
            'size': 'file_size', 
            'status': 'status', 
            'date': 'message_date', 
            'type': 'file_type',
            'name': 'file_name'
        }
        sort_col = sort_map.get(sort_by, 'message_id')
        
        query = f"SELECT * FROM downloads WHERE 1=1"
        params = []
        if status_filter:
            if status_filter == 'hide_completed':
                query += " AND status != 'completed'"
            else:
                query += " AND status = ?"
                params.append(status_filter)
        if type_filter:
            query += " AND file_type = ?"
            params.append(type_filter)
            
        query += f" ORDER BY {sort_col} {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def get_total_count(self, status_filter=None, type_filter=None):
        query = "SELECT COUNT(*) FROM downloads WHERE 1=1"
        params = []
        if status_filter:
            if status_filter == 'hide_completed':
                query += " AND status != 'completed'"
            else:
                query += " AND status = ?"
                params.append(status_filter)
        if type_filter:
            query += " AND file_type = ?"
            params.append(type_filter)
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]

    def get_all_items(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM downloads")
            return cursor.fetchall()
