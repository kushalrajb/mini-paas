import sqlite3
import os

DB_FILE = "/var/paas/state.db"

def init_cluster_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            worker_id TEXT PRIMARY KEY,
            cpu_load REAL,
            ram_usage REAL,
            status TEXT,
            last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def init_db():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # NEW: We added worker_id to track WHERE the app is running
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS containers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            repo_url TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    init_cluster_db()

def register_app(app_name: str, repo_url: str, worker_id: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO containers (app_name, repo_url, worker_id, status) VALUES (?, ?, ?, ?)", 
        (app_name, repo_url, worker_id, "BUILDING")
    )
    conn.commit()
    conn.close()

def update_worker_metrics(worker_id: str, cpu: float, ram: float, status: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO workers (worker_id, cpu_load, ram_usage, status, last_heartbeat)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (worker_id, cpu, ram, status))
    conn.commit()
    conn.close()

# ==========================================
# SELF-HEALING LOGIC (NEW)
# ==========================================
def get_dead_workers():
    """Finds workers that missed their heartbeat for over 30 seconds."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT worker_id FROM workers WHERE status != 'DEAD' AND last_heartbeat < datetime('now', '-30 seconds')")
    dead = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dead

def get_and_orphan_apps(worker_id: str):
    """Marks a worker dead and extracts its apps so they can be rescheduled."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE workers SET status='DEAD' WHERE worker_id=?", (worker_id,))
    cursor.execute("SELECT app_name, repo_url FROM containers WHERE worker_id=?", (worker_id,))
    apps_to_rescue = cursor.fetchall()
    
    # Delete the old broken container records
    cursor.execute("DELETE FROM containers WHERE worker_id=?", (worker_id,))
    conn.commit()
    conn.close()
    
    return apps_to_rescue
