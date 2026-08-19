import urllib.request
import json
import time
import subprocess
import sys
import os

def test_api():
    print("Testing BouncyFinance backend...")
    from database import init_db, seed_demo_data, get_connection
    init_db()
    seed_demo_data()
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count FROM transactions")
    tx_count = c.fetchone()['count']
    c.execute("SELECT COUNT(*) as count FROM deals")
    deals_count = c.fetchone()['count']
    c.execute("SELECT COUNT(*) as count FROM budgets")
    budgets_count = c.fetchone()['count']
    c.execute("SELECT COUNT(*) as count FROM accounts")
    accounts_count = c.fetchone()['count']
    conn.close()

    print(f"[OK] DB Check: {tx_count} transactions, {deals_count} deals, {budgets_count} budgets, {accounts_count} accounts seeded.")
    assert tx_count > 0, "No transactions found"
    assert deals_count > 0, "No deals found"
    assert budgets_count > 0, "No budgets found"
    assert accounts_count > 0, "No accounts found"
    print("[SUCCESS] All backend DB tests passed successfully!")

if __name__ == '__main__':
    test_api()
