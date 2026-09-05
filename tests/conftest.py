import sys
import os

# Point Python to the root directory so it can find your application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import pytest
from unittest.mock import patch


@pytest.fixture
def mock_db():
    # 1. Create a shared in-memory database URI
    db_uri = 'file::memory:?cache=shared'

    # --- NEW: Save the real connect function before we patch it ---
    real_connect = sqlite3.connect

    # 2. Hold a master connection open using the REAL connect function
    master_conn = real_connect(db_uri, uri=True, check_same_thread=False)
    cursor = master_conn.cursor()

    # 3. Build the core 3NF schema structure
    cursor.executescript("""
        CREATE TABLE brands (brand_id INTEGER PRIMARY KEY, brand_name TEXT);
        CREATE TABLE categories (category_id INTEGER PRIMARY KEY, category_name TEXT);
        CREATE TABLE sub_categories (sub_category_id INTEGER PRIMARY KEY, category_id INTEGER, sub_category_name TEXT);
        CREATE TABLE products (product_id INTEGER PRIMARY KEY, brand_id INTEGER, sub_category_id INTEGER, product_name TEXT, sub_type TEXT, unit TEXT, unit_price REAL);
        CREATE TABLE inventory_status (product_id INTEGER PRIMARY KEY, quantity_on_hand INTEGER, quantity_incoming INTEGER, expected_restock_date TEXT);
        CREATE TABLE customers (account_number INTEGER PRIMARY KEY, customer_name TEXT, credit_limit REAL, unpaid_balance REAL, last_payment_date TEXT);
        CREATE TABLE orders (invoice_number INTEGER PRIMARY KEY, account_number INTEGER, order_date TEXT);
        CREATE TABLE order_items (order_item_id INTEGER PRIMARY KEY, invoice_number INTEGER, product_id INTEGER, quantity REAL, price_at_sale REAL);
        CREATE TABLE payments (payment_id INTEGER PRIMARY KEY AUTOINCREMENT, account_number INTEGER, payment_amount REAL, payment_date TEXT);

        INSERT INTO brands (brand_id, brand_name) VALUES (1, 'Vertex Premium');
        INSERT INTO categories (category_id, category_name) VALUES (1, 'Siding');
        INSERT INTO sub_categories (sub_category_id, category_id, sub_category_name) VALUES (1, 1, 'Hero');

        INSERT INTO products (product_id, brand_id, sub_category_id, product_name, sub_type, unit, unit_price) 
        VALUES (100001, 1, 1, 'Double-4 Siding', 'Snow White', 'Square', 252.0);

        INSERT INTO inventory_status (product_id, quantity_on_hand, quantity_incoming, expected_restock_date)
        VALUES (100001, 87, 62, '2030-04-28');
    """)
    master_conn.commit()

    # 4. Patch sqlite3.connect to yield a NEW connection using the REAL connect reference
    def mock_connect(*args, **kwargs):
        return real_connect(db_uri, uri=True)

    with patch('sqlite3.connect', side_effect=mock_connect):
        yield master_conn  # Hand the master connection to the tests

    # 5. Teardown: close the master connection, erasing the shared memory database
    master_conn.close()