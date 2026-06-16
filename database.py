import sqlite3
import os

# We store the database file in the same master directory we made earlier
DB_FILE = "/var/paas/state.db"

def init_db():
    """Creates the tracking table if it doesn't exist."""
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
