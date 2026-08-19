import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'finance')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add user_id column to all data tables
    tables = ['transactions', 'budgets', 'deals', 'goals', 'accounts']
    for table in tables:
        c.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in c.fetchall()]
        if 'user_id' not in columns:
            c.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")
    
    # Create default admin user if no users exist
    c.execute("SELECT COUNT(*) as count FROM users")
    if c.fetchone()['count'] == 0:
        # In production, use hashed passwords. For simplicity, we'll store plaintext
        # but we'll switch to werkzeug.security in server.py.
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                  ('admin', 'admin123'))
        c.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = c.fetchone()['id']
        # Assign existing rows to admin
        for table in tables:
            c.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (admin_id,))
    
    conn.commit()
    conn.close()

def seed_demo_data():
    # Demo data seeding is now per-user, we'll handle it via a separate endpoint.
    pass
