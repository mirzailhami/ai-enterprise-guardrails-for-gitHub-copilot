import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict

DB_PATH = os.getenv('DB_PATH', 'audit.db')

def init_db():
    """Create audit table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audits
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pr_id TEXT,
                  timestamp TEXT,
                  violations_count INTEGER,
                  action TEXT,
                  resolution TEXT DEFAULT 'pending')''')
    conn.commit()
    conn.close()
    print(f"Audit DB initialized at {DB_PATH}")

init_db()

def log(pr_id: str, violations: List[Dict], action: str, resolution: str = 'pending'):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO audits (pr_id, timestamp, violations_count, action, resolution) VALUES (?, ?, ?, ?, ?)",
              (pr_id, datetime.now().isoformat(), len(violations), action, resolution))
    conn.commit()
    conn.close()
    print(f"Audit logged for PR {pr_id}: {len(violations)} violations, action: {action}")