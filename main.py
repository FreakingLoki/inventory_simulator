# ----- IMPORTS SECTION -----

import os
import sys
import math
import sqlite3
import pandas as pd

# ----- FUNCTIONS DEFINITIONS -----

def initialize_local_database():
    """This function creates the local copy of the database if it does not already exist
    if it does already exist, it updates the local copy of the database"""

    # set the connection to none as a default
    connection = None
    try:
        # connect to the database
        connection = sqlite3.connect('local_inventory.db')

        # use Pandas to read the CSV files
        # read the files from CSV to DataFrames
        products_df = pd.read_csv('products.csv')
        requirements_df = pd.read_csv('requirements.csv')
        rules_df = pd.read_csv('category_rules.csv')

        # load the data into SQL tables from the DataFrames
        # the 'replace' tag ensures that if the CSV files are updated, the database is updated when the program is launched
        products_df.to_sql('products', connection, if_exists='replace', index=False)
        requirements_df.to_sql('requirements', connection, if_exists='replace', index=False)
        rules_df.to_sql('rules', connection, if_exists='replace', index=False)

    except Exception as e:
        # if there's a problem, notify the user
        print(f"Database initialization/sync error:\n{e}")

    finally:
        # always close the connection when finished
        if connection:
            connection.close()
            print("Database synchronized with CSV files")

def check_setup():
    """This function verifies the integrity of the local environment to ensure that the
    program will run in a predictable manner"""

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
            # if the database file exists, connect to it
            connection = sqlite3.connect('local_inventory.db')
            cursor = connection.cursor()
            # query the database for a list of all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            # list of tables that should be in the database
            expected_tables = ['products', 'requirements', 'rules']
            # check if the expected tables are present
            # if they're present, return true, if not return false
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
            # return false if a database error occurs
            return False
        finally:
            # if we connected to the database, close the connection
            if connection:
                connection.close()

    else:
        # if the database file was not found return false
        print("local_inventory.db: Not found")
        return False


def display_quote(hero, quantity, accessories, warnings=None):
    """This function is the main formatting tool for displaying job quotes to the user after they're generated
    it takes in the item, quantity, list of accessories, and any stock warnings"""

    main_total = float(hero['price']) * quantity

    print("\n" + "-" * 60)
    print(f"{'Quote':^60}")
    print("-" * 60)
    print(f"Main Item: {hero['brand']} {hero['name']} ({hero['sub_type']})")
    print(f"Quantity: {quantity} {hero['unit']}")
    print(f"Subtotal: ${main_total:,.2f}")

    # check if there are any accessories to recommend
    # if not, skip the accessories section
    # if there are, print their details and add their prices to the grand total
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

    # if there are stock level warnings, print them after the main quote
    if warnings:
        print("\n" + "!" * 20 + " STOCK ALERTS " + "!" *20)
        for msg in warnings:
            print(f"{msg}")
        print("!" * 54)

    print("-" * 60 + "\n")

def get_stock_level(product_id):
    """This function checks the stock level of a product"""

    connection = None
    try:
        # establish the connection to the database
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # grab the inventory count of th eproduct
        sql_query = "SELECT inventory FROM products WHERE id = ?"
        cursor.execute(sql_query, (product_id,))
        item = cursor.fetchone()

        # if the product id number isn't found in the database, warn the user and exit the function
        if not item:
            print(f"Error: product with id {product_id} not found.")
            return None

        # otherwise, return the inventory count of the given product
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
    """This function grabs the restock information of a given product"""

    connection = None
    try:
        # connect to the database
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # grab the restock information of the given product
        sql_query = "SELECT incoming, restock_date FROM products WHERE id = ?"
        cursor.execute(sql_query, (product_id,))
        item = cursor.fetchone()

        # if the item isn't found, warn the user and exit the function
        if not item:
            print(f"Error: product with id {product_id} not found.")
            return None

        # return the incoming stock amount and the date
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
    """This function takes in a product id number and a quantity and generates a quote for that product and also
    recommends appropriate accessory add-ons based on the product being quoted"""

    connection = None
    try:
        # connect to the database
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # grab the product info from the database
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        item = cursor.fetchone()

        # if the product id number isn't found in the database, warn the user and exit the function
        if not item:
            print(f"Error: {product_id} not found.")
            return

        # create a list of warnings for low- or no-stock items
        stock_warnings = []
        current_stock = item['inventory']
        if quantity > current_stock:
            restock_qty, restock_date = get_restock_info(product_id)
            if restock_qty > 0:
                stock_warnings.append(
                    f"MAIN ITEM: {item['name']} ({item['sub_type']})\n"
                    f"           Only {current_stock} on hand. (Need {quantity:.2f})\n"
                    f"           {restock_qty} more arriving {restock_date}."
                )
            else:
                stock_warnings.append(
                    f"MAIN ITEM: {item['name']} ({item['sub_type']})\n"
                    f"           Only {current_stock} on hand. (Need {quantity:.2f})\n"
                    f"           There are no currently incoming shipments."
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
        accessory_color = item['sub_type']
        if item['category'] == "Siding" and rule == "Optional":
            choice = input(f"Accessories match {item['sub_type']}? (y/n): ").lower()
            if choice == 'n':
                accessory_color = input("Enter accessory sub-type or color: ").capitalize()

        # grab the accessories' information
        sql_query = """
                    SELECT p.brand, p.name, p.price, p.inventory, p.incoming, p.restock_date, r.quantity_multiplier, p.unit
                    FROM products p
                    JOIN requirements r ON p.sub_category = r.required_accessory
                    WHERE r.category = ? 
                      AND p.brand = ? 
                      AND (p.sub_type = ? OR p.sub_type = 'Universal')
                """
        cursor.execute(sql_query, (item['category'], item['brand'], accessory_color))
        accessories = cursor.fetchall()

        for acc in accessories:
            # calculate how many are needed based on the hero quantity
            needed_qty = math.ceil(quantity * acc['quantity_multiplier'])
            if needed_qty > acc['inventory']:
                if acc['incoming'] > 0:
                    stock_warnings.append(
                        f"ACCESSORY: {acc['name']} ({accessory_color})\n"
                        f"           Only {acc['inventory']} on hand (Need {needed_qty}).\n"
                        f"           {acc['incoming']} more arriving {acc['restock_date']}."
                    )
                else:
                    stock_warnings.append(
                        f"ACCESSORY: {acc['name']} ({accessory_color})\n"
                        f"           Only {acc['inventory']} on hand (Need {needed_qty}).\n"
                        f"           There are no currently incoming shipments."
                    )

        # call the function to display the quote with the add-on recommendations
        display_quote(item, quantity, accessories, stock_warnings)

    except sqlite3.Error as e:
        print(f"Error: Database error occurred:\n{e}")
    finally:
        if connection:
            connection.close()


def display_inventory_list(only_heroes=True):
    """This function creates and displays a list of all of the items in the database, the default option only
    displays "hero" products, with the option to display all products"""

    connection = None
    try:
        # connect to the database
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row  # Use names, not indices!
        cursor = connection.cursor()

        # select either all of the products, or only the hero products depending on the value of only_heroes
        query = "SELECT id, category, brand, name, sub_type FROM products"
        if only_heroes:
            query += " WHERE sub_category = 'Hero'"
        cursor.execute(query)
        rows = cursor.fetchall()

        # print the list of products
        print(f"\n{'ID':<7} | {'Category':<10} | {'Brand':<15} | {'Name':<30} | {'Sub-Type'}")
        print("-" * 80)
        for row in rows:
            print(f"{row['id']:<7} | {row['category']:<10} | {row['brand']:<15} | {row['name']:<30} | {row['sub_type']}")

    except sqlite3.Error as e:
        print(f"Error: Database error occurred:{e}")
    finally:
        if connection:
            connection.close()

def main_menu():
    """This is the main menu function which serves as the main interface of the application"""

    while True:
        print(f" ----- Main Menu -----")
        print("01: Generate A Quote")
        print("02: List Hero Products")
        print("03: List All Products")
        print("99: Exit")

        # get the user's menu selection
        choice = input("\nEnter Selection: ")

        #check the user's input choice
        match choice:
            case '01':
                p_id = input("Enter Product ID: ")
                try:
                    # get a positive quantity
                    qty = float(input("Enter Quantity: "))
                    if qty <= 0:
                        raise ValueError("Invalid quantity. Please enter a positive number greater than 0")
                    # if the product id and the quantity are appropriate, generate the quote as requested
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

# ----- EXECUTION BLOCK -----

if __name__ == "__main__":
    # initialize the database
    initialize_local_database()
    if check_setup():
        # launch the interactive menu
        main_menu()
    else:
        print("Setup check failed. You may need to manually verify your CSV files and database.")