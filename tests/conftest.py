import sys
import os
# Point Python to the root directory so it can find your application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import pytest
from unittest.mock import patch


@pytest.fixture
def mock_db():
    # 1. Create a temporary database in RAM
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()

    # 2. Build the core 3NF schema structure
    cursor.executescript("""
        CREATE TABLE brands (brand_id INTEGER PRIMARY KEY, brand_name TEXT);
        CREATE TABLE categories (category_id INTEGER PRIMARY KEY, category_name TEXT);
        CREATE TABLE sub_categories (sub_category_id INTEGER PRIMARY KEY, category_id INTEGER, sub_category_name TEXT);
        CREATE TABLE products (product_id INTEGER PRIMARY KEY, brand_id INTEGER, sub_category_id INTEGER, product_name TEXT, sub_type TEXT, unit TEXT, unit_price REAL);
        CREATE TABLE inventory_status (product_id INTEGER PRIMARY KEY, quantity_on_hand INTEGER, quantity_incoming INTEGER, expected_restock_date TEXT);
        CREATE TABLE customers (account_number INTEGER PRIMARY KEY, customer_name TEXT, credit_limit REAL, unpaid_balance REAL, last_payment_date TEXT);
        CREATE TABLE orders (invoice_number INTEGER PRIMARY KEY, account_number INTEGER, order_date TEXT);
        CREATE TABLE order_items (order_item_id INTEGER PRIMARY KEY, invoice_number INTEGER, product_id INTEGER, quantity REAL, price_at_sale REAL);

        -- Insert Lookup Data
        INSERT INTO brands (brand_id, brand_name) VALUES (1, 'Vertex Premium');
        INSERT INTO categories (category_id, category_name) VALUES (1, 'Siding');
        INSERT INTO sub_categories (sub_category_id, category_id, sub_category_name) VALUES (1, 1, 'Hero');

        -- Insert Mock Product & Inventory using the actual CSV baseline
        INSERT INTO products (product_id, brand_id, sub_category_id, product_name, sub_type, unit, unit_price) 
        VALUES (100001, 1, 1, 'Double-4 Siding', 'Snow White', 'Square', 252.0);

        INSERT INTO inventory_status (product_id, quantity_on_hand, quantity_incoming, expected_restock_date)
        VALUES (100001, 87, 62, '2030-04-28');
    """)
    conn.commit()

    # 3. Patch sqlite3.connect so the application modules use this memory DB instead of the real one
    with patch('sqlite3.connect', return_value=conn):
        yield conn  # Hand the database to the test

    # 4. Teardown: close and destroy the memory database after the test finishes
    conn.close()