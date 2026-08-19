import http.server
import socketserver
import json
import urllib.parse
import os
import csv
import io
import sys
import webbrowser
import uuid
from datetime import datetime
from database import get_connection, init_db, DB_PATH
from werkzeug.security import generate_password_hash, check_password_hash

PORT = 5000
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

# Session store: token -> user_id
sessions = {}

class FinanceAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    # -------------------- Helper methods --------------------
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def read_json_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            return json.loads(body)
        except Exception:
            return {}

    def get_user_id(self):
        # Parse cookies
        cookie_header = self.headers.get('Cookie')
        if not cookie_header:
            return None
        for cookie in cookie_header.split(';'):
            cookie = cookie.strip()
            if cookie.startswith('session_token='):
                token = cookie.split('=')[1]
                return sessions.get(token)
        return None

    def require_auth(self):
        user_id = self.get_user_id()
        if user_id is None:
            self.send_json({'error': 'Unauthorized'}, 401)
            return None
        return user_id

    # -------------------- OPTIONS --------------------
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Cookie')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

    # -------------------- GET handlers --------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/api/summary':
            self.handle_get_summary(query)
        elif path == '/api/transactions':
            self.handle_get_transactions(query)
        elif path == '/api/budgets':
            self.handle_get_budgets()
        elif path == '/api/deals':
            self.handle_get_deals(query)
        elif path == '/api/goals':
            self.handle_get_goals()
        elif path == '/api/accounts':
            self.handle_get_accounts()
        elif path == '/api/export/csv':
            self.handle_export_csv()
        elif path == '/api/export/json':
            self.handle_export_json()
        elif path == '/api/me':
            self.handle_get_current_user()
        elif path.startswith('/api/'):
            self.send_json({'error': 'Endpoint not found'}, 404)
        else:
            if path == '/':
                self.path = '/index.html'
            super().do_GET()

    def handle_get_summary(self, query):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        month = query.get('month', [None])[0]

        month_filter = ''
        params = [user_id]
        if month:
            month_filter = "AND strftime('%Y-%m', date) = ?"
            params.append(month)

        cursor.execute(f'''
            SELECT type, SUM(amount) as total 
            FROM transactions 
            WHERE user_id = ? {month_filter}
            GROUP BY type
        ''', params)
        rows = cursor.fetchall()
        
        income = 0.0
        expense = 0.0
        for r in rows:
            if r['type'] == 'income':
                income = r['total'] or 0.0
            elif r['type'] == 'expense':
                expense = r['total'] or 0.0

        net_balance = income - expense
        savings_rate = ((income - expense) / income * 100) if income > 0 else 0.0

        # Total savings from Deals (this user)
        cursor.execute('SELECT SUM(amount_saved) as total_saved FROM deals WHERE user_id = ? AND status IN ("purchased", "active")', (user_id,))
        deal_savings_row = cursor.fetchone()
        deal_savings = deal_savings_row['total_saved'] or 0.0

        # Accounts
        cursor.execute('SELECT * FROM accounts WHERE user_id = ? ORDER BY balance DESC', (user_id,))
        accounts_rows = [dict(r) for r in cursor.fetchall()]
        total_on_hand = sum(a['balance'] for a in accounts_rows)
        total_annual_interest = sum((a['balance'] * (a.get('interest_rate_pa', 0) / 100.0)) for a in accounts_rows)
        total_monthly_interest = total_annual_interest / 12.0

        # Category breakdown for expenses
        cat_filter = f"AND strftime('%Y-%m', date) = ?" if month else ""
        cursor.execute(f'''
            SELECT category, SUM(amount) as total 
            FROM transactions 
            WHERE user_id = ? AND type = 'expense' {cat_filter}
            GROUP BY category 
            ORDER BY total DESC
        ''', params if month else [user_id])
        category_breakdown = [{'category': r['category'], 'total': r['total']} for r in cursor.fetchall()]

        # Monthly Trends
        cursor.execute('''
            SELECT 
                strftime('%Y-%m', date) as month,
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
            FROM transactions
            WHERE user_id = ?
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month ASC
            LIMIT 12
        ''', (user_id,))
        monthly_trends = [{'month': r['month'], 'income': r['income'] or 0.0, 'expense': r['expense'] or 0.0} for r in cursor.fetchall()]

        # Recent transactions
        cursor.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 5', (user_id,))
        recent_txs = [dict(r) for r in cursor.fetchall()]

        conn.close()
        self.send_json({
            'total_income': round(income, 2),
            'total_expense': round(expense, 2),
            'net_balance': round(net_balance, 2),
            'savings_rate': round(savings_rate, 1),
            'deal_savings': round(deal_savings, 2),
            'total_on_hand': round(total_on_hand, 2),
            'total_annual_interest': round(total_annual_interest, 2),
            'total_monthly_interest': round(total_monthly_interest, 2),
            'accounts': accounts_rows,
            'category_breakdown': category_breakdown,
            'monthly_trends': monthly_trends,
            'recent_transactions': recent_txs
        })

    def handle_get_transactions(self, query):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT t.*, d.title as deal_title FROM transactions t LEFT JOIN deals d ON t.deal_id = d.id WHERE t.user_id = ?"
        params = [user_id]

        if 'type' in query and query['type'][0]:
            sql += " AND t.type = ?"
            params.append(query['type'][0])
        if 'category' in query and query['category'][0]:
            sql += " AND t.category = ?"
            params.append(query['category'][0])
        if 'search' in query and query['search'][0]:
            search = f"%{query['search'][0]}%"
            sql += " AND (t.description LIKE ? OR t.category LIKE ? OR t.tags LIKE ?)"
            params.extend([search, search, search])

        sql += " ORDER BY t.date DESC, t.id DESC"
        cursor.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json({'transactions': rows})

    def handle_get_budgets(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        current_month = datetime.now().strftime('%Y-%m')

        cursor.execute('SELECT * FROM budgets WHERE user_id = ? ORDER BY category ASC', (user_id,))
        budgets = [dict(r) for r in cursor.fetchall()]

        for b in budgets:
            cursor.execute('''
                SELECT SUM(amount) as spent 
                FROM transactions 
                WHERE user_id = ? AND type = 'expense' AND category = ? AND strftime('%Y-%m', date) = ?
            ''', (user_id, b['category'], current_month))
            row = cursor.fetchone()
            spent = row['spent'] or 0.0
            b['spent'] = round(spent, 2)
            b['remaining'] = round(b['monthly_limit'] - spent, 2)
            b['percentage'] = round((spent / b['monthly_limit'] * 100), 1) if b['monthly_limit'] > 0 else 0

        conn.close()
        self.send_json({'budgets': budgets, 'current_month': current_month})

    def handle_get_deals(self, query):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        status = query.get('status', [None])[0]
        if status:
            cursor.execute('SELECT * FROM deals WHERE user_id = ? AND status = ? ORDER BY created_at DESC', (user_id, status))
        else:
            cursor.execute('SELECT * FROM deals WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        deals = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json({'deals': deals})

    def handle_get_goals(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM goals WHERE user_id = ? ORDER BY target_date ASC, id ASC', (user_id,))
        goals = [dict(r) for r in cursor.fetchall()]
        conn.close()
        self.send_json({'goals': goals})

    def handle_get_accounts(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE user_id = ? ORDER BY balance DESC, id ASC', (user_id,))
        accounts = [dict(r) for r in cursor.fetchall()]
        for acc in accounts:
            rate = acc.get('interest_rate_pa') or 0.0
            bal = acc.get('balance') or 0.0
            acc['annual_interest'] = round(bal * (rate / 100.0), 2)
            acc['monthly_interest'] = round((bal * (rate / 100.0)) / 12.0, 2)
        conn.close()
        self.send_json({'accounts': accounts})

    def handle_get_current_user(self):
        user_id = self.get_user_id()
        if user_id is None:
            self.send_json({'error': 'Not logged in'}, 401)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            self.send_json(dict(user))
        else:
            self.send_json({'error': 'User not found'}, 404)

    # -------------------- POST handlers --------------------
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/register':
            self.handle_register()
        elif path == '/api/login':
            self.handle_login()
        elif path == '/api/logout':
            self.handle_logout()
        elif path == '/api/transactions':
            self.handle_create_transaction()
        elif path == '/api/budgets':
            self.handle_create_or_update_budget()
        elif path == '/api/deals':
            self.handle_create_deal()
        elif path == '/api/goals':
            self.handle_create_goal()
        elif path == '/api/accounts':
            self.handle_create_account()
        elif path == '/api/seed':
            self.handle_seed_demo()
        elif path == '/api/import/json':
            self.handle_import_json()
        elif path == '/api/reset':
            self.handle_reset_db()
        else:
            self.send_json({'error': 'Endpoint not found'}, 404)

    def handle_register(self):
        data = self.read_json_body()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            self.send_json({'error': 'Username and password required'}, 400)
            return
        if len(password) < 4:
            self.send_json({'error': 'Password must be at least 4 characters'}, 400)
            return

        conn = get_connection()
        cursor = conn.cursor()
        # Check if username exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            self.send_json({'error': 'Username already taken'}, 400)
            return

        hashed = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hashed))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'User registered successfully'})

    def handle_login(self):
        data = self.read_json_body()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            self.send_json({'error': 'Username and password required'}, 400)
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        if not row or not check_password_hash(row['password_hash'], password):
            self.send_json({'error': 'Invalid username or password'}, 401)
            return

        # Create session token
        token = str(uuid.uuid4())
        sessions[token] = row['id']

        # Send cookie
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Set-Cookie', f'session_token={token}; Path=/; HttpOnly')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True, 'message': 'Login successful'}).encode('utf-8'))

    def handle_logout(self):
        token = self.headers.get('Cookie', '').split('session_token=')[-1].split(';')[0] if 'session_token=' in self.headers.get('Cookie', '') else None
        if token in sessions:
            del sessions[token]
        self.send_json({'success': True, 'message': 'Logged out'})

    def handle_seed_demo(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        # Seed demo data for this user only (you can adapt)
        from database import seed_demo_data  # but we'll implement a simpler version
        # For now, just respond with a note
        self.send_json({'success': True, 'message': 'Demo seeding not implemented per user yet'})

    # -------------------- PUT handlers --------------------
    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        user_id = self.require_auth()
        if user_id is None:
            return

        if path.startswith('/api/transactions/'):
            tx_id = path.split('/')[-1]
            self.handle_update_transaction(tx_id, user_id)
        elif path.startswith('/api/deals/'):
            deal_id = path.split('/')[-1]
            self.handle_update_deal(deal_id, user_id)
        elif path.startswith('/api/goals/'):
            goal_id = path.split('/')[-1]
            self.handle_update_goal(goal_id, user_id)
        elif path.startswith('/api/accounts/'):
            acc_id = path.split('/')[-1]
            self.handle_update_account(acc_id, user_id)
        else:
            self.send_json({'error': 'Endpoint not found'}, 404)

    # -------------------- DELETE handlers --------------------
    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        user_id = self.require_auth()
        if user_id is None:
            return

        if path.startswith('/api/transactions/'):
            tx_id = path.split('/')[-1]
            self.handle_delete_transaction(tx_id, user_id)
        elif path.startswith('/api/budgets/'):
            b_id = path.split('/')[-1]
            self.handle_delete_budget(b_id, user_id)
        elif path.startswith('/api/deals/'):
            deal_id = path.split('/')[-1]
            self.handle_delete_deal(deal_id, user_id)
        elif path.startswith('/api/goals/'):
            goal_id = path.split('/')[-1]
            self.handle_delete_goal(goal_id, user_id)
        elif path.startswith('/api/accounts/'):
            acc_id = path.split('/')[-1]
            self.handle_delete_account(acc_id, user_id)
        else:
            self.send_json({'error': 'Endpoint not found'}, 404)

    # ---- CRUD helpers with user_id ----
    def handle_create_transaction(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        data = self.read_json_body()
        tx_type = data.get('type', 'expense')
        amount = float(data.get('amount', 0))
        category = data.get('category', 'General')
        subcategory = data.get('subcategory', '')
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        description = data.get('description', '')
        payment_method = data.get('payment_method', 'Cash')
        tags = data.get('tags', '')
        is_recurring = 1 if data.get('is_recurring') else 0
        deal_id = data.get('deal_id') or None

        if amount <= 0:
            self.send_json({'error': 'Amount must be greater than 0'}, 400)
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (type, amount, category, subcategory, date, description, payment_method, tags, is_recurring, deal_id, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tx_type, amount, category, subcategory, date, description, payment_method, tags, is_recurring, deal_id, user_id))
        tx_id = cursor.lastrowid
        if deal_id:
            cursor.execute("UPDATE deals SET status = 'purchased' WHERE id = ? AND user_id = ?", (deal_id, user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'id': tx_id, 'message': 'Transaction added'})

    def handle_update_transaction(self, tx_id, user_id):
        data = self.read_json_body()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transactions 
            SET type = ?, amount = ?, category = ?, subcategory = ?, date = ?, description = ?, payment_method = ?, tags = ?, is_recurring = ?, deal_id = ?
            WHERE id = ? AND user_id = ?
        ''', (
            data.get('type', 'expense'),
            float(data.get('amount', 0)),
            data.get('category', 'General'),
            data.get('subcategory', ''),
            data.get('date', datetime.now().strftime('%Y-%m-%d')),
            data.get('description', ''),
            data.get('payment_method', 'Cash'),
            data.get('tags', ''),
            1 if data.get('is_recurring') else 0,
            data.get('deal_id') or None,
            tx_id,
            user_id
        ))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Transaction updated'})

    def handle_delete_transaction(self, tx_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Transaction deleted'})

    # ---- Budgets ----
    def handle_create_or_update_budget(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        data = self.read_json_body()
        category = data.get('category')
        limit = float(data.get('monthly_limit', 0))
        if not category or limit <= 0:
            self.send_json({'error': 'Valid category and limit > 0 required'}, 400)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO budgets (category, monthly_limit, user_id)
            VALUES (?, ?, ?)
            ON CONFLICT(category, user_id) DO UPDATE SET monthly_limit = excluded.monthly_limit
        ''', (category, limit, user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Budget saved'})

    def handle_delete_budget(self, b_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM budgets WHERE id = ? AND user_id = ?', (b_id, user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Budget deleted'})

    # ---- Deals ----
    def handle_create_deal(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        data = self.read_json_body()
        title = data.get('title')
        orig = float(data.get('original_price', 0))
        deal = float(data.get('deal_price', 0))
        saved = float(data.get('amount_saved', max(0, orig - deal)))
        store = data.get('store', '')
        cat = data.get('category', 'Shopping & Deals')
        notes = data.get('url_or_notes', '')
        status = data.get('status', 'active')
        expiry = data.get('expiry_date', '')
        if not title or orig <= 0:
            self.send_json({'error': 'Title and original price required'}, 400)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO deals (title, original_price, deal_price, amount_saved, store, category, url_or_notes, status, expiry_date, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, orig, deal, saved, store, cat, notes, status, expiry, user_id))
        deal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'id': deal_id, 'message': 'Deal tracked'})

    def handle_update_deal(self, deal_id, user_id):
        data = self.read_json_body()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE deals 
            SET title = ?, original_price = ?, deal_price = ?, amount_saved = ?, store = ?, category = ?, url_or_notes = ?, status = ?, expiry_date = ?
            WHERE id = ? AND user_id = ?
        ''', (
            data.get('title'),
            float(data.get('original_price', 0)),
            float(data.get('deal_price', 0)),
            float(data.get('amount_saved', 0)),
            data.get('store', ''),
            data.get('category', ''),
            data.get('url_or_notes', ''),
            data.get('status', 'active'),
            data.get('expiry_date', ''),
            deal_id,
            user_id
        ))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Deal updated'})

    def handle_delete_deal(self, deal_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM deals WHERE id = ? AND user_id = ?', (deal_id, user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Deal removed'})

    # ---- Goals ----
    def handle_create_goal(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        data = self.read_json_body()
        title = data.get('title')
        target = float(data.get('target_amount', 0))
        current = float(data.get('current_amount', 0))
        target_date = data.get('target_date', '')
        category = data.get('category', 'Savings')
        color = data.get('color', '#3b82f6')
        if not title or target <= 0:
            self.send_json({'error': 'Title and valid target amount required'}, 400)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO goals (title, target_amount, current_amount, target_date, category, color, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, target, current, target_date, category, color, user_id))
        goal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'id': goal_id, 'message': 'Goal created'})

    def handle_update_goal(self, goal_id, user_id):
        data = self.read_json_body()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE goals 
            SET title = ?, target_amount = ?, current_amount = ?, target_date = ?, category = ?, color = ?
            WHERE id = ? AND user_id = ?
        ''', (
            data.get('title'),
            float(data.get('target_amount', 0)),
            float(data.get('current_amount', 0)),
            data.get('target_date', ''),
            data.get('category', 'Savings'),
            data.get('color', '#3b82f6'),
            goal_id,
            user_id
        ))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Goal updated'})

    def handle_delete_goal(self, goal_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM goals WHERE id = ? AND user_id = ?', (goal_id, user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Goal removed'})

    # ---- Accounts ----
    def handle_create_account(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        data = self.read_json_body()
        name = data.get('name')
        inst = data.get('institution', 'Bank')
        acc_type = data.get('account_type', 'Savings')
        balance = float(data.get('balance', 0))
        rate_pa = float(data.get('interest_rate_pa', 0))
        notes = data.get('notes', '')
        color = data.get('color', '#3b82f6')
        is_liquid = 1 if data.get('is_liquid', True) else 0
        if not name:
            self.send_json({'error': 'Account name required'}, 400)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO accounts (name, institution, account_type, balance, interest_rate_pa, notes, color, is_liquid, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, inst, acc_type, balance, rate_pa, notes, color, is_liquid, user_id))
        acc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'id': acc_id, 'message': 'Account saved'})

    def handle_update_account(self, acc_id, user_id):
        data = self.read_json_body()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE accounts 
            SET name = ?, institution = ?, account_type = ?, balance = ?, interest_rate_pa = ?, notes = ?, color = ?, is_liquid = ?
            WHERE id = ? AND user_id = ?
        ''', (
            data.get('name'),
            data.get('institution', 'Bank'),
            data.get('account_type', 'Savings'),
            float(data.get('balance', 0)),
            float(data.get('interest_rate_pa', 0)),
            data.get('notes', ''),
            data.get('color', '#3b82f6'),
            1 if data.get('is_liquid', True) else 0,
            acc_id,
            user_id
        ))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Account updated'})

    def handle_delete_account(self, acc_id, user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM accounts WHERE id = ? AND user_id = ?', (acc_id, user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Account deleted'})

    # ---- Export/Import ----
    def handle_export_csv(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC', (user_id,))
        rows = cursor.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Type', 'Amount', 'Category', 'Subcategory', 'Date', 'Description', 'Payment Method', 'Tags', 'Recurring'])
        for r in rows:
            writer.writerow([r['id'], r['type'], r['amount'], r['category'], r['subcategory'], r['date'], r['description'], r['payment_method'], r['tags'], r['is_recurring']])

        csv_data = output.getvalue()
        self.send_response(200)
        self.send_header('Content-Type', 'text/csv')
        self.send_header('Content-Disposition', 'attachment; filename="finance_transactions.csv"')
        self.end_headers()
        self.wfile.write(csv_data.encode('utf-8'))

    def handle_export_json(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE user_id = ?', (user_id,))
        transactions = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM budgets WHERE user_id = ?', (user_id,))
        budgets = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM deals WHERE user_id = ?', (user_id,))
        deals = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM goals WHERE user_id = ?', (user_id,))
        goals = [dict(r) for r in cursor.fetchall()]
        cursor.execute('SELECT * FROM accounts WHERE user_id = ?', (user_id,))
        accounts = [dict(r) for r in cursor.fetchall()]
        conn.close()

        backup = {
            'exported_at': datetime.now().isoformat(),
            'transactions': transactions,
            'budgets': budgets,
            'deals': deals,
            'goals': goals,
            'accounts': accounts
        }
        self.send_json(backup)

    def handle_import_json(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        data = self.read_json_body()
        conn = get_connection()
        cursor = conn.cursor()
        # Delete existing user data
        cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM budgets WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM deals WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM goals WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM accounts WHERE user_id = ?', (user_id,))

        # Insert with new user_id
        for t in data.get('transactions', []):
            cursor.execute('''
                INSERT INTO transactions (type, amount, category, subcategory, date, description, payment_method, tags, is_recurring, deal_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (t.get('type'), t.get('amount'), t.get('category'), t.get('subcategory'), t.get('date'), t.get('description'), t.get('payment_method'), t.get('tags'), t.get('is_recurring'), t.get('deal_id'), user_id))
        for b in data.get('budgets', []):
            cursor.execute('INSERT INTO budgets (category, monthly_limit, user_id) VALUES (?, ?, ?)', (b.get('category'), b.get('monthly_limit'), user_id))
        for d in data.get('deals', []):
            cursor.execute('''
                INSERT INTO deals (title, original_price, deal_price, amount_saved, store, category, url_or_notes, status, expiry_date, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (d.get('title'), d.get('original_price'), d.get('deal_price'), d.get('amount_saved'), d.get('store'), d.get('category'), d.get('url_or_notes'), d.get('status'), d.get('expiry_date'), user_id))
        for g in data.get('goals', []):
            cursor.execute('''
                INSERT INTO goals (title, target_amount, current_amount, target_date, category, color, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (g.get('title'), g.get('target_amount'), g.get('current_amount'), g.get('target_date'), g.get('category'), g.get('color'), user_id))
        for a in data.get('accounts', []):
            cursor.execute('''
                INSERT INTO accounts (name, institution, account_type, balance, interest_rate_pa, notes, color, is_liquid, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (a.get('name'), a.get('institution'), a.get('account_type'), a.get('balance'), a.get('interest_rate_pa'), a.get('notes'), a.get('color'), a.get('is_liquid', 1), user_id))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Data imported successfully'})

    def handle_reset_db(self):
        user_id = self.require_auth()
        if user_id is None:
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM budgets WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM deals WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM goals WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM accounts WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        self.send_json({'success': True, 'message': 'Your data has been reset'})

# -------------------- Server runner --------------------
def run(port=None, open_browser=True):
    init_db()
    if port is None:
        port = int(os.environ.get('PORT', 5000))
    
    server_address = ('0.0.0.0', port)
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    try:
        httpd = ReusableTCPServer(server_address, FinanceAPIHandler)
        print("=======================================================")
        print(" BouncyFinance Logger & Deals Tracker is Running!")
        print(f" Access URL: http://0.0.0.0:{port}")
        print(" Press Ctrl+C to stop.")
        print("=======================================================\n")
        if open_browser:
            webbrowser.open(f"http://localhost:{port}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == '__main__':
    open_b = '--no-browser' not in sys.argv
    run(open_browser=open_b)
