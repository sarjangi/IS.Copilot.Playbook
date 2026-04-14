/**
 * VULNERABLE: JavaScript Template Literals - SQL Injection
 * ==========================================================
 * NEVER use template literals or string concatenation for SQL queries!
 */

const mysql = require('mysql');

const connection = mysql.createConnection({
  host: 'localhost',
  user: 'dbuser',
  password: 'dbpass',
  database: 'myapp'
});

/**
 * ❌ CRITICAL: Template literal with user input
 * 
 * Attack: userId = "1 OR 1=1"
 * Result: Returns all users
 */
function getUserVulnerable(userId) {
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  
  connection.query(query, (error, results) => {
    if (error) throw error;
    console.log(results);
  });
}

/**
 * ❌ HIGH: String concatenation
 * 
 * Attack: keyword = "'; DROP TABLE users; --"
 */
function searchProductsVulnerable(keyword) {
  const query = "SELECT * FROM products WHERE name LIKE '%" + keyword + "%'";
  
  connection.query(query, (error, results) => {
    if (error) throw error;
    console.log(results);
  });
}

/**
 * ❌ CRITICAL: Express route with SQL injection
 * 
 * Attack: GET /user/1%20OR%201=1
 */
const express = require('express');
const app = express();

app.get('/user/:id', (req, res) => {
  const userId = req.params.id;
  
  const query = `SELECT * FROM users WHERE id = ${userId}`;
  
  connection.query(query, (error, results) => {
    if (error) return res.status(500).send('Error');
    res.json(results);
  });
});

module.exports = { getUserVulnerable, searchProductsVulnerable };
