import sqlite3
import csv
from datetime import datetime

# Define file and DB locations
DB_FILE = "../wms_normalized.db"
PRODUCTS_CSV = "products.csv"
CUSTOMERS_CSV = "customers.csv"
ORDERS_CSV = "orders.csv"


def format_date(date_str):
    """Helper to convert MM/DD/YYYY to database-friendly YYYY-MM-DD."""
    if not date_str or date_str in ["0/00/0000", "00/00/0000"]:
        return None
    try:
        # some dates may have timestamps; split to get just the date portion
        clean_date = date_str.split()[0]
        dt = datetime.strptime(clean_date, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def migrate_data():
    # 1. Connect to SQLite and apply the new 3NF schema structure
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("--- Step 1: Initializing Schema ---")
    # Read your schema.sql file and execute it
    with open("schema.sql", "r", encoding="utf-8") as schema_file:
        schema_script = schema_file.read()
        cursor.executescript(schema_script)
    print("Database tables created successfully from schema.sql.")

    # Enable foreign keys explicitly for this connection session
    cursor.execute("PRAGMA foreign_keys = ON;")

    print("--- Step 2A: Seeding Lookup Tables (Brands & Categories) ---")

    # We will use temporary sets to gather unique lookup data out of products.csv
    unique_brands = set()
    unique_categories = set()
    unique_sub_categories = set()  # Stores tuple pairs: (category_name, sub_category_name)

    # Read products.csv to isolate the structural hierarchies
    with open(PRODUCTS_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            unique_brands.add(row['brand'].strip())
            unique_categories.add(row['category'].strip())
            unique_sub_categories.add((row['category'].strip(), row['sub_category'].strip()))

    # Insert unique Brands into the brands table
    for brand in unique_brands:
        cursor.execute("INSERT OR IGNORE INTO brands (brand_name) VALUES (?);", (brand,))

    # Insert unique Categories into the categories table
    for cat in unique_categories:
        cursor.execute("INSERT OR IGNORE INTO categories (category_name) VALUES (?);", (cat,))

    conn.commit()  # Save progress to look up auto-generated IDs next

    # Insert unique Sub-Categories by looking up their parent category_id
    for cat_name, sub_cat_name in unique_sub_categories:
        cursor.execute("SELECT category_id FROM categories WHERE category_name = ?;", (cat_name,))
        cat_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT OR IGNORE INTO sub_categories (category_id, sub_category_name) VALUES (?, ?);",
            (cat_id, sub_cat_name)
        )

    conn.commit()
    print("Successfully seeded all lookup configurations.")

    print("\n--- Step 2B: Migrating Products & Inventory Status ---")

    # Keep track of standard product prices to use when rebuilding historical order receipts
    product_price_map = {}

    with open(PRODUCTS_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            p_id = int(row['id'])
            b_name = row['brand'].strip()
            sub_cat_name = row['sub_category'].strip()
            price = float(row['price'])

            # Map item price for order resolution later
            product_price_map[p_id] = price

            # Retrieve relational integer IDs from our lookup tables
            cursor.execute("SELECT brand_id FROM brands WHERE brand_name = ?;", (b_name,))
            brand_id = cursor.fetchone()[0]

            cursor.execute("SELECT sub_category_id FROM sub_categories WHERE sub_category_name = ?;", (sub_cat_name,))
            sub_cat_id = cursor.fetchone()[0]

            # Populate the clean, static 3NF 'products' profile card
            cursor.execute(
                """INSERT INTO products (product_id, brand_id, sub_category_id, product_name, sub_type, unit) 
                   VALUES (?, ?, ?, ?, ?, ?);""",
                (p_id, brand_id, sub_cat_id, row['name'].strip(), row['sub_type'].strip(), row['unit'].strip())
            )

            # Parse inventory dynamic tracking attributes into the detached log table
            clean_restock_date = format_date(row['restock_date'])
            cursor.execute(
                """INSERT INTO inventory_status (product_id, quantity_on_hand, quantity_incoming, expected_restock_date) 
                   VALUES (?, ?, ?, ?);""",
                (p_id, int(row['inventory']), int(row['incoming']), clean_restock_date)
            )

    conn.commit()
    print("Successfully migrated products catalog and operational inventory layers.")

    print("\n--- Step 2C: Migrating Customers, Orders, and Order Items ---")

    # 1. Populate Customers Table directly
    with open(CUSTOMERS_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute(
                """INSERT INTO customers (account_number, customer_name, credit_limit, unpaid_balance, last_payment_date) 
                   VALUES (?, ?, ?, ?, ?);""",
                (int(row['account_number']), row['customer_name'].strip(),
                 float(row['credit_limit']), float(row['unpaid_balance']), format_date(row['last_payment_date']))
            )

    # 2. Extract Invoice Header Details and Line Item Details
    unique_invoices = set()

    with open(ORDERS_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        orders_rows = list(reader)  # Cache rows to iterate over safely twice

        # Build Invoice Headers first
        for row in orders_rows:
            inv_num = int(row['invoice_number'])
            if inv_num not in unique_invoices:
                unique_invoices.add(inv_num)
                cursor.execute(
                    "INSERT INTO orders (invoice_number, account_number, order_date) VALUES (?, ?, ?);",
                    (inv_num, int(row['account_number']), format_date(row['date']))
                )

        # Build Individual Order Items without storing redundant line totals
        for row in orders_rows:
            inv_num = int(row['invoice_number'])
            p_id = int(row['product_id'])
            qty = float(row['quantity'])

            # Look up base baseline catalog price captured during setup
            historical_price = product_price_map.get(p_id, 0.0)

            cursor.execute(
                """INSERT INTO order_items (invoice_number, product_id, quantity, price_at_sale) 
                   VALUES (?, ?, ?, ?);""",
                (inv_num, p_id, qty, historical_price)
            )

    conn.commit()
    print("Successfully parsed operational invoices, ledger balances, and line items!")

    # Close out the connection cleanly
    conn.close()
    print("\nMigration Completed Successfully! Your database is fully 3NF normalized.")


if __name__ == "__main__":
    migrate_data()