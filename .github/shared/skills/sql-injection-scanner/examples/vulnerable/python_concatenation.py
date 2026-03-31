"""
VULNERABLE: Python String Concatenation - SQL Injection
========================================================
This code demonstrates the MOST COMMON SQL injection vulnerability in Python.

NEVER concatenate user input into SQL queries!
"""

import sqlite3

def get_user_vulnerable(user_id):
    """
    ❌ CRITICAL VULNERABILITY: String concatenation
    
    An attacker can inject malicious SQL by passing:
    user_id = "1 OR 1=1; DROP TABLE users; --"
    
    Resulting query:
    SELECT * FROM users WHERE id = 1 OR 1=1; DROP TABLE users; --
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # UNSAFE: Direct string concatenation
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    
    return cursor.fetchone()


def search_products_vulnerable(keyword):
    """
    ❌ HIGH VULNERABILITY: F-string interpolation
    
    An attacker can inject by passing:
    keyword = "'; DELETE FROM products; --"
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # UNSAFE: F-string with user input
    query = f"SELECT * FROM products WHERE name LIKE '%{keyword}%'"
    cursor.execute(query)
    
    return cursor.fetchall()


def authenticate_vulnerable(username, password):
    """
    ❌ CRITICAL VULNERABILITY: Form input concatenation
    
    Classic SQL injection attack:
    username = "admin' --"
    password = "(anything)"
    
    Resulting query bypasses password check:
    SELECT * FROM users WHERE username = 'admin' --' AND password = '...'
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # UNSAFE: Concatenating form inputs
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    cursor.execute(query)
    
    return cursor.fetchone()


def dynamic_table_vulnerable(table_name):
    """
    ❌ HIGH VULNERABILITY: .format() method
    
    Allows table/column name injection:
    table_name = "users; DROP TABLE sessions; --"
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # UNSAFE: Using .format()
    query = "SELECT * FROM {}".format(table_name)
    cursor.execute(query)
    
    return cursor.fetchall()
