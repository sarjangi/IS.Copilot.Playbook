/*
 * Vulnerable C# code with SQL injection - FOR TESTING ONLY
 * DO NOT USE IN PRODUCTION
 */
using System;
using System.Data.SqlClient;
using Microsoft.AspNetCore.Mvc;

namespace VulnerableApp
{
    public class UserController : Controller
    {
        private readonly string connectionString = "Server=localhost;Database=MyApp;";

        // UNSAFE - String interpolation vulnerability
        public IActionResult GetUserById(int userId)
        {
            using (SqlConnection conn = new SqlConnection(connectionString))
            {
                conn.Open();
                
                // HIGH: String interpolation - SQL Injection vulnerability
                string query = $"SELECT * FROM Users WHERE Id = {userId}";
                SqlCommand cmd = new SqlCommand(query, conn);
                
                SqlDataReader reader = cmd.ExecuteReader();
                // Process results...
                return Ok();
            }
        }

        // UNSAFE - String concatenation vulnerability
        public IActionResult SearchUsers(string searchTerm)
        {
            using (SqlConnection conn = new SqlConnection(connectionString))
            {
                conn.Open();
                
                // HIGH: String concatenation - SQL Injection vulnerability
                string query = "SELECT * FROM Users WHERE Name LIKE '%" + searchTerm + "%'";
                SqlCommand cmd = new SqlCommand(query, conn);
                
                SqlDataReader reader = cmd.ExecuteReader();
                return Ok();
            }
        }

        // UNSAFE - User input concatenation
        [HttpPost]
        public IActionResult Login([FromForm] string username, [FromForm] string password)
        {
            using (SqlConnection conn = new SqlConnection(connectionString))
            {
                conn.Open();
                
                // CRITICAL: Direct user input concatenation - SQL Injection vulnerability
                string query = "SELECT * FROM Users WHERE Username = '" + username + 
                              "' AND Password = '" + password + "'";
                SqlCommand cmd = new SqlCommand(query, conn);
                
                SqlDataReader reader = cmd.ExecuteReader();
                if (reader.Read())
                {
                    return Ok(new { success = true });
                }
                return Unauthorized();
            }
        }

        // UNSAFE - String.Format vulnerability
        public IActionResult GetRecordsByTable(string tableName, int recordId)
        {
            using (SqlConnection conn = new SqlConnection(connectionString))
            {
                conn.Open();
                
                // HIGH: String.Format - SQL Injection vulnerability
                string query = String.Format("SELECT * FROM {0} WHERE Id = {1}", tableName, recordId);
                SqlCommand cmd = new SqlCommand(query, conn);
                
                SqlDataReader reader = cmd.ExecuteReader();
                return Ok();
            }
        }
    }
}
