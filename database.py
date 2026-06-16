import sqlite3
import os

# We store the database file in the same master directory we made earlier
DB_FILE = "/var/paas/state.db"

def init_cluster_db():
    """Creates the tracking table for worker nodes and their hardware metrics."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table to act as our central Metrics Collector & Health Monitor
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
    """Creates the tracking tables if they don't exist."""
    # Ensure the directory exists before connecting
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create a table to track all our deployed containers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS containers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT UNIQUE NOT NULL,
            repo_url TEXT NOT NULL,
            internal_port INTEGER,
            container_pid INTEGER,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    
    # Automatically initialize the cluster metrics table at the same time
    init_cluster_db()

def register_app(app_name: str, repo_url: str):
    """Logs a new app into the system when the user hits /deploy."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO containers (app_name, repo_url, status) VALUES (?, ?, ?)", 
        (app_name, repo_url, "BUILDING")
    )
    conn.commit()
    conn.close()

def update_app_state(app_name: str, status: str, port: int = None, pid: int = None):
    """Updates the app when the Linux container successfully spins up or crashes."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if port and pid:
        cursor.execute(
            "UPDATE containers SET status=?, internal_port=?, container_pid=? WHERE app_name=?", 
            (status, port, pid, app_name)
        )
    else:
        cursor.execute(
            "UPDATE containers SET status=? WHERE app_name=?", 
            (status, app_name)
        )
        
    conn.commit()
    conn.close()

def update_worker_metrics(worker_id: str, cpu: float, ram: float, status: str):
    """Upserts the latest health check and metrics from a worker node."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # INSERT OR REPLACE ensures we just update the existing worker's row
    cursor.execute('''
        INSERT OR REPLACE INTO workers (worker_id, cpu_load, ram_usage, status, last_heartbeat)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (worker_id, cpu, ram, status))
    
    conn.commit()
    conn.close()
