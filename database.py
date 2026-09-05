import os
import sys
import sqlite3
import pandas as pd
from migrations import migrate

DB_FILE = 'wms_normalized.db'


def initialize_local_database():
    # auto-install on first launch
    if not os.path.exists(DB_FILE):
        print("First launch detected. Building and populating the warehouse database...")
        migrate.migrate_data()
        print("Warehouse database built successfully!")

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        # Ensure the payments table exists
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_number INTEGER,
                        payment_amount REAL,
                        payment_date TEXT
                    )
                """)
        connection.commit()

        # pandas rulebook initialization
        if os.path.exists('requirements.csv'):
            requirements_df = pd.read_csv('requirements.csv')
            requirements_df.to_sql('requirements', connection, if_exists='replace', index=False)

        if os.path.exists('category_rules.csv'):
            rules_df = pd.read_csv('category_rules.csv')
            rules_df.to_sql('rules', connection, if_exists='replace', index=False)
    except Exception as e:
        print(f"Rules initialization error:\n{e}")
    finally:
        if connection:
            connection.close()


def check_setup():
    print("--- Environment Check ---")
    if sys.prefix != sys.base_prefix:
        print("Virtual Environment: Active")
    else:
        print("Running in Global Python")

    if os.path.exists(DB_FILE):
        print(f"{DB_FILE}: Found\nVerifying integrity of database...")
        connection = None
        try:
            connection = sqlite3.connect(DB_FILE)
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['brands', 'categories', 'sub_categories', 'products',
                               'inventory_status', 'customers', 'orders', 'order_items']

            if all(table in tables for table in expected_tables):
                print("Database: All core normalized tables found\nDatabase Integrity: Good")
                return True
            else:
                missing = [table for table in expected_tables if table not in tables]
                print(f"Database: Missing tables\n{missing}")
                return False
        except sqlite3.Error as e:
            print(f"Database verification error:\n{e}")
            return False
        finally:
            if connection:
                connection.close()
    else:
        print(f"{DB_FILE}: Not found. Please run migrate.py first.")
        return False