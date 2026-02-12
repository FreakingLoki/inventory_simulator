import os
import sys
import math
import sqlite3
import pandas as pd



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

def generate_quote(main_inventory, product_id, quantity):
    if product_id not in main_inventory:
        print(f"Product with id {product_id} not found!")
        return

    main_item = main_inventory[product_id]
    main_total = float(main_item['price']) * quantity

    print(f"------------------------------------------------------------------------------------------")
    print(f"--------------------------------- BUILDING PRODUCT QUOTE ---------------------------------")
    print(f"------------------------------------------------------------------------------------------")
    print(f"{main_item['name']} ({main_item['color']})")
    print(f"Quantity: {quantity} {main_item['unit']}")
    print(f"Base Price: ${main_total:,.2f}")
    print(f"----------------------------------- SUGGESTED ADD-ONS ------------------------------------")

    grand_total = main_total

    for acc_name in main_item['accessories']:
        # need to find the accessor object to get its price
        acc_item = next((item for item in main_inventory.values() if item['name'] == acc_name), None)

        if acc_item:
            # add 2 pieces of trim and starter per quare of siding
            # add 1 box of nails per 5 squares
            if "Nails" in acc_name:
                acc_qty = math.ceil(quantity / 5)
            else:
                acc_qty = math.ceil(quantity * 2)

            acc_cost = float(acc_item['price']) * acc_qty
            grand_total += acc_cost
            print(f"- {acc_name:.<25} qty: {acc_qty:>2} | ${acc_cost:>8,.2f}")

    print(f"-------------------------------------- GRAND TOTAL ---------------------------------------")
    print(F"Total Before Accessories: ${main_total:,.2f}")
    print(f"Total Incl. Accessories: ${grand_total:,.2f}")

def main_menu(main_inventory):
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

                # check for a valid product id
                if p_id not in main_inventory:
                    print(f"Error: Product ID '{p_id}' not found.")
                    continue

                try:
                    qty = float(input("Enter Quantity (Squares): "))
                    generate_quote(main_inventory, p_id, qty)
                except ValueError:
                    print("Invalid quantity. Please enter a number.")

            case '02':
                print("ID | Category | Name | Color")
                print("-" * 40)
                for p in main_inventory.values():
                    # only show 'Hero' products, not accessories
                    if p['category'] == 'Siding':
                        print(f"{p['id']: <3} | {p['category']: <7} | {p['name']: <20} | {p['color']}")

            case '03':
                print("ID | Category | Name | Color")
                print("-" * 40)
                for p in main_inventory.values():
                    print(f"{p['id']: <3} | {p['category']: <7} | {p['name']: <20} | {p['color']}")

            case '99':
                print("Exiting...")
                break

            case _:
                print("Invalid choice, try again.")



if __name__ == "__main__":
    # verify environment setup
    check_setup()
    # load inventory information
    inventory = load_data()

    # launch the interactive menu
    main_menu(inventory)