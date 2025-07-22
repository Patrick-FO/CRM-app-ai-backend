import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), 
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def test_connection():
    """Test database connection"""
    try:
        conn = get_db_connection()
        conn.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False