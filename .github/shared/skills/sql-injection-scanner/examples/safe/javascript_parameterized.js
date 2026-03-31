/**
 * SAFE: JavaScript Parameterized Queries - SQL Injection Prevention
 * ==================================================================
 * ALWAYS use parameterized queries, query builders, or ORMs!
 */

const mysql = require('mysql');
const knex = require('knex');

const connection = mysql.createConnection({
  host: 'localhost',
  user: 'dbuser',
  password: 'dbpass',
  database: 'myapp'
});

/**
 * ✅ SAFE: Using parameterized query with ? placeholder
 * 
 * The mysql library automatically escapes parameters.
 */
function getUserSafe(userId) {
  const query = 'SELECT * FROM users WHERE id = ?';
  
  connection.query(query, [userId], (error, results) => {
    if (error) throw error;
    console.log(results);
  });
}

/**
 * ✅ SAFE: Multiple parameters with array
 */
function searchProductsSafe(keyword, category) {
  const query = 'SELECT * FROM products WHERE name LIKE ? AND category = ?';
  const params = [`%${keyword}%`, category];
  
  connection.query(query, params, (error, results) => {
    if (error) throw error;
    console.log(results);
  });
}

/**
 * ✅ SAFE: Express route with parameterized query
 */
const express = require('express');
const app = express();

app.get('/user/:id', (req, res) => {
  const userId = req.params.id;
  const query = 'SELECT * FROM users WHERE id = ?';
  
  connection.query(query, [userId], (error, results) => {
    if (error) return res.status(500).send('Error');
    res.json(results);
  });
});

/**
 * ✅ SAFE: Using Knex query builder
 * 
 * Query builders automatically use parameterized queries.
 */
const db = knex({
  client: 'mysql',
  connection: {
    host: 'localhost',
    user: 'dbuser',
    password: 'dbpass',
    database: 'myapp'
  }
});

async function getUserKnexSafe(userId) {
  // SAFE: Knex handles parameterization
  const user = await db('users')
    .where('id', userId)
    .first();
  
  return user;
}

async function searchProductsKnexSafe(keyword) {
  // SAFE: Even with LIKE, Knex parameterizes correctly
  const products = await db('products')
    .where('name', 'like', `%${keyword}%`)
    .select('*');
  
  return products;
}

/**
 * ✅ SAFE: Using Sequelize ORM
 */
const { Sequelize, DataTypes } = require('sequelize');
const sequelize = new Sequelize('myapp', 'dbuser', 'dbpass', {
  host: 'localhost',
  dialect: 'mysql'
});

const User = sequelize.define('User', {
  id: { type: DataTypes.INTEGER, primaryKey: true },
  username: DataTypes.STRING,
  email: DataTypes.STRING
});

async function getUserSequelizeSafe(userId) {
  // SAFE: ORM handles everything
  const user = await User.findByPk(userId);
  return user;
}

async function searchUsersSequelizeSafe(keyword) {
  // SAFE: ORMs use parameterized queries internally
  const users = await User.findAll({
    where: {
      username: {
        [Sequelize.Op.like]: `%${keyword}%`
      }
    }
  });
  return users;
}

module.exports = { 
  getUserSafe, 
  searchProductsSafe,
  getUserKnexSafe,
  getUserSequelizeSafe
};
