import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'finance.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Transactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT,
        date TEXT NOT NULL,
        description TEXT,
        payment_method TEXT DEFAULT 'Cash',
        tags TEXT,
        is_recurring INTEGER DEFAULT 0,
        deal_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. Budgets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE NOT NULL,
        monthly_limit REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 3. Deals & Discounts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        original_price REAL NOT NULL,
        deal_price REAL NOT NULL,
        amount_saved REAL NOT NULL,
        store TEXT,
        category TEXT,
        url_or_notes TEXT,
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'purchased', 'expired', 'wishlist')),
        expiry_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 4. Savings Goals table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL DEFAULT 0,
        target_date TEXT,
        category TEXT,
        color TEXT DEFAULT '#3b82f6',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 5. Bank Accounts & On-Hand Cash table (with Per Annum interest rate)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        institution TEXT NOT NULL,
        account_type TEXT NOT NULL DEFAULT 'Savings',
        balance REAL NOT NULL DEFAULT 0,
        interest_rate_pa REAL DEFAULT 0.0,
        notes TEXT,
        color TEXT DEFAULT '#3b82f6',
        is_liquid INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

def seed_demo_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as count FROM transactions')
    if cursor.fetchone()['count'] > 0:
        conn.close()
        return False

    current_month_prefix = datetime.now().strftime('%Y-%m')

    # Sample Budgets (in Philippine Peso ₱)
    sample_budgets = [
        ('Food & Dining', 8000.0),
        ('Groceries', 12000.0),
        ('Housing & Utilities', 18000.0),
        ('Entertainment & Leisure', 4000.0),
        ('Shopping & Deals', 6000.0),
        ('Transportation', 3500.0),
        ('Health & Fitness', 2500.0),
        ('Subscriptions', 1500.0)
    ]
    cursor.executemany('INSERT OR IGNORE INTO budgets (category, monthly_limit) VALUES (?, ?)', sample_budgets)

    # Sample Deals (in Philippine Peso ₱)
    sample_deals = [
        ('50% Off Wireless Noise-Cancelling Headphones', 4999.00, 2499.00, 2500.00, 'Shopee Mall', 'Shopping & Deals', 'Shopee Voucher: TECH50', 'purchased', f'{current_month_prefix}-28'),
        ('Supermarket Payday Weekend Flash Sale', 3500.00, 2600.00, 900.00, 'SM Supermarket', 'Groceries', 'Buy 2 Get 1 Free Promo', 'purchased', f'{current_month_prefix}-20'),
        ('Steam Summer Game Bundle Sale', 2800.00, 890.00, 1910.00, 'Steam PH', 'Entertainment & Leisure', '70% off publisher bundle', 'purchased', f'{current_month_prefix}-25'),
        ('Gym Annual Pass Promo (Save ₱3,000)', 15000.00, 12000.00, 3000.00, 'Anytime Fitness', 'Health & Fitness', 'Early bird renewal discount', 'active', f'{current_month_prefix}-30'),
        ('Ultra-Wide 27-inch Monitor Deal Alert', 14999.00, 9999.00, 5000.00, 'Lazada LazMall', 'Shopping & Deals', 'Mega Sale Voucher Alert', 'wishlist', f'{current_month_prefix}-31')
    ]
    cursor.executemany('''
    INSERT INTO deals (title, original_price, deal_price, amount_saved, store, category, url_or_notes, status, expiry_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_deals)

    # Sample Transactions (in Philippine Peso ₱)
    sample_txs = [
        ('income', 65000.00, 'Salary', 'Main Job', f'{current_month_prefix}-01', 'Monthly Salary Payroll', 'Bank Transfer', 'income,salary,work', 1, None),
        ('income', 12500.00, 'Freelance', 'Side Project', f'{current_month_prefix}-10', 'Web Design Project for Client', 'GCash', 'side-hustle,freelance', 0, None),
        ('expense', 15000.00, 'Housing & Utilities', 'Rent', f'{current_month_prefix}-02', 'Condo Monthly Rent', 'Bank Transfer', 'rent,fixed', 1, None),
        ('expense', 3200.00, 'Housing & Utilities', 'Meralco Electricity & Water', f'{current_month_prefix}-05', 'Utility Bills', 'Maya', 'utilities,bills', 1, None),
        ('expense', 2600.00, 'Groceries', 'Supermarket', f'{current_month_prefix}-06', 'Weekly Groceries (Deals saved ₱900)', 'Credit Card', 'food,groceries,deal-saved', 0, 2),
        ('expense', 2499.00, 'Shopping & Deals', 'Shopee Gadgets', f'{current_month_prefix}-08', 'Headphones Flash Sale (Saved ₱2,500)', 'GCash', 'gadgets,discount', 0, 1),
        ('expense', 850.00, 'Food & Dining', 'Restaurants', f'{current_month_prefix}-09', 'Dinner with friends', 'Debit Card', 'dining,social', 0, None),
        ('expense', 1800.00, 'Transportation', 'Gas / Fuel', f'{current_month_prefix}-11', 'Car Refuel', 'Credit Card', 'commute,gas', 0, None),
        ('expense', 890.00, 'Entertainment & Leisure', 'Gaming', f'{current_month_prefix}-12', 'Steam Game Bundle (Saved ₱1,910)', 'Maya', 'gaming,deals', 0, 3),
        ('expense', 549.00, 'Subscriptions', 'Streaming', f'{current_month_prefix}-14', 'Netflix Premium Plan', 'Credit Card', 'streaming,monthly', 1, None),
        ('expense', 1650.00, 'Groceries', 'Market Run', f'{current_month_prefix}-15', 'Fresh market fruits & meats', 'Cash', 'groceries', 0, None),
        ('expense', 380.00, 'Food & Dining', 'Cafe', f'{current_month_prefix}-16', 'Coffee & Pastry', 'GCash', 'coffee,lunch', 0, None)
    ]
    cursor.executemany('''
    INSERT INTO transactions (type, amount, category, subcategory, date, description, payment_method, tags, is_recurring, deal_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_txs)

    # Sample Goals (in Philippine Peso ₱)
    sample_goals = [
        ('Emergency Fund (6 Months)', 150000.00, 85000.00, '2026-12-31', 'Savings', '#10b981'),
        ('Japan Vacation Trip', 60000.00, 32000.00, '2026-11-15', 'Travel', '#6366f1'),
        ('New M3 MacBook / Laptop Upgrade', 75000.00, 42000.00, '2026-10-01', 'Tech', '#f59e0b')
    ]
    cursor.executemany('''
    INSERT INTO goals (title, target_amount, current_amount, target_date, category, color)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', sample_goals)

    # Sample Bank Accounts & On-Hand Funds (Philippine Banks with % p.a. interest)
    sample_accounts = [
        ('BDO Payroll & Checking', 'BDO Unibank', 'Checking', 32500.00, 0.05, 'Primary payroll & bills checking account', '#3b82f6', 1),
        ('Maya High-Yield Savings', 'Maya Bank', 'High-Yield Savings', 85000.00, 6.00, 'Emergency fund earning 6.0% p.a. interest', '#10b981', 1),
        ('SeaBank / GoTyme Vault', 'SeaBank PH', 'Digital Bank', 45000.00, 4.50, 'Daily savings vault earning 4.5% p.a.', '#8b5cf6', 1),
        ('GCash Wallet', 'GCash', 'Digital Bank', 12450.00, 0.00, 'Everyday cashless QR payments & transfers', '#06b6d4', 1),
        ('Cash in Wallet & Home Drawer', 'Physical Cash', 'Cash On-Hand', 3800.00, 0.00, 'Physical peso banknotes on-hand', '#f59e0b', 1),
        ('BPI Time Deposit (1 Year)', 'BPI (Bank of the Philippine Islands)', 'Time Deposit (CD)', 50000.00, 5.25, '1-Year Fixed lock-in at 5.25% p.a.', '#ec4899', 0)
    ]
    cursor.executemany('''
    INSERT INTO accounts (name, institution, account_type, balance, interest_rate_pa, notes, color, is_liquid)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_accounts)

    conn.commit()
    conn.close()
    return True
