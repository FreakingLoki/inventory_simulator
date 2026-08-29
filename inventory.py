import sqlite3

DB_FILE = 'wms_normalized.db'


def get_stock_level(product_id):
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute("SELECT quantity_on_hand FROM inventory_status WHERE product_id = ?", (product_id,))
        item = cursor.fetchone()
        return item['quantity_on_hand'] if item else None
    except sqlite3.Error as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()


def get_restock_info(product_id):
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute("SELECT quantity_incoming, expected_restock_date FROM inventory_status WHERE product_id = ?",
                       (product_id,))
        item = cursor.fetchone()
        return (item['quantity_incoming'], item['expected_restock_date']) if item else (None, None)
    except sqlite3.Error as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()


def display_inventory_list(only_heroes=True):
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        query = """
            SELECT p.product_id as id, c.category_name as category, 
                   b.brand_name as brand, p.product_name as name, p.sub_type 
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN categories c ON p.sub_category_id IN (SELECT sub_category_id FROM sub_categories WHERE category_id = c.category_id)
            JOIN sub_categories sc ON p.sub_category_id = sc.sub_category_id
        """
        if only_heroes:
            query += " WHERE sc.sub_category_name = 'Hero'"

        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"\n{'ID':<7} | {'Category':<10} | {'Brand':<15} | {'Name':<30} | {'Sub-Type'}")
        print("-" * 80)
        for row in rows:
            print(
                f"{row['id']:<7} | {row['category']:<10} | {row['brand']:<15} | {row['name']:<30} | {row['sub_type']}")
    except sqlite3.Error as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()


def receive_po():
    product_id = input("\nEnter Product ID to receive: ").strip()
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT quantity_incoming, expected_restock_date FROM inventory_status WHERE product_id = ?",
                       (product_id,))
        result = cursor.fetchone()

        if not result:
            print(f"[!] Product ID {product_id} not found in inventory.")
            return

        incoming, restock_date = result
        if incoming <= 0:
            print(f"[-] No incoming stock expected for Product {product_id}.")
            return

        print(f"Expected Delivery: {incoming} units (Scheduled for {restock_date}).")

        try:
            received_qty = int(input(f"Enter quantity received (Expected: {incoming}): "))

            if received_qty > 0:
                if received_qty < incoming:
                    cursor.execute("""
                        UPDATE inventory_status 
                        SET quantity_on_hand = quantity_on_hand + ?,
                            quantity_incoming = quantity_incoming - ?
                        WHERE product_id = ?
                    """, (received_qty, received_qty, product_id))
                    print(
                        f"[SUCCESS] Partial delivery of {received_qty} received. {incoming - received_qty} still on backorder.")
                else:
                    cursor.execute("""
                        UPDATE inventory_status 
                        SET quantity_on_hand = quantity_on_hand + ?,
                            quantity_incoming = 0,
                            expected_restock_date = NULL
                        WHERE product_id = ?
                    """, (received_qty, product_id))
                    print(f"[SUCCESS] Shipment fully received! {received_qty} units added.")
                connection.commit()
            else:
                print("Receiving cancelled or invalid amount.")
        except ValueError:
            print("Invalid input. Must be a whole number.")

    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        connection.close()


def cycle_count():
    product_id = input("\nEnter Product ID to audit: ").strip()
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT quantity_on_hand FROM inventory_status WHERE product_id = ?", (product_id,))
        result = cursor.fetchone()

        if not result:
            print(f"[!] Product ID {product_id} not found.")
            return

        current_stock = result[0]
        print(f"System shows {current_stock} units on hand.")

        try:
            new_stock = int(input("Enter actual physical count: "))
            if new_stock != current_stock:
                cursor.execute("UPDATE inventory_status SET quantity_on_hand = ? WHERE product_id = ?",
                               (new_stock, product_id))
                connection.commit()
                print(f"[SUCCESS] Inventory adjusted by {new_stock - current_stock} units. New total: {new_stock}")
            else:
                print("Count matches system. No adjustment needed.")
        except ValueError:
            print("Invalid input. Must be a whole number.")

    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        connection.close()


def inventory_management_menu():
    while True:
        print(f"\n --- Inventory Management ---")
        print("01: Receive Incoming PO (Dock Delivery)")
        print("02: Cycle Count (Manual Adjustment)")
        print("03: Return to Main Menu")

        choice = input("\nEnter Selection: ")
        match choice:
            case '01':
                receive_po()
            case '02':
                cycle_count()
            case '03':
                break
            case _:
                print("Invalid selection.")