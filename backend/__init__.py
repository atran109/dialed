"""Backend package for the Dialed study-session distraction classifier."""

from .database import (
    init_db,
    insert_gaze_log,
    insert_tab_log,
    insert_label,
    get_gaze_logs,
    get_tab_logs,
    get_labels,
    get_stats,
    DB_PATH
)

__all__ = [
    'init_db',
    'insert_gaze_log',
    'insert_tab_log',
    'insert_label',
    'get_gaze_logs',
    'get_tab_logs',
    'get_labels',
    'get_stats',
    'DB_PATH'
]
