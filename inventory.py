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

            freight_bill = float(input("Enter total outside carrier freight cost for this shipment: $") or 0)

            if freight_bill > 0:
                freight_per_unit = freight_bill / received_qty

                # update the moving average freight cost in the products table
                cursor.execute("""
                    UPDATE products
                    SET avg_freight_cost = ((avg_freight_cost + ?) / 2)
                    WHERE product_id = ?
                    """, (freight_per_unit, product_id))
                connection.commit()

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

def add_product():
    """adds a new product within an existing brand, category, and sub-category"""
    print("\n--- Add New Product ---")
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        # 1. Brand Resolution
        brand_name = input("Enter Brand Name to search: ").strip()
        cursor.execute("SELECT brand_id FROM brands WHERE LOWER(brand_name) = LOWER(?)", (brand_name,))
        brand_res = cursor.fetchone()

        if brand_res:
            brand_id = brand_res[0]
            print(f"  -> Found Brand ID: {brand_id}")
        else:
            print(f"  -> Brand '{brand_name}' not found. Diverting to creation module...")
            brand_id = add_brand()
            if not brand_id: return

        # 2. Category Resolution
        cat_name = input("\nEnter Category Name to search (e.g. Siding, Roofing): ").strip()
        cursor.execute("SELECT category_id FROM categories WHERE LOWER(category_name) = LOWER(?)", (cat_name,))
        cat_res = cursor.fetchone()

        if cat_res:
            cat_id = cat_res[0]
            print(f"  -> Found Category ID: {cat_id}")
        else:
            print(f"  -> Category '{cat_name}' not found. Diverting to creation module...")
            cat_id = add_category()
            if not cat_id: return

        # 3. Sub-Category Resolution
        sub_name = input("\nEnter Sub-Category Name to search (e.g. Hero, J-Channel): ").strip()
        cursor.execute("""
                SELECT sub_category_id FROM sub_categories 
                WHERE LOWER(sub_category_name) = LOWER(?) AND category_id = ?
            """, (sub_name, cat_id))
        sub_res = cursor.fetchone()

        if sub_res:
            sub_id = sub_res[0]
            print(f"  -> Found Sub-Category ID: {sub_id}")
        else:
            print(f"  -> Sub-Category '{sub_name}' not found under this category. Diverting to creation module...")
            sub_id = add_sub_category(cat_id)
            if not sub_id: return

        # 4. Product Details Entry
        print("\n--- Enter Product Details ---")
        product_name = input("Product Name (e.g. Double-4 Siding): ").strip()
        sub_type = input("Sub-Type (e.g. Snow White, R-13, Type X): ").strip()
        unit = input("Unit of Measure (e.g. Square, PC, Bag): ").strip()

        try:
            unit_price = float(input("Unit Price: $"))
            qty_on_hand = int(input("Initial Quantity on Hand: "))
            qty_incoming = int(input("Incoming Quantity: "))
        except ValueError:
            print("[!] Invalid numeric entry. Aborting product creation.")
            return

        restock_date = input("Expected Restock Date (YYYY-MM-DD) or press Enter to skip: ").strip()
        if not restock_date:
            restock_date = None

        # 5. Generate Safe Product ID and Insert
        cursor.execute("SELECT MAX(product_id) FROM products")
        max_id = cursor.fetchone()[0]
        new_product_id = (max_id + 1) if max_id else 100001

        cursor.execute("""
                INSERT INTO products (product_id, brand_id, sub_category_id, product_name, sub_type, unit, unit_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_product_id, brand_id, sub_id, product_name, sub_type, unit, unit_price))

        # Detached logistical tracking insert
        cursor.execute("""
                INSERT INTO inventory_status (product_id, quantity_on_hand, quantity_incoming, expected_restock_date)
                VALUES (?, ?, ?, ?)
            """, (new_product_id, qty_on_hand, qty_incoming, restock_date))

        connection.commit()
        print(f"\n[SUCCESS] '{product_name} ({sub_type})' successfully added as Catalog ID #{new_product_id}.")

    except sqlite3.Error as e:
        if connection:
            connection.rollback()
        print(f"Database Error: Transaction rolled back to prevent corruption.\n{e}")
    finally:
        if connection:
            connection.close()


def add_brand():
    """adds a new brand with appropriate categories and sub-categories"""
    print("\n--- Add New Brand ---")
    new_brand = input("Enter the new brand name: ").strip()

    if not new_brand:
        print("[!] Brand name cannot be empty.")
        return None

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        # Check if the brand already exists (case-insensitive)
        cursor.execute("SELECT brand_id, brand_name FROM brands WHERE LOWER(brand_name) = LOWER(?)", (new_brand,))
        existing = cursor.fetchone()

        if existing:
            print(f"[!] The brand '{existing[1]}' already exists (ID: {existing[0]}).")
            return existing[0]

        # Insert the new brand
        cursor.execute("INSERT INTO brands (brand_name) VALUES (?)", (new_brand,))
        connection.commit()

        # Grab the auto-incremented ID to pass back to the product creation flow
        new_brand_id = cursor.lastrowid
        print(f"[SUCCESS] Brand '{new_brand}' added successfully with ID #{new_brand_id}.")
        return new_brand_id

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
        return None
    finally:
        if connection:
            connection.close()


def add_category():
    """adds a new category to the database"""
    print("\n--- Add New Category ---")
    new_cat = input("Enter the category name (e.g., Siding, Roofing): ").strip()

    if not new_cat:
        print("[!] Category name cannot be empty.")
        return None

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        cursor.execute("SELECT category_id, category_name FROM categories WHERE LOWER(category_name) = LOWER(?)",
                       (new_cat,))
        existing = cursor.fetchone()

        if existing:
            print(f"[!] Category '{existing[1]}' already exists (ID: {existing[0]}).")
            return existing[0]

        cursor.execute("INSERT INTO categories (category_name) VALUES (?)", (new_cat,))
        connection.commit()

        new_cat_id = cursor.lastrowid
        print(f"[SUCCESS] Category '{new_cat}' added with ID #{new_cat_id}.")
        return new_cat_id

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
        return None
    finally:
        if connection:
            connection.close()


def add_sub_category(category_id):
    """adds a new sub-category to the database"""
    print("\n--- Add New Sub-Category ---")
    new_sub = input("Enter the sub-category name (e.g., Hero, J-Channel): ").strip()

    if not new_sub:
        print("[!] Sub-category name cannot be empty.")
        return None

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        # Check if this exact sub-category already exists underneath this specific parent category
        cursor.execute("""
            SELECT sub_category_id, sub_category_name 
            FROM sub_categories 
            WHERE LOWER(sub_category_name) = LOWER(?) AND category_id = ?
        """, (new_sub, category_id))
        existing = cursor.fetchone()

        if existing:
            print(f"[!] Sub-Category '{existing[1]}' already exists for this category (ID: {existing[0]}).")
            return existing[0]

        cursor.execute("INSERT INTO sub_categories (category_id, sub_category_name) VALUES (?, ?)",
                       (category_id, new_sub))
        connection.commit()

        new_sub_id = cursor.lastrowid
        print(f"[SUCCESS] Sub-Category '{new_sub}' added with ID #{new_sub_id}.")
        return new_sub_id

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
        return None
    finally:
        if connection:
            connection.close()


def view_product():
    """displays all relevant details of a product including bin location and pricing"""
    print("\n--- Product Lookup ---")
    try:
        prod_id = int(input("Enter Product Catalog ID: "))
    except ValueError:
        print("[!] Invalid entry. Product ID must be a number.")
        return

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # Complex JOIN to reconstruct the 3NF data and calculate total sales
        cursor.execute("""
                SELECT 
                    p.product_id, b.brand_name, c.category_name, sc.sub_category_name, 
                    p.product_name, p.sub_type, p.unit, p.unit_price,
                    i.quantity_on_hand, i.quantity_incoming, i.expected_restock_date,
                    COALESCE(SUM(oi.quantity), 0) as total_sold
                FROM products p
                JOIN brands b ON p.brand_id = b.brand_id
                JOIN sub_categories sc ON p.sub_category_id = sc.sub_category_id
                JOIN categories c ON sc.category_id = c.category_id
                JOIN inventory_status i ON p.product_id = i.product_id
                LEFT JOIN order_items oi ON p.product_id = oi.product_id
                WHERE p.product_id = ?
                GROUP BY p.product_id
            """, (prod_id,))

        product = cursor.fetchone()

        if not product:
            print(f"[!] Product ID #{prod_id} not found in the catalog.")
            return

        print(f"\n==========================================================")
        print(f" ITEM PROFILE: #{product['product_id']} | {product['brand_name']}")
        print(f"==========================================================")
        print(f" Description : {product['product_name']} ({product['sub_type']})")
        print(f" Hierarchy   : {product['category_name']} > {product['sub_category_name']}")
        print(f" Unit/Price  : {product['unit']} / ${product['unit_price']:,.2f}")
        print(f"----------------------------------------------------------")
        print(f" INVENTORY STATUS")
        print(f"----------------------------------------------------------")
        print(f" On-Hand     : {product['quantity_on_hand']} {product['unit']}s")

        incoming_str = f"{product['quantity_incoming']} (ETA: {product['expected_restock_date']})" if product[
                                                                                                          'quantity_incoming'] > 0 else "0"
        print(f" Incoming    : {incoming_str}")
        print(f" Total Sold  : {product['total_sold']} {product['unit']}s (Lifetime)")
        print(f"----------------------------------------------------------")
        print(f" WAREHOUSE MAPPING")
        print(f"----------------------------------------------------------")
        print(f" Pick Bin    : [Bin Assignment Pending]")
        print(f" Overstock   : [Bin Assignment Pending]")
        print(f"==========================================================\n")

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
    finally:
        if connection:
            connection.close()


def update_product():
    """updates any aspect of a product's details except for pricing"""
    print("\n--- Update Product Details ---")
    try:
        prod_id = int(input("Enter Product Catalog ID to update: "))
    except ValueError:
        print("[!] Invalid entry. Product ID must be a number.")
        return

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        cursor.execute("SELECT product_name, sub_type, unit FROM products WHERE product_id = ?", (prod_id,))
        product = cursor.fetchone()

        if not product:
            print(f"[!] Product ID #{prod_id} not found.")
            return

        print("\nEnter new values, or press Enter to keep the current value.")

        new_name = input(f"Product Name [{product['product_name']}]: ").strip() or product['product_name']
        new_sub = input(f"Sub-Type [{product['sub_type']}]: ").strip() or product['sub_type']
        new_unit = input(f"Unit of Measure [{product['unit']}]: ").strip() or product['unit']

        cursor.execute("""
                UPDATE products 
                SET product_name = ?, sub_type = ?, unit = ?
                WHERE product_id = ?
            """, (new_name, new_sub, new_unit, prod_id))

        connection.commit()
        print(f"\n[SUCCESS] Catalog ID #{prod_id} has been updated.")

    except sqlite3.Error as e:
        if connection:
            connection.rollback()
        print(f"Database Error: Transaction rolled back.\n{e}")
    finally:
        if connection:
            connection.close()


def delete_product():
    """removes a product from availability, only possible if there is none of this product left in inventory"""
    # currently this function can only remove products if they have never been sold due to the nature of the database schema
    print("\n--- Delete Product ---")
    try:
        prod_id = int(input("Enter the Catalog ID of the product to delete: "))
    except ValueError:
        print("[!] Invalid entry. Product ID must be a number.")
        return

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        # Verify the product exists
        cursor.execute("SELECT product_name, sub_type FROM products WHERE product_id = ?", (prod_id,))
        product = cursor.fetchone()

        if not product:
            print(f"[!] Product ID #{prod_id} not found.")
            return

        # SAFEGUARD: Check for historical sales data
        cursor.execute("SELECT COUNT(*) FROM order_items WHERE product_id = ?", (prod_id,))
        sales_count = cursor.fetchone()[0]

        if sales_count > 0:
            print(f"[!] ERROR: Cannot delete '{product[0]} ({product[1]})'.")
            print(f"    This item exists on {sales_count} historical invoice(s).")
            print(
                "    To remove it from the active catalog, an 'is_active' status must be added to the database schema.")
            return

        # Delete from both tables to prevent orphaned inventory counts
        cursor.execute("DELETE FROM inventory_status WHERE product_id = ?", (prod_id,))
        cursor.execute("DELETE FROM products WHERE product_id = ?", (prod_id,))

        connection.commit()
        print(f"[SUCCESS] Catalog ID #{prod_id} has been permanently removed.")

    except sqlite3.Error as e:
        if connection:
            connection.rollback()
        print(f"Database Error: Transaction rolled back.\n{e}")
    finally:
        if connection:
            connection.close()


def remove_brand():
    print("\n--- Remove Brand ---")
    brand_name = input("Enter the exact brand name to remove: ").strip()

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        cursor.execute("SELECT brand_id FROM brands WHERE LOWER(brand_name) = LOWER(?)", (brand_name,))
        brand = cursor.fetchone()

        if not brand:
            print("[!] Brand not found.")
            return

        brand_id = brand[0]

        # SAFEGUARD: Check for existing products
        cursor.execute("SELECT COUNT(*) FROM products WHERE brand_id = ?", (brand_id,))
        if cursor.fetchone()[0] > 0:
            print("[!] ERROR: Cannot delete. There are active products linked to this brand.")
            return

        cursor.execute("DELETE FROM brands WHERE brand_id = ?", (brand_id,))
        connection.commit()
        print(f"[SUCCESS] Brand '{brand_name}' has been removed.")

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
    finally:
        if connection:
            connection.close()


def remove_category():
    print("\n--- Remove Category ---")
    cat_name = input("Enter the exact category name to remove: ").strip()

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        cursor.execute("SELECT category_id FROM categories WHERE LOWER(category_name) = LOWER(?)", (cat_name,))
        cat = cursor.fetchone()

        if not cat:
            print("[!] Category not found.")
            return

        cat_id = cat[0]

        # SAFEGUARD: Check for existing sub-categories
        cursor.execute("SELECT COUNT(*) FROM sub_categories WHERE category_id = ?", (cat_id,))
        if cursor.fetchone()[0] > 0:
            print("[!] ERROR: Cannot delete. There are sub-categories linked to this parent category.")
            return

        cursor.execute("DELETE FROM categories WHERE category_id = ?", (cat_id,))
        connection.commit()
        print(f"[SUCCESS] Category '{cat_name}' has been removed.")

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
    finally:
        if connection:
            connection.close()


def remove_sub_category():
    print("\n--- Remove Sub-Category ---")
    sub_name = input("Enter the exact sub-category name to remove: ").strip()

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        cursor.execute("SELECT sub_category_id FROM sub_categories WHERE LOWER(sub_category_name) = LOWER(?)",
                       (sub_name,))
        sub = cursor.fetchone()

        if not sub:
            print("[!] Sub-Category not found.")
            return

        sub_id = sub[0]

        # SAFEGUARD: Check for existing products
        cursor.execute("SELECT COUNT(*) FROM products WHERE sub_category_id = ?", (sub_id,))
        if cursor.fetchone()[0] > 0:
            print("[!] ERROR: Cannot delete. There are active products linked to this sub-category.")
            return

        cursor.execute("DELETE FROM sub_categories WHERE sub_category_id = ?", (sub_id,))
        connection.commit()
        print(f"[SUCCESS] Sub-Category '{sub_name}' has been removed.")

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
    finally:
        if connection:
            connection.close()


def inventory_management_menu():
    while True:
        print(f"\n --- Inventory Management ---")
        print("01: View Product Details")
        print("02: Receive Incoming PO (Dock Delivery)")
        print("03: Cycle Count (Manual Adjustment)")
        print("04: Add New Product")
        print("05: Update Product Details")
        print("06: Delete Product")
        print("99: Return to Main Menu")

        choice = input("\nEnter Selection: ")
        match choice:
            case '01':
                view_product()
            case '02':
                receive_po()
            case '03':
                cycle_count()
            case '04':
                add_product()
            case '05':
                update_product()
            case '06':
                delete_product()
            case '99':
                break
            case _:
                print("Invalid selection.")