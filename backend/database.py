import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.db")


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database with schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Gaze logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gaze_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                eye_off_center REAL NOT NULL,
                blink INTEGER NOT NULL,
                head_pitch REAL NOT NULL,
                head_yaw REAL NOT NULL,
                head_distance REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tab logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tab_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                domain TEXT NOT NULL,
                title TEXT,
                idle_state TEXT NOT NULL,
                keypress_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Labels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                label TEXT NOT NULL CHECK(label IN ('distracted', 'focused')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gaze_timestamp
            ON gaze_logs(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tab_timestamp
            ON tab_logs(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_labels_timestamp
            ON labels(timestamp)
        """)

        conn.commit()
        print(f"Database initialized at {DB_PATH}")


def insert_gaze_log(timestamp: float, eye_off_center: float, blink: int,
                    head_pitch: float, head_yaw: float, head_distance: float):
    """Insert a gaze log entry."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO gaze_logs
            (timestamp, eye_off_center, blink, head_pitch, head_yaw, head_distance)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp, eye_off_center, blink, head_pitch, head_yaw, head_distance))
        conn.commit()


def insert_tab_log(timestamp: float, domain: str, title: str,
                   idle_state: str, keypress_count: int):
    """Insert a tab log entry."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tab_logs
            (timestamp, domain, title, idle_state, keypress_count)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, domain, title, idle_state, keypress_count))
        conn.commit()


def insert_label(timestamp: float, label: str):
    """Insert a label entry."""
    if label not in ['distracted', 'focused']:
        raise ValueError(f"Label must be 'distracted' or 'focused', got '{label}'")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO labels (timestamp, label)
            VALUES (?, ?)
        """, (timestamp, label))
        conn.commit()


def get_gaze_logs(start_time: Optional[float] = None,
                  end_time: Optional[float] = None) -> List[Dict[str, Any]]:
    """Get gaze logs within a time range."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM gaze_logs WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_tab_logs(start_time: Optional[float] = None,
                 end_time: Optional[float] = None) -> List[Dict[str, Any]]:
    """Get tab logs within a time range."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM tab_logs WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_labels(start_time: Optional[float] = None,
               end_time: Optional[float] = None) -> List[Dict[str, Any]]:
    """Get labels within a time range."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM labels WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_stats() -> Dict[str, Any]:
    """Get database statistics."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM gaze_logs")
        gaze_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM tab_logs")
        tab_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM labels")
        label_count = cursor.fetchone()['count']

        cursor.execute("""
            SELECT label, COUNT(*) as count
            FROM labels
            GROUP BY label
        """)
        label_breakdown = {row['label']: row['count'] for row in cursor.fetchall()}

        return {
            'gaze_logs': gaze_count,
            'tab_logs': tab_count,
            'labels': label_count,
            'label_breakdown': label_breakdown
        }


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print("\nDatabase schema created successfully!")
    print(f"Location: {DB_PATH}")

    # Show current stats
    stats = get_stats()
    print(f"\nCurrent statistics:")
    print(f"  Gaze logs: {stats['gaze_logs']}")
    print(f"  Tab logs: {stats['tab_logs']}")
    print(f"  Labels: {stats['labels']}")
    if stats['label_breakdown']:
        print(f"  Label breakdown: {stats['label_breakdown']}")
