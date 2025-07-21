import os
import mysql.connector
from dotenv import load_dotenv

# ✅ Load .env
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', ''),
    'database': os.getenv('DB_NAME', 'receipt_db')
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
        raise Exception("Connection not established")
    except Exception as e:
        raise Exception(f"❌ Database connection failed: {e}")


def execute_query(query, params=(), fetch=True, return_last_id=False):
    """
    Execute SQL query.
    - fetch=True => returns results
    - return_last_id=True => returns last inserted row ID (only for INSERT)
    """
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)

        if fetch:
            results = cursor.fetchall()
        else:
            connection.commit()
            results = cursor.lastrowid if return_last_id else None

        cursor.close()
        connection.close()
        return results

    except Exception as e:
        connection.close()
        raise Exception(f"❌ Query failed: {e}")
