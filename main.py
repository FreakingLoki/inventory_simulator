import os
import sys
import math
import sqlite3
import pandas as pd

#TODO maybe add a script to auto-generate some of the csv file content (to randomize inventory stock levels and restock dates)
#TODO start building a good README.md


def initialize_local_database():
    # connect to (or if required, create) the database file
    connection = None
    try:
        connection = sqlite3.connect('local_inventory.db')

        # use Pandas to read the CSV files
        products_df = pd.read_csv('products.csv')
        requirements_df = pd.read_csv('requirements.csv')
        rules_df = pd.read_csv('category_rules.csv')

        # load the data into SQL tables
        # the 'replace' tag ensures that if the CSV files are updated, the database is updated when the program is launched
        products_df.to_sql('products', connection, if_exists='replace', index=False)
        requirements_df.to_sql('requirements', connection, if_exists='replace', index=False)
        rules_df.to_sql('rules', connection, if_exists='replace', index=False)

    except Exception as e:
        print(f"Database initialization/sync error:\n{e}")

    finally:
        connection.close()
        print("Database synchronized with CSV files")

def check_setup():
    print("--- Environment Check ---")

    # check if we are inside a virtual environment
    # sys.prefix is the current environment
    # sys.base_prefix is the main Python install
    if sys.prefix != sys.base_prefix:
        print("Virtual Environment: Active")
    else:
        print("Running in Global Python")

    # check if the database file exists
    if os.path.exists("local_inventory.db"):
        print("local_inventory.db: Found")
        print("Verifying integrity of database...")
        connection = None
        try:
            connection = sqlite3.connect('local_inventory.db')
            cursor = connection.cursor()
            # query the database for a list of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = ['products', 'requirements', 'rules']
            # check if the expected tables are present
            if all(table in tables for table in expected_tables):
                print("Database: All tables found")
                print("Database Integrity: Good")
                return True
            else:
                missing = [table for table in expected_tables if table not in tables]
                print(f"Database: Missing tables")
                print(f"Database is missing the below table(s):\n{missing}")
                return False

        except sqlite3.Error as e:
            print(f"Database verification error:\n{e}")
            return False
        finally:
            if connection:
                connection.close()

    else:
        print("local_inventory.db: Not found")
        return False


def display_quote(hero, quantity, accessories, warnings=None):
    main_total = float(hero['price']) * quantity

    print("\n" + "-" * 60)
    print(f"{'Quote':^60}")
    print("-" * 60)
    print(f"Main Item: {hero['name']} ({hero['color']})")
    print(f"Quantity: {quantity} {hero['unit']}")
    print(f"Subtotal: ${main_total:,.2f}")

    # check if there are any accessories to recommend
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

            print(f"- {acc['name']:.<35} qty: {acc_qty:>3} | ${acc_cost:>10,.2f}")

        print("-" * 60)
        print(f"{'Total Before Accessories:':<45} ${main_total:>12,.2f}")
        print(f"{'Grand Total (Including Accessories):':<45} ${grand_total:>12,.2f}")

    # if there are stock level warnings, print them after the main quote
    if warnings:
        print("\n" + "!" * 20 + " STOCK ALERTS " + "!" *20)
        for msg in warnings:
            print(f"{msg}")
        print("!" * 54)

    print("-" * 60 + "\n")

def get_stock_level(product_id):
    connection = None
    try:
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_query = "SELECT inventory FROM products WHERE id = ?"
        cursor.execute(sql_query, (product_id,))
        item = cursor.fetchone()

        if not item:
            print(f"Error: product with id {product_id} not found.")
            return None

        else:
            on_hand_count = item['inventory']
            print(f"On Hand count: {on_hand_count}")
            return on_hand_count

    except sqlite3.Error as e:
        print(f"Error: A database error occurred:\n{e}")
    finally:
        if connection:
            connection.close()

def get_restock_info(product_id):
    connection = None
    try:
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_query = "SELECT incoming, restock_date FROM products WHERE id = ?"
        cursor.execute(sql_query, (product_id,))
        item = cursor.fetchone()

        if not item:
            print(f"Error: product with id {product_id} not found.")
            return None

        else:
            restock_amount = item['incoming']
            restock_date = item['restock_date']

            return restock_amount, restock_date

    except sqlite3.Error as e:
        print(f"Error: A database error occurred:\n{e}")
    finally:
        if connection:
            connection.close()

def generate_quote(product_id, quantity):
    connection = None
    try:
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # grab the product info from the database
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        item = cursor.fetchone()

        if not item:
            print(f"Error: {product_id} not found.")
            return

        # create a list of warnings for low- or no-stock items
        stock_warnings = []
        current_stock = item['inventory']
        if quantity > current_stock:
            restock_qty, restock_date = get_restock_info(product_id)
            stock_warnings.append(
                f"MAIN ITEM: {item['name']} ({item['color']})\n"
                f"           Only {current_stock} on hand. (Need {quantity:.2f})\n"
                f"           {restock_qty} more arriving {restock_date}."
            )

        # determine the sub_category of the item
        # if the sub_category is "None" then it is a "hero" item
        is_hero = item['sub_category'] == "Hero"

        # if the item is not a hero item
        if not is_hero:
            # generate a simple quote without recommended add-ons
            accessories = "None"
            display_quote(item, quantity, accessories, stock_warnings)
            return

        # if the item is a hero item the following block will execute
        # start by checking the rule for this item's category
        cursor.execute("SELECT color_matching_type FROM rules WHERE category = ?", (item['category'],))
        rule_row = cursor.fetchone()
        rule = rule_row['color_matching_type'] if rule_row else "None"

        # determine if the accessories match the hero product's color
        # only if color matching rule is optional
        accessory_color = item['color']
        if rule == "Optional":
            choice = input(f"Accessories match {item['color']}? (y/n): ").lower()
            if choice == 'n':
                accessory_color = input("Enter accessory color:").capitalize()

        # grab the accessories' information
        sql_query = """
            SELECT p.name, p.price, p.inventory, p.incoming, p.restock_date, r.quantity_multiplier, p.unit
            FROM products p
            JOIN requirements r ON p.sub_category = r.required_accessory
            WHERE r.category = ? AND p.color = ?
        """
        cursor.execute(sql_query, (item['category'], accessory_color))
        accessories = cursor.fetchall()

        for acc in accessories:
            # calculate how many are needed based on the hero quantity
            needed_qty = math.ceil(quantity * acc['quantity_multiplier'])
            if needed_qty > acc['inventory']:
                stock_warnings.append(
                    f"ACCESSORY: {acc['name']} ({accessory_color})\n"
                    f"           Only {acc['inventory']} on hand (Need {needed_qty}).\n"
                    f"           {acc['incoming']} more arriving {acc['restock_date']}."
                )

        # call the function to display the quote with the add-on recommendations
        display_quote(item, quantity, accessories, stock_warnings)

    except sqlite3.Error as e:
        print(f"Error: Database error occurred:\n{e}")
    finally:
        if connection:
            connection.close()


def display_inventory_list(only_heroes=True):
    connection = sqlite3.connect('local_inventory.db')
    cursor = connection.cursor()

    query = "SELECT id, category, name, color FROM products"
    if only_heroes:
        query += " WHERE [sub_category] = 'Hero'"

    cursor.execute(query)
    rows = cursor.fetchall()

    print(f"\n{'ID':<5} | {'Category':<10} | {'Name':<25} | {'Color'}")
    print("-" * 60)
    for row in rows:
        print(f"{row[0]:<5} | {row[1]:<10} | {row[2]:<25} | {row[3]}")
    connection.close()

def main_menu():
    while True:
        print(f" ----- Main Menu -----")
        print("01: Generate A Quote")
        print("02: List Hero Products")
        print("03: List All Products")
        print("99: Exit")

        choice = input("\nEnter Selection: ")

        match choice:
            case '01':
                p_id = input("Enter Product ID: ")
                try:
                    qty = float(input("Enter Quantity: "))
                    if qty <= 0:
                        raise ValueError("Invalid quantity. Please enter a positive number greater than 0")
                    generate_quote(p_id, qty)
                except ValueError as e:
                    print(f"Error:\n{e}")

            case '02' | '03':
                # this line displays only the hero items if the user selects option 02
                # otherwise it displays all items
                display_inventory_list(only_heroes=(choice == '02'))

            case '99':
                print("Exiting...")
                break

            case _:
                print("Invalid choice, try again.")



if __name__ == "__main__":
    # initialize the database
    initialize_local_database()
    if check_setup():
        # launch the interactive menu
        main_menu()
    else:
        print("Setup check failed. You may need to manually verify your CSV files and database.")