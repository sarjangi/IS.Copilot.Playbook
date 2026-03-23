"""
SAFE: Python Parameterized Queries - SQL Injection Prevention
==============================================================
This code demonstrates the CORRECT way to prevent SQL injection in Python.

ALWAYS use parameterized queries or ORMs!
"""

import sqlite3
from sqlalchemy.orm import Session
from models import User, Product  # Assuming SQLAlchemy models

def get_user_safe(user_id):
    """
    ✅ SAFE: Using parameterized query with ? placeholder
    
    The database driver properly escapes the parameter,
    preventing SQL injection regardless of input.
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # SAFE: Parameterized query
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    
    return cursor.fetchone()


def search_products_safe(keyword):
    """
    ✅ SAFE: Using parameterized query for LIKE searches
    
    The wildcard % is included in the parameter value,
    not in the SQL string itself.
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # SAFE: Parameter handles the keyword safely
    query = "SELECT * FROM products WHERE name LIKE ?"
    cursor.execute(query, (f'%{keyword}%',))
    
    return cursor.fetchall()


def authenticate_safe(username, password):
    """
    ✅ SAFE: Using named parameters
    
    Named parameters (:username, :password) provide the same
    protection as positional parameters but are more readable.
    """
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # SAFE: Named parameters
    query = "SELECT * FROM users WHERE username = :username AND password = :password"
    cursor.execute(query, {"username": username, "password": password})
    
    return cursor.fetchone()


def get_user_sqlalchemy_safe(user_id):
    """
    ✅ SAFE: Using SQLAlchemy ORM
    
    ORMs automatically use parameterized queries under the hood.
    This is the recommended approach for complex applications.
    """
    session = Session()
    
    # SAFE: ORM handles parameterization automatically
    user = session.query(User).filter(User.id == user_id).first()
    
    session.close()
    return user


def search_products_orm_safe(keyword):
    """
    ✅ SAFE: Using ORM with LIKE
    
    Even complex queries are safe when using an ORM.
    """
    session = Session()
    
    # SAFE: ORM with LIKE operator
    products = session.query(Product).filter(
        Product.name.like(f'%{keyword}%')
    ).all()
    
    session.close()
    return products


# Note: For dynamic table/column names (which can't be parameterized),
# use an allowlist approach:
ALLOWED_TABLES = ['users', 'products', 'orders']

def query_table_safe(table_name):
    """
    ✅ SAFE: Using allowlist for dynamic identifiers
    
    Table and column names cannot be parameterized, so validate
    against a known list of allowed values.
    """
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name}")
    
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # SAFE: Validated against allowlist before use
    query = f"SELECT * FROM {table_name}"
    cursor.execute(query)
    
    return cursor.fetchall()
