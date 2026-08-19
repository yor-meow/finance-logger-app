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
        # 1. Try X-Session-Token header (from localStorage method)
        token = self.headers.get('X-Session-Token')
        if token:
            return sessions.get(token)
        
        # 2. Fallback to cookie (for backward compatibility)
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
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

    # ---- Existing handlers (unchanged, but all use require_auth) ----
    # ... (keep all handle_* methods exactly as in your current file) ...

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

        token = str(uuid.uuid4())
        sessions[token] = row['id']

        # Return token in JSON (frontend stores in localStorage)
        self.send_json({'success': True, 'message': 'Login successful', 'token': token})

    def handle_logout(self):
        # Remove token from session store
        token = self.headers.get('X-Session-Token') or self.headers.get('Cookie', '').split('session_token=')[-1].split(';')[0] if 'session_token=' in self.headers.get('Cookie', '') else None
        if token and token in sessions:
            del sessions[token]
        self.send_json({'success': True, 'message': 'Logged out'})

    # ---- All other handlers unchanged (they use require_auth) ----
    # ... (keep the existing handle_* methods exactly as in your file) ...

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
