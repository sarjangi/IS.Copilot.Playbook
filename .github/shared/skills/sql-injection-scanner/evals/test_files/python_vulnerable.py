"""
Vulnerable Python code with SQL injection - FOR TESTING ONLY
DO NOT USE IN PRODUCTION
"""
import sqlite3
from flask import request

def get_user_by_id_vulnerable(user_id):
    """UNSAFE - String concatenation vulnerability"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # CRITICAL: Direct string concatenation - SQL Injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result

def search_users_vulnerable(search_term):
    """UNSAFE - F-string vulnerability"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # HIGH: F-string interpolation - SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE name LIKE '%{search_term}%'"
    cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    return results

def login_vulnerable():
    """UNSAFE - Request parameter concatenation"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # CRITICAL: User input directly concatenated - SQL Injection vulnerability
    query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    cursor.execute(query)
    
    user = cursor.fetchone()
    conn.close()
    return user

def get_records_by_table_vulnerable(table_name, record_id):
    """UNSAFE - String format vulnerability"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # HIGH: .format() method - SQL Injection vulnerability
    query = "SELECT * FROM {} WHERE id = {}".format(table_name, record_id)
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    return result
