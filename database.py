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
    
    # Create users table first
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user if no users exist
    c.execute("SELECT COUNT(*) as count FROM users")
    if c.fetchone()['count'] == 0:
        # Default admin user (password: admin123)
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", 
                  ('admin', 'admin123'))
        c.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = c.fetchone()['id']
    else:
        # Get first user's id to assign existing rows
        c.execute("SELECT id FROM users LIMIT 1")
        admin_id = c.fetchone()['id']

    # Define each table with user_id from the start
    tables = {
        'transactions': '''
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
                deal_id INTEGER,
                user_id INTEGER REFERENCES users(id)
            )
        ''',
        'budgets': '''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                user_id INTEGER REFERENCES users(id),
                UNIQUE(category, user_id)
            )
        ''',
        'deals': '''
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER REFERENCES users(id)
            )
        ''',
        'goals': '''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date TEXT,
                category TEXT,
                color TEXT,
                user_id INTEGER REFERENCES users(id)
            )
        ''',
        'accounts': '''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                institution TEXT,
                account_type TEXT,
                balance REAL DEFAULT 0,
                interest_rate_pa REAL DEFAULT 0,
                notes TEXT,
                color TEXT,
                is_liquid INTEGER DEFAULT 1,
                user_id INTEGER REFERENCES users(id)
            )
        '''
    }

    for table_name, create_sql in tables.items():
        # Check if table already exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not c.fetchone():
            # Table doesn't exist – create it with user_id
            c.execute(create_sql)
        else:
            # Table exists – check if user_id column is present
            c.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in c.fetchall()]
            if 'user_id' not in columns:
                # Add the column
                c.execute(f"ALTER TABLE {table_name} ADD COLUMN user_id INTEGER REFERENCES users(id)")
                # Assign existing rows to the admin user
                c.execute(f"UPDATE {table_name} SET user_id = ?", (admin_id,))
    
    conn.commit()
    conn.close()

def seed_demo_data():
    # You can implement per-user demo seeding later
    pass
