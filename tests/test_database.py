"""
Simple database connectivity test using direct psycopg2 connection.
Tests Supabase PostgreSQL connection without Django dependencies.
"""

import pytest
import os
import psycopg2
from dotenv import load_dotenv


def test_database_connection():
    """Test direct database connection using psycopg2"""
    print("\n=== Testing Direct Database Connection ===")

    # Load environment variables
    load_dotenv()

    # Get DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    print(f"DATABASE_URL configured: {'Yes' if database_url else 'No'}")

    if not database_url:
        pytest.fail("DATABASE_URL not found in environment variables")

    # Hide password in output
    safe_url = database_url.replace(database_url.split(":")[2].split("@")[0], "****")
    print(f"Database URL: {safe_url}")

    # Test connection
    try:
        conn = psycopg2.connect(database_url)
        print("✅ Successfully connected to database!")

        # Test basic query
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 as test_value")
            result = cursor.fetchone()
            print(f"Test query result: {result}")
            assert result[0] == 1, "Basic query failed"

        conn.close()
        print("✅ Database connection test passed!")

    except psycopg2.Error as e:
        pytest.fail(f"Database connection failed: {e}")


def test_database_info():
    """Get database information using direct connection"""
    print("\n=== Testing Database Information ===")

    # Load environment variables
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        pytest.skip("DATABASE_URL not configured")

    try:
        conn = psycopg2.connect(database_url)

        with conn.cursor() as cursor:
            # Get database version
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"PostgreSQL version: {version}")

            # Get current database name
            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()[0]
            print(f"Current database: {db_name}")

            # Get current user
            cursor.execute("SELECT current_user")
            user = cursor.fetchone()[0]
            print(f"Connected as user: {user}")

        conn.close()

        assert "PostgreSQL" in version, "Not connected to PostgreSQL"
        print("✅ Database information retrieved successfully!")

    except psycopg2.Error as e:
        pytest.fail(f"Database info query failed: {e}")
