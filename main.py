# ----- IMPORTS SECTION -----

import os
import sys
import math
import sqlite3
import pandas as pd
from datetime import datetime

# ----- GLOBAL CONSTANTS -----

SIDING_FACTORS = {
    "stick_length": 12.5,
    "window_j_ft": 13.0,
    "window_finish_ft": 3.0,
    "door_j_ft": 16.5,
    "gable_pitch_mult": 1.25,
    "sqft_per_square": 100.0,
    "corner_post_length": 10.0,
    "avg_wall_height": 9.0,
}

ROOFING_FACTORS = {
    "bundle_per_square": 3.0,
    "ridge_cap_coverage": 30.0,
    "starter_coverage": 100.0,
    "ice_water_sqft": 200.0,
    "ice_water_width_ft": 3.0,
    "underlayment_sqft": 1000.0,
    "sqft_per_square": 100.0
}

SHEETROCK_FACTORS = {
    "sqft_per_panel": 32.0,
    "tape_coverage": 50.0,
    "screws_sqft_per_pound": 150,
    "mud_sqft_per_pail": 600,
}

INSULATION_FACTORS = {
    "sqft_per_bag": 50.0,
    "sqft_per_board": 32.0,
    "sqft_per_roll": 100.0,
    "sqft_per_wire_box": 200,
}

DB_FILE = 'wms_normalized.db'


# ----- FUNCTIONS DEFINITIONS -----

def initialize_local_database():
    """Syncs non-normalized configuration files (requirements/rules) to the database."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)

        # We still use Pandas here ONLY to load your operational rules, since those weren't normalized
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
    """Verifies the integrity of the normalized local environment."""
    print("--- Environment Check ---")

    if sys.prefix != sys.base_prefix:
        print("Virtual Environment: Active")
    else:
        print("Running in Global Python")

    if os.path.exists(DB_FILE):
        print(f"{DB_FILE}: Found")
        print("Verifying integrity of database...")
        connection = None
        try:
            connection = sqlite3.connect(DB_FILE)
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            # Updated to match our new 3NF Schema
            expected_tables = ['brands', 'categories', 'sub_categories', 'products',
                               'inventory_status', 'customers', 'orders', 'order_items']

            if all(table in tables for table in expected_tables):
                print("Database: All core normalized tables found")
                print("Database Integrity: Good")
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


def display_quote(hero, quantity, accessories, warnings=None):
    """Formats and displays job quotes to the user."""
    main_total = float(hero['price']) * quantity

    print("\n" + "-" * 60)
    print(f"{'Quote':^60}")
    print("-" * 60)
    print(f"Main Item: {hero['brand']} {hero['name']} ({hero['sub_type']})")
    print(f"Quantity: {quantity} {hero['unit']}")
    print(f"Subtotal: ${main_total:,.2f}")

    if accessories == "None" or not accessories:
        print("-" * 60)
        print(f"{'Grand Total:':^45} ${main_total:>12,.2f}")
    else:
        print("\n" + "-" * 20 + " Suggested Add-Ons " + "-" * 20)
        grand_total = main_total

        for acc in accessories:
            acc_qty = math.ceil(quantity * acc['quantity_multiplier'])
            acc_cost = float(acc['price']) * acc_qty
            grand_total += acc_cost
            display_name = f"{acc['brand']} {acc['name']}"
            print(f"- {display_name:.<35} qty: {acc_qty:>3} | ${acc_cost:>10,.2f}")

        print("-" * 60)
        print(f"{'Total Before Accessories:':<45} ${main_total:>12,.2f}")
        print(f"{'Grand Total (Including Accessories):':<45} ${grand_total:>12,.2f}")

    if warnings:
        print("\n" + "!" * 20 + " STOCK ALERTS " + "!" * 20)
        for msg in warnings:
            print(f"{msg}")
        print("!" * 54)

    print("-" * 60 + "\n")


def get_stock_level(product_id):
    """Checks the stock level of a product."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_query = "SELECT quantity_on_hand FROM inventory_status WHERE product_id = ?"
        cursor.execute(sql_query, (product_id,))
        item = cursor.fetchone()

        if not item:
            print(f"Error: product with id {product_id} not found.")
            return None
        else:
            return item['quantity_on_hand']
    except sqlite3.Error as e:
        print(f"Error: A database error occurred:\n{e}")
    finally:
        if connection:
            connection.close()


def get_restock_info(product_id):
    """Grabs the restocking information of a given product."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_query = "SELECT quantity_incoming, expected_restock_date FROM inventory_status WHERE product_id = ?"
        cursor.execute(sql_query, (product_id,))
        item = cursor.fetchone()

        if not item:
            return None, None
        else:
            return item['quantity_incoming'], item['expected_restock_date']
    except sqlite3.Error as e:
        print(f"Error: A database error occurred:\n{e}")
    finally:
        if connection:
            connection.close()


def get_calculation_mode():
    """Prompts the user to determine calculation method."""
    print("\n--- Accessory Calculation Options ---")
    print("01: Standard Estimate (Uses industry-average ratios)")
    print("02: Site-Specific Estimate (Enter window/door/corner counts)")
    print("03: Custom Quantities (Enter exact accessory counts)")
    print("04: Skip Add-ons (Quote hero product only)")
    return int(input("\nSelect Calculation Method: "))


def get_site_specs(category):
    """Collects job-site measurements."""
    specs = {}
    if category == "Siding":
        print("\n--- Siding Site Details ---")
        specs['windows'] = int(input("Number of Windows: ") or 0)
        specs['doors'] = int(input("Number of Doors: ") or 0)
        specs['foundation_ft'] = float(input("Total Foundation Linear Feet: ") or 0)
        specs['gable_width'] = float(input("Total Width of Gable Bases (ft): ") or 0)
        specs['outside_corners'] = int(input("Number of Outside Corners: ") or 0)
        specs['inside_corners'] = int(input("Number of Inside Corners: ") or 0)
        specs['total_wall_sqft'] = float(input("Total Wall Square Footage: ") or 0)
    elif category == "Roofing":
        print("\n--- Roofing Site Details ---")
        specs['ridges_ft'] = float(input("Total Linear Feet of Ridges: ") or 0)
        specs['eaves_ft'] = float(input("Total Linear Feet of Eaves: ") or 0)
        specs['rakes_ft'] = float(input("Total Linear Feet of Rakes: ") or 0)
        specs['valleys_ft'] = float(input("Total Linear Feet of Valleys: ") or 0)
        specs['total_sqft'] = float(input("Total Roof Square Footage (Deck Area): ") or 0)
    elif category in ["Sheetrock", "Insulation"]:
        print(f"\n--- {category} Site Details ---")
        specs['total_sqft'] = float(input("Total Square Feet: ") or 0)
    return specs


def calculate_site_specific(category, hero_qty):
    """Calculates site-specific numbers."""
    specs = get_site_specs(category)
    calculated_results = {}
    final_hero_qty = hero_qty

    match category:
        case "Siding":
            if final_hero_qty is None:
                final_hero_qty = math.ceil(specs['total_wall_sqft'] / SIDING_FACTORS['sqft_per_square'])
            total_j_ft = (specs['windows'] * SIDING_FACTORS['window_j_ft']) + \
                         (specs['doors'] * SIDING_FACTORS['door_j_ft']) + \
                         (specs['gable_width'] * SIDING_FACTORS['gable_pitch_mult'])
            calculated_results['J-Channel'] = math.ceil(total_j_ft / SIDING_FACTORS['stick_length']) / final_hero_qty
            total_finish_ft = (specs['windows'] * SIDING_FACTORS['window_finish_ft']) + specs['foundation_ft']
            calculated_results['Finish Trim'] = math.ceil(
                total_finish_ft / SIDING_FACTORS['stick_length']) / final_hero_qty
            posts_per_corner = math.ceil(SIDING_FACTORS['avg_wall_height'] / SIDING_FACTORS['corner_post_length'])
            calculated_results['Outside Corner Post'] = (specs['outside_corners'] * posts_per_corner) / final_hero_qty
            calculated_results['Inside Corner Post'] = (specs['inside_corners'] * posts_per_corner) / final_hero_qty
            calculated_results['Starter Strip'] = math.ceil(
                specs['foundation_ft'] / SIDING_FACTORS['stick_length']) / final_hero_qty
        case "Roofing":
            if final_hero_qty is None:
                final_hero_qty = math.ceil(
                    (specs['total_sqft'] / ROOFING_FACTORS['sqft_per_square']) * ROOFING_FACTORS['bundle_per_square'])
            calculated_results['Ridge Cap'] = math.ceil(
                specs['ridges_ft'] / ROOFING_FACTORS['ridge_cap_coverage']) / final_hero_qty
            calculated_results['Shingle Starter'] = math.ceil(
                (specs['eaves_ft'] + specs['rakes_ft']) / ROOFING_FACTORS['starter_coverage']) / final_hero_qty
            total_ice_water_sqft = (specs['eaves_ft'] * 6.0) + (specs['valleys_ft'] * 3.0)
            calculated_results['Ice and Water Shield'] = math.ceil(
                total_ice_water_sqft / ROOFING_FACTORS['ice_water_sqft']) / final_hero_qty
            remaining_area = max(0, specs['total_sqft'] - total_ice_water_sqft)
            calculated_results['Synthetic Underlayment'] = math.ceil(
                remaining_area / ROOFING_FACTORS['underlayment_sqft']) / final_hero_qty
        case "Sheetrock":
            if final_hero_qty is None:
                final_hero_qty = math.ceil(specs['total_sqft'] / SHEETROCK_FACTORS['sqft_per_panel'])
            calculated_results['Screws'] = math.ceil(
                specs['total_sqft'] / SHEETROCK_FACTORS['screws_sqft_per_pound']) / final_hero_qty
            calculated_results['Mud'] = math.ceil(
                specs['total_sqft'] / SHEETROCK_FACTORS['mud_sqft_per_pail']) / final_hero_qty
            calculated_results['Tape'] = math.ceil(
                specs['total_sqft'] / SHEETROCK_FACTORS['tape_coverage']) / final_hero_qty
        case "Insulation":
            if final_hero_qty is None:
                final_hero_qty = math.ceil(specs['total_sqft'] / INSULATION_FACTORS['sqft_per_bag'])
            calculated_results['6-mil Poly Vapor Barrier'] = math.ceil(
                specs['total_sqft'] / INSULATION_FACTORS['sqft_per_roll']) / final_hero_qty
            calculated_results['Insulation Fabric Backing'] = math.ceil(
                specs['total_sqft'] / INSULATION_FACTORS['sqft_per_roll']) / final_hero_qty
            calculated_results['Insulation Support Wires'] = math.ceil(
                specs['total_sqft'] / INSULATION_FACTORS['sqft_per_wire_box']) / final_hero_qty

    return final_hero_qty, calculated_results


def find_customer(account_number):
    """Fetches a customer's information."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM customers WHERE account_number = ?", (account_number,))
        customer = cursor.fetchone()
        return dict(customer) if customer else None
    except Exception as e:
        print(f"Error:\n{e}")
        return None
    finally:
        if connection:
            connection.close()


def check_credit_status(customer, order_total):
    """Checks if a customer has enough credit to place an order."""
    projected_balance = customer['unpaid_balance'] + order_total
    if projected_balance > customer['credit_limit']:
        overage = projected_balance - customer['credit_limit']
        return False, f"Credit Denied: Order Total ${order_total:,.2f} is ${overage:,.2f} over the limit."
    return True, "Credit approved."


def generate_quote(product_id):
    """Master controller for quote generation."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # Fetches hero item using JOINs and ALIASES to keep dictionary keys identical to old code
        sql_hero = """
            SELECT 
                p.product_id as id, 
                b.brand_name as brand, 
                c.category_name as category, 
                sc.sub_category_name as sub_category, 
                p.product_name as name, 
                p.sub_type, 
                p.unit, 
                p.unit_price as price, 
                i.quantity_on_hand as inventory, 
                i.quantity_incoming as incoming, 
                i.expected_restock_date as restock_date
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN sub_categories sc ON p.sub_category_id = sc.sub_category_id
            JOIN categories c ON sc.category_id = c.category_id
            JOIN inventory_status i ON p.product_id = i.product_id
            WHERE p.product_id = ?
        """
        cursor.execute(sql_hero, (product_id,))
        item = cursor.fetchone()

        if not item:
            print(f"Error: Product ID {product_id} not found.")
            return None

        item = dict(item)
        mode = get_calculation_mode()
        final_hero_qty = 0
        final_accessories = []
        stock_warnings = []

        # Common accessory query template mapping 3NF to flat dictionary structure
        sql_acc_base = """
            SELECT 
                p.product_id as id, b.brand_name as brand, p.product_name as name, 
                p.unit_price as price, i.quantity_on_hand as inventory, 
                i.quantity_incoming as incoming, i.expected_restock_date as restock_date, 
                sc.sub_category_name as sub_category, p.unit, p.sub_type
            FROM products p
            JOIN brands b ON p.brand_id = b.brand_id
            JOIN sub_categories sc ON p.sub_category_id = sc.sub_category_id
            JOIN categories c ON sc.category_id = c.category_id
            JOIN inventory_status i ON p.product_id = i.product_id
            WHERE c.category_name = ? AND b.brand_name = ? AND (p.sub_type = ? OR p.sub_type = 'Universal')
        """

        if mode == 4:
            final_hero_qty = float(input(f"Enter quantity of {item['unit']}s: "))
            final_accessories = "None"

        elif mode == 1:
            final_hero_qty = float(input(f"Enter quantity of {item['unit']}s: "))
            sql_query = sql_acc_base + " AND sc.sub_category_name IN (SELECT required_accessory FROM requirements WHERE category = ?)"
            cursor.execute(sql_query, (item['category'], item['brand'], item['sub_type'], item['category']))

            # Fetch quantity multipliers
            raw_accs = [dict(row) for row in cursor.fetchall()]
            for acc in raw_accs:
                cursor.execute("SELECT quantity_multiplier FROM requirements WHERE required_accessory = ?",
                               (acc['sub_category'],))
                mult_row = cursor.fetchone()
                acc['quantity_multiplier'] = mult_row['quantity_multiplier'] if mult_row else 0
                final_accessories.append(acc)

        elif mode == 2:
            final_hero_qty, site_multipliers = calculate_site_specific(item['category'], None)
            sql_query = sql_acc_base + " AND sc.sub_category_name != 'Hero'"
            cursor.execute(sql_query, (item['category'], item['brand'], item['sub_type']))

            raw_accessories = cursor.fetchall()
            for row in raw_accessories:
                acc_dict = dict(row)
                acc_dict['quantity_multiplier'] = site_multipliers.get(acc_dict['sub_category'], 0)
                if acc_dict['quantity_multiplier'] > 0:
                    final_accessories.append(acc_dict)

        elif mode == 3:
            final_hero_qty = float(input(f"Enter quantity of {item['unit']}s: "))
            sql_query = sql_acc_base + " AND sc.sub_category_name != 'Hero'"
            cursor.execute(sql_query, (item['category'], item['brand'], item['sub_type']))

            raw_accessories = cursor.fetchall()
            print("\n--- Manual Accessory Entry ---")
            for row in raw_accessories:
                acc_dict = dict(row)
                user_count = float(input(f"How many {acc_dict['name']}? ") or 0)
                acc_dict['quantity_multiplier'] = user_count / final_hero_qty if final_hero_qty > 0 else 0
                if user_count > 0:
                    final_accessories.append(acc_dict)

        # ----- stock validation
        if final_hero_qty > item['inventory']:
            in_qty, in_date = item['incoming'], item['restock_date']
            msg = f"MAIN ITEM: {item['name']} - Need {final_hero_qty}, only {item['inventory']} on hand."
            if in_qty and int(in_qty) > 0:
                msg += f" ({in_qty} arriving {in_date})"
            stock_warnings.append(msg)

        if final_accessories != "None":
            for acc in final_accessories:
                needed = math.ceil(final_hero_qty * acc['quantity_multiplier'])
                if needed > acc['inventory']:
                    msg = f"ACCESSORY: {acc['name']} - Need {needed}, only {acc['inventory']} on hand."
                    if acc['incoming'] and int(acc['incoming']) > 0:
                        msg += f" ({acc['incoming']} arriving {acc['restock_date']})"
                    stock_warnings.append(msg)

        return {
            "hero": item,
            "quantity": final_hero_qty,
            "accessories": final_accessories,
            "warnings": stock_warnings
        }

    except ValueError:
        print("Error: Invalid input. Please enter numeric values.")
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        if connection:
            connection.close()


def display_inventory_list(only_heroes=True):
    """Displays items using 3NF relational structure."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        query = """
            SELECT 
                p.product_id as id, c.category_name as category, 
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
        print(f"Error: Database error occurred:{e}")
    finally:
        if connection:
            connection.close()


def get_next_invoice_number():
    """Fetches the next invoice number safely from SQL."""
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()
    cursor.execute("SELECT MAX(invoice_number) FROM orders;")
    result = cursor.fetchone()[0]
    connection.close()
    return result + 1 if result else 1001


def check_order_feasibility(quote_data):
    """
    Evaluates if an order can be filled today, pushed to a future date, or must be rejected.
    Returns: (is_possible, push_date, message)
    """
    latest_restock_date = datetime.now()
    requires_delay = False

    # Check Hero Item
    hero = quote_data['hero']
    hero_needed = quote_data['quantity']
    if hero_needed > hero['inventory']:
        if not hero['incoming'] or hero_needed > (hero['inventory'] + hero['incoming']):
            return False, None, f"REJECTED: Hero item '{hero['name']}' requires {hero_needed}, but warehouse only has {hero['inventory']} on hand and {hero['incoming'] or 0} incoming."
        requires_delay = True
        hero_date = datetime.strptime(hero['restock_date'], '%Y-%m-%d') if hero['restock_date'] else datetime.now()
        latest_restock_date = max(latest_restock_date, hero_date)

    # Check Accessories
    if quote_data['accessories'] != "None":
        for acc in quote_data['accessories']:
            acc_needed = math.ceil(quote_data['quantity'] * acc['quantity_multiplier'])
            if acc_needed > acc['inventory']:
                if not acc['incoming'] or acc_needed > (acc['inventory'] + acc['incoming']):
                    return False, None, f"REJECTED: Accessory '{acc['name']}' requires {acc_needed}, but warehouse only has {acc['inventory']} on hand and {acc['incoming'] or 0} incoming."
                requires_delay = True
                acc_date = datetime.strptime(acc['restock_date'], '%Y-%m-%d') if acc['restock_date'] else datetime.now()
                latest_restock_date = max(latest_restock_date, acc_date)

    if requires_delay:
        return True, latest_restock_date.strftime('%Y-%m-%d'), "DELAY REQUIRED"
    return True, datetime.now().strftime('%Y-%m-%d'), "READY NOW"


def submit_order(quote_data, customer, grand_total, order_date):
    """Saves the order and deducts inventory dynamically across on-hand and incoming."""
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    invoice_nbr = get_next_invoice_number()
    acct_num = customer['account_number'] if customer else 0

    try:
        # 1. Create Invoice Header using the validated order_date
        cursor.execute("INSERT INTO orders (invoice_number, account_number, order_date) VALUES (?, ?, ?)",
                       (invoice_nbr, acct_num, order_date))

        # Helper logic to split deductions between on_hand and incoming if needed
        def deduct_inventory(item_id, qty_needed):
            cursor.execute("SELECT quantity_on_hand, quantity_incoming FROM inventory_status WHERE product_id = ?",
                           (item_id,))
            on_hand, incoming = cursor.fetchone()

            if qty_needed <= on_hand:
                cursor.execute(
                    "UPDATE inventory_status SET quantity_on_hand = quantity_on_hand - ? WHERE product_id = ?",
                    (qty_needed, item_id))
            else:
                remainder = qty_needed - on_hand
                cursor.execute("""
                    UPDATE inventory_status 
                    SET quantity_on_hand = 0, quantity_incoming = quantity_incoming - ? 
                    WHERE product_id = ?
                """, (remainder, item_id))

        # 2. Process Hero
        hero_id = int(quote_data['hero']['id'])
        cursor.execute(
            "INSERT INTO order_items (invoice_number, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
            (invoice_nbr, hero_id, quote_data['quantity'], quote_data['hero']['price']))
        deduct_inventory(hero_id, quote_data['quantity'])

        # 3. Process Accessories
        if quote_data['accessories'] != "None":
            for acc in quote_data['accessories']:
                acc_id = int(acc['id'])
                qty_needed = math.ceil(quote_data['quantity'] * acc['quantity_multiplier'])

                cursor.execute(
                    "INSERT INTO order_items (invoice_number, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                    (invoice_nbr, acc_id, qty_needed, acc['price']))
                deduct_inventory(acc_id, qty_needed)

        # 4. Update Customer Balance
        if customer:
            cursor.execute("UPDATE customers SET unpaid_balance = unpaid_balance + ? WHERE account_number = ?",
                           (grand_total, acct_num))

        connection.commit()
        print(f"\n[SUCCESS] Invoice #{invoice_nbr} successfully logged for {order_date}.")
        print(f"Inventory updated and ${grand_total:,.2f} charged to record.")

    except sqlite3.Error as e:
        connection.rollback()
        print(f"Transaction failed! Changes rolled back. Error: {e}")
    finally:
        connection.close()


def handle_quote_actions(quote_data, customer=None):
    """Displays quote options and runs safety checks before submission."""
    while True:
        hero_total = quote_data['hero']['price'] * quote_data['quantity']
        accessory_total = 0
        if quote_data['accessories'] != "None":
            accessory_total = sum((acc['price'] * math.ceil(quote_data['quantity'] * acc['quantity_multiplier']))
                                  for acc in quote_data['accessories'])
        grand_total = hero_total + accessory_total

        display_quote(quote_data['hero'], quote_data['quantity'], quote_data['accessories'], quote_data['warnings'])

        print(f" --- Customer: {customer['customer_name'] if customer else 'Guest'} --- ")
        print("01: Submit and Finalize Order")
        print("02: Modify Quantities (Add/Remove items)")
        print("03: Discard Quote")

        choice = input("\nEnter Selection: ")

        match choice:
            case "01":
                # 1. Credit Check
                if customer:
                    allowed, message = check_credit_status(customer, grand_total)
                    if not allowed:
                        print(f"\n{message}")
                        continue

                # 2. Inventory Feasibility Check
                is_possible, order_date, status_msg = check_order_feasibility(quote_data)

                if not is_possible:
                    print(f"\n[!] ORDER BLOCKED: {status_msg}")
                    print("Please modify quantities or discard the quote.")
                    continue

                if order_date != datetime.now().strftime('%Y-%m-%d'):
                    print(f"\n[!] INVENTORY SHORTAGE: This order exceeds current on-hand stock.")
                    print(f"The earliest we can fulfill this entire order is: {order_date}")
                    confirm = input("Would you like to reserve this stock and push the order date? (y/n): ").lower()
                    if confirm != 'y':
                        print("Order cancelled by user.")
                        continue

                # 3. Submit
                submit_order(quote_data, customer, grand_total, order_date)
                break
            case "02":
                print("Quote modification coming soon...")
            case "03":
                if input("Are you sure you'd like to discard this quote? (y/n): ").lower() == "y":
                    print("Quote discarded")
                    break


def start_quote_flow():
    """Starts the quote generation process."""
    product_id = input("Enter Product ID: ").strip()
    if not product_id:
        print("Invalid Product ID.")
        return

    print("\n ----- Customer Selection -----")
    account_number = input("Enter Customer Account Number or 0 for Guest: ").strip()
    current_customer = find_customer(account_number) if account_number and account_number != "0" else None

    quote_data = generate_quote(product_id)
    if quote_data:
        handle_quote_actions(quote_data, current_customer)


def get_invoice_data(invoice_number):
    """Pulls dynamic invoice data."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_query = """
            SELECT o.invoice_number, o.order_date as date, o.account_number, 
                   b.brand_name as brand, p.product_name as name, 
                   oi.quantity, p.unit, (oi.quantity * oi.price_at_sale) as line_total,
                   c.customer_name
            FROM orders o
            JOIN order_items oi ON o.invoice_number = oi.invoice_number
            JOIN products p ON oi.product_id = p.product_id
            JOIN brands b ON p.brand_id = b.brand_id
            LEFT JOIN customers c ON o.account_number = c.account_number
            WHERE o.invoice_number = ?
        """
        cursor.execute(sql_query, (invoice_number,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows] if rows else None
    except sqlite3.Error as e:
        print(f"Error fetching invoice data:\n{e}")
        return None
    finally:
        if connection:
            connection.close()


def display_invoice(invoice_data):
    """Prints a formatted invoice."""
    if not invoice_data:
        print("\n[!] No invoice data to display.")
        return

    header = invoice_data[0]
    invoice_no = header['invoice_number']
    customer = header['customer_name'] if header['customer_name'] else "GUEST"

    print("\n" + "=" * 60)
    print(f"{'INVOICE: #' + str(invoice_no):^60}")
    print(f"{'Date: ' + header['date']:^60}")
    print(f"{'Customer: ' + customer:^60}")
    print("=" * 60)

    grand_total = 0
    for row in invoice_data:
        display_name = f"{row['brand']} {row['name']}"
        print(f"- {display_name:.<40} {row['quantity']:>5} {row['unit']:<6} | ${row['line_total']:>10,.2f}")
        grand_total += row['line_total']

    print("-" * 60)
    print(f"{'TOTAL DUE:':>48} ${grand_total:>10,.2f}")
    print("=" * 60 + "\n")


def get_recent_orders_summary():
    """Fetches a summary of all unique invoices."""
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_query = """
            SELECT o.invoice_number, o.order_date as date, 
                   COALESCE(c.customer_name, 'GUEST') as customer,
                   SUM(oi.quantity * oi.price_at_sale) as order_total
            FROM orders o
            JOIN order_items oi ON o.invoice_number = oi.invoice_number
            LEFT JOIN customers c ON o.account_number = c.account_number
            GROUP BY o.invoice_number
            ORDER BY o.invoice_number DESC
        """
        cursor.execute(sql_query)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        return None
    finally:
        if connection:
            connection.close()


def order_history_manager():
    """Main interface for browsing orders."""
    while True:
        summary = get_recent_orders_summary()
        if not summary:
            print("\n[!] No order history found.")
            break

        display_order_ledger(summary)
        choice = input("\nEnter Invoice # to view details (or 'q' to return to Main Menu): ").strip()

        if choice.lower() == 'q' or not choice:
            break

        invoice_data = get_invoice_data(choice)
        if invoice_data:
            display_invoice(invoice_data)
            input("Press Enter to return to the Ledger...")
        else:
            print(f"Invoice #{choice} not found.")


def display_order_ledger(summary_data):
    """Prints a table of all recent transactions."""
    print("\n" + "=" * 70)
    print(f"{'SALES LEDGER / ORDER HISTORY':^70}")
    print("=" * 70)
    print(f"{'INV #':<10} | {'Date':<12} | {'Customer':<25} | {'Total'}")
    print("-" * 70)

    for row in summary_data:
        print(f"{row['invoice_number']:<10} | {row['date']:<12} | "
              f"{row['customer']:<25} | ${row['order_total']:>10,.2f}")
    print("=" * 70)


def receive_po():
    """Simulates a delivery truck arriving and unloading expected stock."""
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

        # --- New Partial Delivery Logic ---
        try:
            received_qty = int(input(f"Enter quantity received (Expected: {incoming}): "))

            if received_qty > 0:
                if received_qty < incoming:
                    # Partial delivery
                    cursor.execute("""
                        UPDATE inventory_status 
                        SET quantity_on_hand = quantity_on_hand + ?,
                            quantity_incoming = quantity_incoming - ?
                        WHERE product_id = ?
                    """, (received_qty, received_qty, product_id))
                    print(
                        f"[SUCCESS] Partial delivery of {received_qty} received. {incoming - received_qty} still on backorder.")
                else:
                    # Full delivery
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
    """Allows manual override of physical stock for auditing."""
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
                count_difference = new_stock - current_stock
                print(f"[SUCCESS] Inventory adjusted by {count_difference} units. New total: {new_stock}")
            else:
                print("Count matches system. No adjustment needed.")
        except ValueError:
            print("Invalid input. Must be a whole number.")

    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        connection.close()


def inventory_management_menu():
    """Sub-menu for warehouse operations."""
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


def main_menu():
    """Main application loop."""
    while True:
        print(f"\n ----- Main Menu -----")
        print("01: Generate A Quote")
        print("02: List Hero Products")
        print("03: List All Products")
        print("04: View Order History")
        print("05: Manage Inventory")
        print("99: Exit")

        choice = input("\nEnter Selection: ")

        match choice:
            case '01':
                start_quote_flow()
            case '02' | '03':
                display_inventory_list(only_heroes=(choice == '02'))
            case '04':
                order_history_manager()
            case '05':
                inventory_management_menu()
            case '99':
                print("Exiting...")
                break
            case _:
                print("Invalid choice, try again.")


# ----- EXECUTION BLOCK -----

if __name__ == "__main__":
    initialize_local_database()
    if check_setup():
        main_menu()