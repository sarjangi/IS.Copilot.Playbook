"""
Safe Python code with parameterized queries - TESTING EXAMPLE
"""
import sqlite3
from flask import request

def get_user_by_id_safe(user_id):
    """SAFE - Using parameterized query with placeholder"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # SAFE: Parameterized query with ? placeholder
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result

def search_users_safe(search_term):
    """SAFE - Using parameterized query for LIKE"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # SAFE: Parameterized query with proper escaping
    query = "SELECT * FROM users WHERE name LIKE ?"
    cursor.execute(query, (f'%{search_term}%',))
    
    results = cursor.fetchall()
    conn.close()
    return results

def login_safe():
    """SAFE - Using parameterized query with named placeholders"""
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # SAFE: Named placeholders
    query = "SELECT * FROM users WHERE username = :username AND password = :password"
    cursor.execute(query, {"username": username, "password": password})
    
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_email_orm(email):
    """SAFE - Using ORM (SQLAlchemy)"""
    from sqlalchemy.orm import Session
    from models import User
    
    # SAFE: ORM automatically handles parameterization
    session = Session()
    user = session.query(User).filter(User.email == email).first()
    session.close()
    return user
