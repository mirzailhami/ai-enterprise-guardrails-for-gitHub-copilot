import sqlite3
import os
from datetime import datetime
from typing import List, Dict

DB_PATH = os.getenv('DB_PATH', 'audit.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audits
                 (pr_id TEXT, timestamp TEXT, violations_count INTEGER, action TEXT, resolution TEXT)''')
    conn.commit()
    conn.close()

def log(pr_id: str, violations: List[Dict], action: str, resolution: str = 'pending'):
    init_db()  # Ensures table exists
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO audits VALUES (?, ?, ?, ?, ?)",
              (pr_id, datetime.now().isoformat(), len(violations), action, resolution))
    conn.commit()
    conn.close()