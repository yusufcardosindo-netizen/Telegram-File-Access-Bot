import sqlite3
import time
from typing import Optional, List, Dict, Any
from config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Files metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_code TEXT UNIQUE NOT NULL,
                file_id TEXT,
                file_type TEXT NOT NULL,
                file_name TEXT,
                file_size INTEGER DEFAULT 0,
                local_path TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Active file shares table (for self-destruction tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                file_message_id INTEGER NOT NULL,
                warning_message_id INTEGER NOT NULL,
                file_code TEXT,
                expires_at REAL NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Bot settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()

def add_file(file_code: str, file_type: str, file_id: Optional[str] = None,
             file_name: Optional[str] = None, file_size: int = 0,
             local_path: Optional[str] = None, is_default: int = 0) -> int:
    """Save or update a file record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_default:
            cursor.execute("UPDATE files SET is_default = 0")
            
        cursor.execute("""
            INSERT INTO files (file_code, file_id, file_type, file_name, file_size, local_path, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_code) DO UPDATE SET
                file_id = excluded.file_id,
                file_type = excluded.file_type,
                file_name = excluded.file_name,
                file_size = excluded.file_size,
                local_path = excluded.local_path,
                is_default = excluded.is_default
        """, (file_code, file_id, file_type, file_name, file_size, local_path, is_default))
        conn.commit()
        return cursor.lastrowid

def get_file(file_code: str) -> Optional[Dict[str, Any]]:
    """Retrieve file metadata by code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE file_code = ?", (file_code,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_file_id(file_code: str, file_id: str):
    """Update Telegram file_id for a registered file to enable instant sending."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE files SET file_id = ? WHERE file_code = ?", (file_id, file_code))
        conn.commit()

def get_default_file() -> Optional[Dict[str, Any]]:
    """Retrieve default file (or most recently added file)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE is_default = 1 ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            # Fallback to the latest file
            cursor.execute("SELECT * FROM files ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
        return dict(row) if row else None

def set_default_file(file_code: str) -> bool:
    """Set a file as default."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE files SET is_default = 0")
        cursor.execute("UPDATE files SET is_default = 1 WHERE file_code = ?", (file_code,))
        conn.commit()
        return cursor.rowcount > 0

def list_files() -> List[Dict[str, Any]]:
    """List all available files."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_file(file_code: str) -> bool:
    """Delete a file by its code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE file_code = ?", (file_code,))
        conn.commit()
        return cursor.rowcount > 0

def record_active_share(chat_id: int, file_message_id: int, warning_message_id: int,
                        file_code: str, expires_at: float) -> int:
    """Record a delivered file share that needs self-destruction."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO active_shares (chat_id, file_message_id, warning_message_id, file_code, expires_at, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (chat_id, file_message_id, warning_message_id, file_code, expires_at))
        conn.commit()
        return cursor.lastrowid

def get_pending_active_shares() -> List[Dict[str, Any]]:
    """Get all shares that are still active for self-destruct processing."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM active_shares WHERE status = 'active'")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def mark_share_deleted(share_id: int):
    """Mark an active share as deleted."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE active_shares SET status = 'deleted' WHERE id = ?", (share_id,))
        conn.commit()

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get bot setting value."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

def set_setting(key: str, value: str):
    """Set bot setting value."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, value))
        conn.commit()
