import sqlite3
import os
import appdirs

# Determine the user's application data folder
APP_NAME = 'FinanceLogger'
DB_PATH = os.path.join(appdirs.user_data_dir(APP_NAME), 'finance.db')

def get_connection():
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Create tables (no user_id, no users table)
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            subcategory TEXT,
            date TEXT NOT NULL,
            description TEXT,
            payment_method TEXT,
            tags TEXT,
            is_recurring INTEGER DEFAULT 0,
            deal_id INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            monthly_limit REAL NOT NULL,
            UNIQUE(category)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            original_price REAL,
            deal_price REAL,
            amount_saved REAL,
            store TEXT,
            category TEXT,
            url_or_notes TEXT,
            status TEXT DEFAULT 'active',
            expiry_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            target_date TEXT,
            category TEXT,
            color TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            institution TEXT,
            account_type TEXT,
            balance REAL DEFAULT 0,
            interest_rate_pa REAL DEFAULT 0,
            notes TEXT,
            color TEXT,
            is_liquid INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

def seed_demo_data():
    # Optional: add some demo data if the database is empty
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count FROM transactions")
    if c.fetchone()['count'] == 0:
        # Insert sample data here if you like
        pass
    conn.close()
