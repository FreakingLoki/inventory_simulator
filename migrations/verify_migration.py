import sqlite3
import csv

DB_FILE = "../wms_normalized.db"
PRODUCTS_CSV = "products.csv"
CUSTOMERS_CSV = "customers.csv"
ORDERS_CSV = "orders.csv"


def run_verification():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    print("=== STARTING DATA VALIDATION ===\n")

    # ---------------------------------------------------------
    # TEST 1: Record Counts
    # ---------------------------------------------------------
    print("Checking Record Counts...")

    # Count rows in CSVs
    with open(PRODUCTS_CSV, 'r', encoding='utf-8') as f:
        csv_prod_count = sum(1 for row in csv.DictReader(f))
    with open(CUSTOMERS_CSV, 'r', encoding='utf-8') as f:
        csv_cust_count = sum(1 for row in csv.DictReader(f))
    with open(ORDERS_CSV, 'r', encoding='utf-8') as f:
        csv_order_items_count = sum(1 for row in csv.DictReader(f))

    # Count rows in DB
    db_prod_count = cursor.execute("SELECT COUNT(*) FROM products;").fetchone()[0]
    db_cust_count = cursor.execute("SELECT COUNT(*) FROM customers;").fetchone()[0]
    db_items_count = cursor.execute("SELECT COUNT(*) FROM order_items;").fetchone()[0]

    print(
        f"  Products:  CSV = {csv_prod_count} | DB = {db_prod_count} -> {'PASS' if csv_prod_count == db_prod_count else 'FAIL'}")
    print(
        f"  Customers: CSV = {csv_cust_count} | DB = {db_cust_count} -> {'PASS' if csv_cust_count == db_cust_count else 'FAIL'}")
    print(
        f"  Order Lines: CSV = {csv_order_items_count} | DB = {db_items_count} -> {'PASS' if csv_order_items_count == db_items_count else 'FAIL'}")

    # ---------------------------------------------------------
    # TEST 2: Inventory Log Integrity
    # ---------------------------------------------------------
    print("\nChecking Inventory Metrics...")

    with open(PRODUCTS_CSV, 'r', encoding='utf-8') as f:
        csv_total_stock = sum(int(row['inventory']) for row in csv.DictReader(f))

    db_total_stock = cursor.execute("SELECT SUM(quantity_on_hand) FROM inventory_status;").fetchone()[0]

    print(
        f"  Total Stock: CSV = {csv_total_stock} | DB = {db_total_stock} -> {'PASS' if csv_total_stock == db_total_stock else 'FAIL'}")

    # ---------------------------------------------------------
    # TEST 3: Relational Join Integrity (The Ultimate Test)
    # ---------------------------------------------------------
    print("\nTesting Relational Database Reconstruction...")
    print("Rebuilding product names via JOINs to see if data maps correctly...")

    # This query forces SQLite to jump across all 4 product/category tables to find an item
    sample_query = """
        SELECT b.brand_name, c.category_name, p.product_name, p.sub_type, i.quantity_on_hand
        FROM products p
        JOIN brands b ON p.brand_id = b.brand_id
        JOIN sub_categories sc ON p.sub_category_id = sc.sub_category_id
        JOIN categories c ON sc.category_id = c.category_id
        JOIN inventory_status i ON p.product_id = i.product_id
        LIMIT 3;
    """
    cursor.execute(sample_query)
    sample_rows = cursor.fetchall()

    print("  Sample Query Output (First 3 Items):")
    for row in sample_rows:
        print(f"    - Brand: {row[0]} | Cat: {row[1]} | Name: {row[2]} ({row[3]}) | Stock: {row[4]}")

    conn.close()
    print("\n=== VALIDATION COMPLETE ===")


if __name__ == "__main__":
    run_verification()