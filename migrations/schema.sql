-- enable foreign key support in SQLite
PRAGMA foreign_keys = ON;

-- 1. Lookup Tables
CREATE TABLE brands (
    brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name TEXT NOT NULL UNIQUE
);

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
);

CREATE TABLE sub_categories (
    sub_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    sub_category_name TEXT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id),
    UNIQUE(category_id, sub_category_name)
);

-- 2. Clean Product Profile
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    brand_id INTEGER NOT NULL,
    sub_category_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    sub_type TEXT NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id),
    FOREIGN KEY (sub_category_id) REFERENCES sub_categories(sub_category_id)
);

-- 3. Logistics & Live Data
CREATE TABLE inventory_status (
    product_id INTEGER PRIMARY KEY,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0,
    quantity_incoming INTEGER NOT NULL DEFAULT 0,
    expected_restock_date TEXT, -- SQLite handles dates as TEXT (ISO8601 strings)
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 4. Transactions
CREATE TABLE customers (
    account_number INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    credit_limit REAL NOT NULL,
    unpaid_balance REAL NOT NULL,
    last_payment_date TEXT
);

CREATE TABLE orders (
    invoice_number INTEGER PRIMARY KEY,
    account_number INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    FOREIGN KEY (account_number) REFERENCES customers(account_number)
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity REAL NOT NULL,
    price_at_sale REAL NOT NULL,
    FOREIGN KEY (invoice_number) REFERENCES orders(invoice_number),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);