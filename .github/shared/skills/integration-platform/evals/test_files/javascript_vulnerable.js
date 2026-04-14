/**
 * Vulnerable JavaScript code with SQL injection - FOR TESTING ONLY
 * DO NOT USE IN PRODUCTION
 */
const mysql = require('mysql');
const express = require('express');

// Create database connection
const connection = mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: 'password',
  database: 'myapp'
});

// UNSAFE - Template literal vulnerability
function getUserByIdVulnerable(userId) {
  // CRITICAL: Template literal with user input - SQL Injection vulnerability
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  
  connection.query(query, (error, results) => {
    if (error) throw error;
    return results;
  });
}

// UNSAFE - String concatenation vulnerability
function searchUsersVulnerable(searchTerm) {
  // HIGH: String concatenation - SQL Injection vulnerability
  const query = "SELECT * FROM users WHERE name LIKE '%" + searchTerm + "%'";
  
  connection.query(query, (error, results) => {
    if (error) throw error;
    return results;
  });
}

// UNSAFE - Express route with SQL injection
const app = express();
app.get('/user/:id', (req, res) => {
  const userId = req.params.id;
  
  // CRITICAL: User input from URL parameter - SQL Injection vulnerability
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).send('Database error');
    } else {
      res.json(results);
    }
  });
});

// UNSAFE - POST login with concatenation
app.post('/login', (req, res) => {
  const { username, password } = req.body;
  
  // CRITICAL: Direct concatenation of user credentials - SQL Injection vulnerability
  const query = "SELECT * FROM users WHERE username = '" + username + 
                "' AND password = '" + password + "'";
  
  connection.query(query, (error, results) => {
    if (error) {
      res.status(500).send('Login failed');
    } else if (results.length > 0) {
      res.json({ success: true, user: results[0] });
    } else {
      res.status(401).send('Invalid credentials');
    }
  });
});

module.exports = { getUserByIdVulnerable, searchUsersVulnerable };
