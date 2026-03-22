# ----- IMPORTS SECTION -----

import os
import sys
import math
import sqlite3
import pandas as pd

# ----- GLOBAL CONSTANTS -----

SIDING_FACTORS = {
    "stick_length": 12.5,       # all siding accessories are sold in 12.5 ft lengths
    "window_j_ft": 13.0,        # linear feet of j-channel, on average, per window
    "window_finish_ft": 3.0,    # linear feet of finish trim per window
    "door_j_ft": 16.5,          # linear feet of j-channel for an average exterior door
    "gable_pitch_mult": 1.25,   # multiplier for the bottom edge of roof gables
    "sqft_per_square": 100.0,   # conversion between 'squares' and square feet
    "corner_post_length": 10.0, # inside and outside corners are sold in 10 foot lengths
    "avg_wall_height": 9.0,     # the height of an average wall, used for corner post estimates
}

ROOFING_FACTORS = {
    "bundle_per_square": 3.0,       # three bundles cover 100 sqft
    "ridge_cap_coverage": 30.0,     # each bundle of cap covers 30 ft of ridge
    "starter_coverage": 100.0,      # each bundle of shingle starter covers 100 ft of edge
    "ice_water_sqft": 200.0,        # the ice and water rolls cover 200 sqft
    "ice_water_width_ft": 3.0,      # standard width of a roll
    "underlayment_sqft": 1000.0,  # the underlayment rolls cover 1000 sqft
    "sqft_per_square": 100.0        # conversion between 'squares' and square feet
}

SHEETROCK_FACTORS = {
    "sqft_per_panel": 32.0,         # square feet of coverage per panel
    "tape_coverage": 50.0,          # linear feet of coverage per roll of tape
    "screws_sqft_per_pound": 150,    # square feet of coverage per pound of nails
    "mud_sqft_per_pail": 600,       # square feet of coverage per pail of mud
}

INSULATION_FACTORS = {
    "sqft_per_bag": 50.0,       # square feet of wall coverage per bag of insulation
    "sqft_per_board": 32.0,     # square feet of wall coverage per foam board
    "sqft_per_roll": 100.0,     # square feet of wall coverage per accessory roll
    "sqft_per_wire_box": 200,   # square feet of material supported per box of wire supports
}

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
        customers_df = pd.read_csv('customers.csv')
        orders_df = pd.read_csv('orders.csv')

        # load the data into SQL tables from the DataFrames
        # the 'replace' tag ensures that if the CSV files are updated, the database is updated when the program is launched
        products_df.to_sql('products', connection, if_exists='replace', index=False)
        requirements_df.to_sql('requirements', connection, if_exists='replace', index=False)
        rules_df.to_sql('rules', connection, if_exists='replace', index=False)
        customers_df.to_sql('customers', connection, if_exists='replace', index=False)
        orders_df.to_sql('orders', connection, if_exists='replace', index=False)

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

        # grab the inventory count of the product
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
    """This function grabs the restocking information of a given product"""

    connection = None
    try:
        # connect to the database
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # grab the restocking information of the given product
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

def get_calculation_mode():
    """Prompts the user to determine how they'd like to handle calculation accessory add-ons"""

    print("\n--- Accessory Calculation Options ---")
    print("01: Standard Estimate (Uses industry-average ratios)")
    print("02: Site-Specific Estimate (Enter window/door/corner counts)")
    print("03: Custom Quantities (Enter exact accessory counts)")
    print("04: Skip Add-ons (Quote hero product only)")

    choice = int(input("\nSelect Calculation Method: "))
    return choice

def get_site_specs(category):
    """This function collect job-site measurements and counts for more precise quotes (calc mode 2)"""

    specs = {}

    if category == "Siding":
        print("\n--- Siding Site Details ---")
        specs['windows'] = int(input("Number of Windows: ") or 0)
        specs['doors'] = int(input("Number of Doors: ") or 0)
        specs['foundation_ft'] = float(input("Total Foundation Linear Feet: ") or 0)
        specs['gable_width'] = float(input("Total Width of Gable Bases (ft): ") or 0)
        specs['outside_corners'] = int(input("Number of Outside Corners: ") or 0)
        specs['inside_corners'] = int(input("Number of Inside Corners: ") or 0)


    elif category == "Roofing":
        print("\n--- Roofing Site Details ---")
        specs['ridges_ft'] = float(input("Total Linear Feet of Ridges: ") or 0)
        specs['eaves_ft'] = float(input("Total Linear Feet of Eaves: ") or 0)
        specs['rakes_ft'] = float(input("Total Linear Feet of Rakes: ") or 0)
        specs['valleys_ft'] = float(input("Total Linear Feet of Valleys: ") or 0)
        specs['total_sqft'] = float(input("Total Roof Square Footage (Deck Area): ") or 0)

    elif category == "Sheetrock" or "Insulation":
        print(f"\n--- {category} Site Details ---")
        specs['square_ft'] = float(input("Total Square Feet of Wall") or 0)

    return specs

def calculate_site_specific(category, hero_qty):
    """This function takes in a product category and prompts the user for site-specific numbers to calculate
    a much more accurate job quote with less over/under ordering. If hero_qty is None, it also calculates the
    required amount of hero product"""

    # start by getting the site specific information
    specs = get_site_specs(category)
    # a container dictionary with {accessory_name: new_multiplier}
    calculated_results = {}
    final_hero_qty = hero_qty

    match category:
        case "Siding":
            # ----- Hero Product -----
            # if the user provides a total wall area, override the hero_qty
            if final_hero_qty is None:
                final_hero_qty = math.ceil(specs['total_wall_sqft'] / SIDING_FACTORS['sqft_per_square'])

            # ----- J-Channel -----
            # use the site-specific counts of openings with the multipliers from the siding dictionary to determine the
            # total feet of j-channel required
            total_j_ft = (specs['windows'] * SIDING_FACTORS['window_j_ft']) + \
                         (specs['doors'] * SIDING_FACTORS['door_j_ft']) + \
                         (specs['gable_width'] * SIDING_FACTORS['gable_pitch_mult'])

            # divide by stick length and then again by hero_qty to turn this number back into a multiplier
            # this allows us to use display_quote()
            j_sticks = math.ceil(total_j_ft / SIDING_FACTORS['stick_length'])
            calculated_results['J-Channel'] = j_sticks / final_hero_qty

            # ----- Finish Trim -----
            # finish trim for underneath windows and along the top of non-gable walls
            total_finish_ft = (specs['windows'] * SIDING_FACTORS['window_finish_ft']) + \
                              specs['foundation_ft']  # assuming top of wall = foundation length
            finish_sticks = math.ceil(total_finish_ft / SIDING_FACTORS['stick_length'])
            calculated_results['Finish Trim'] = finish_sticks / final_hero_qty

            # ----- Outside Corner Posts -----
            # each corner needs posts based on wall height
            posts_per_corner = math.ceil(SIDING_FACTORS['avg_wall_height'] / SIDING_FACTORS['corner_post_length'])
            calculated_results['Outside Corner Post'] = (specs['outside_corners'] * posts_per_corner) / final_hero_qty

            # ----- Inside Corner Posts -----
            # calculated based on the number of inside corners
            posts_per_corner = math.ceil(SIDING_FACTORS['avg_wall_height'] / SIDING_FACTORS['corner_post_length'])
            calculated_results['Inside Corner Post'] = (specs['inside_corners'] * posts_per_corner) / final_hero_qty

            # ----- Starter Strip -----
            # calculated based on the linear feet of foundation, or the bottom edge of the wall
            starter_sticks = math.ceil(specs['foundation_ft'] / SIDING_FACTORS['stick_length'])
            calculated_results['Starter Strip'] = starter_sticks / final_hero_qty

        case "Roofing":
            # ----- Hero Product -----
            if final_hero_qty is None:
                # calculate the required quantity of bundles
                squares = specs['total_sqft'] / ROOFING_FACTORS['sqft_per_square']
                final_hero_qty = math.ceil(squares * ROOFING_FACTORS['bundle_per_square'])

            # ----- Ridge Cap -----
            # divide total feet by feet per bundle to calculate the number of bundles
            bundles_ridge_cap = math.ceil(specs['ridges_ft'] / ROOFING_FACTORS['ridge_cap_coverage'])
            calculated_results['Ridge Cap'] = bundles_ridge_cap / final_hero_qty

            # ----- Shingle Starter -----
            # shingle starter covers the edges of the eaves and rakes of the roof
            # calculate by adding linear feet of eaves and rakes, then dividing by coverage per bundle
            bundles_shingle_starter = math.ceil((specs['eaves_ft'] + specs['rakes_ft']) / ROOFING_FACTORS['starter_coverage'])
            calculated_results['Shingle Starter'] = bundles_shingle_starter / final_hero_qty

            # ----- Ice and Water Shield -----
            # two rows along the eaves and one along valleys
            # calculate the required square footage, then divide by the square footage per roll
            eave_area = specs['eaves_ft'] * 6.0
            valley_area = specs['valleys_ft'] * 3.0
            total_ice_water_sqft = eave_area + valley_area
            rolls_ice_water = math.ceil(total_ice_water_sqft / ROOFING_FACTORS['ice_water_sqft'])
            calculated_results['Ice and Water Shield'] = rolls_ice_water / final_hero_qty

            # ----- Synthetic Underlayment -----
            # total roof area minus the area already covered by ice and water
            remaining_area = specs['total_sqft'] - total_ice_water_sqft
            if remaining_area < 0: remaining_area = 0

            rolls_underlayment = math.ceil(remaining_area / ROOFING_FACTORS['underlayment_sqft'])
            calculated_results['Synthetic Underlayment'] = rolls_underlayment / final_hero_qty

        case "Sheetrock":
            # ----- Hero Product -----
            if final_hero_qty is None:
                final_hero_qty = math.ceil(specs['total_sqft'] / SHEETROCK_FACTORS['sqft_per_panel'])

            # ----- Screws -----
            boxes_screws = math.ceil(specs['total_sqft'] / SHEETROCK_FACTORS['screws_sqft_per_pound'])
            calculated_results['Screws'] = boxes_screws / final_hero_qty

            # ----- Mud -----
            pails_mud = math.ceil(specs['total_sqft'] / SHEETROCK_FACTORS['mud_sqft_per_pail'])
            calculated_results['Mud'] = pails_mud / final_hero_qty

            # ----- Tape -----
            rolls_tape = math.ceil(specs['total_sqft'] / SHEETROCK_FACTORS['tape_coverage'])
            calculated_results['Tape'] = rolls_tape / final_hero_qty

        case "Insulation":
            # ----- Hero Product -----
            if final_hero_qty is None:
                final_hero_qty = math.ceil(specs['total_sqft'] / INSULATION_FACTORS['sqft_per_bag'])

            # ----- Vapor Barrier -----
            rolls_barrier = math.ceil(specs['total_sqft'] / INSULATION_FACTORS['sqft_per_roll'])
            calculated_results['6-mil Poly Vapor Barrier'] = rolls_barrier / final_hero_qty

            # ----- Fabric Backing -----
            rolls_backing = math.ceil(specs['total_sqft'] / INSULATION_FACTORS['sqft_per_roll'])
            calculated_results['Insulation Fabric Backing'] = rolls_backing / final_hero_qty

            # ----- Support Wires -----
            support_wires = math.ceil(specs['total_sqft'] / INSULATION_FACTORS['sqft_per_wire_box'])
            calculated_results['Insulation Support Wires'] = support_wires / final_hero_qty
        case _:
            print(f"Error, category {category} not found or invalid.")

    return final_hero_qty, calculated_results

def calculate_custom_quantities(hero_qty, accessories):
    """This function allows the user to manually enter exact accessory counts"""

    calculated_results = {}

    print("\n--- Manual Accessory Entry ---")
    for acc in accessories:
        try:
            # ask for the total count of each item they want
            count = float(input(f"Enter quantity for {acc['name']} ({acc['sub_type']}): ") or 0)
            calculated_results[acc['name']] = count /hero_qty
        except ValueError:
            calculated_results[acc['name']] = 0

    return calculated_results

def find_customer(account_number):
    """Fetches a customer's information from the local database"""

    customer_id = None
    connection = None
    try:
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_query = "SELECT * FROM customers WHERE account_number = ?"
        cursor.execute(sql_query, (account_number,))
        customer = cursor.fetchone()

        if customer:
            # if the customer was found, return the customer as a Python dictionary
            return dict(customer)
        else:
            print(f"Error, Account #{account_number} not found.")
            return None
    except Exception as e:
        print(f"Error:\n{e}")
    finally:
        if connection:
            connection.close()

def generate_quote(product_id):
    """
    The master controller for quote generation.
    1. Fetches the main (Hero) product.
    2. Determines the calculation mode (Standard, Site-Specific, Custom, or Skip).
    3. Calculates quantities for Hero and Accessories based on the chosen mode.
    4. Performs stock-level validation across all items.
    5. Displays the final formatted quote.
    """
    connection = None
    try:
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        # ----- fetch the hero product
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        item = cursor.fetchone()

        if not item:
            print(f"Error: Product ID {product_id} not found.")
            return

        # ----- determine the calculation mode and define the variables
        mode = get_calculation_mode()
        final_hero_qty = 0
        final_accessories = []  # This will store dictionaries of {brand, name, price, multiplier, etc.}
        stock_warnings = []

        # ----- calculation logic branches
        if mode == 4:  # SKIP ADD-ONS
            final_hero_qty = float(input(f"Enter quantity of {item['unit']}s: "))
            final_accessories = "None"

        elif mode == 1:  # STANDARD (ratio-based)
            final_hero_qty = float(input(f"Enter quantity of {item['unit']}s: "))
            # the standard mode SQL fetch uses requirements.csv
            sql_query = """
                SELECT p.brand, p.name, p.price, p.inventory, p.incoming, p.restock_date, r.quantity_multiplier, p.unit
                FROM products p
                JOIN requirements r ON p.sub_category = r.required_accessory
                WHERE r.category = ? AND p.brand = ? AND (p.sub_type = ? OR p.sub_type = 'Universal')
            """
            cursor.execute(sql_query, (item['category'], item['brand'], item['sub_type']))
            final_accessories = [dict(row) for row in cursor.fetchall()]

        elif mode == 2:  # SITE-SPECIFIC (precision math)
            # Pass None for qty so calculate_site_specific defines it from area
            final_hero_qty, site_multipliers = calculate_site_specific(item['category'], None)

            # fetch all possible accessories for this brand
            sql_query = """
                SELECT p.brand, p.name, p.price, p.inventory, p.incoming, p.restock_date, p.sub_category, p.unit
                FROM products p
                WHERE p.category = ? AND p.brand = ? AND (p.sub_type = ? OR p.sub_type = 'Universal')
                AND p.sub_category != 'Hero'
            """
            cursor.execute(sql_query, (item['category'], item['brand'], item['sub_type']))
            raw_accs = cursor.fetchall()

            # map the site-calculated multipliers to the database items
            for row in raw_accs:
                acc_dict = dict(row)
                # get the multiplier calculated in the math module
                # use .get() to default to 0 if an accessory isn't needed for this site
                acc_dict['quantity_multiplier'] = site_multipliers.get(row['sub_category'], 0)
                if acc_dict['quantity_multiplier'] > 0:
                    final_accessories.append(acc_dict)

        elif mode == 3:  # CUSTOM (manual entry)
            final_hero_qty = float(input(f"Enter quantity of {item['unit']}s: "))
            # fetch all matching accessories first
            cursor.execute("""
                SELECT p.brand, p.name, p.price, p.inventory, p.incoming, p.restock_date, p.unit
                FROM products p
                WHERE p.category = ? AND p.brand = ? AND (p.sub_type = ? OR p.sub_type = 'Universal')
                AND p.sub_category != 'Hero'
            """, (item['category'], item['brand'], item['sub_type']))
            raw_accs = cursor.fetchall()

            print("\n--- Manual Accessory Entry ---")
            for row in raw_accs:
                acc_dict = dict(row)
                user_count = float(input(f"How many {acc_dict['name']}? ") or 0)
                acc_dict['quantity_multiplier'] = user_count / final_hero_qty
                if user_count > 0:
                    final_accessories.append(acc_dict)

        # ----- stock validation
        # check hero
        if final_hero_qty > item['inventory']:
            in_qty, in_date = get_restock_info(product_id)
            msg = f"MAIN ITEM: {item['name']} - Need {final_hero_qty}, only {item['inventory']} on hand."
            if in_qty > 0: msg += f" ({in_qty} arriving {in_date})"
            stock_warnings.append(msg)

        # check accessories
        if final_accessories != "None":
            for acc in final_accessories:
                needed = math.ceil(final_hero_qty * acc['quantity_multiplier'])
                if needed > acc['inventory']:
                    msg = f"ACCESSORY: {acc['name']} - Need {needed}, only {acc['inventory']} on hand."
                    if acc['incoming'] > 0: msg += f" ({acc['incoming']} arriving {acc['restock_date']})"
                    stock_warnings.append(msg)

        # ----- final output
        # construct a dictionary of the quote data and return that
        quote_data = {
            "hero": item,
            "quantity": final_hero_qty,
            "accessories": final_accessories,
            "warnings": stock_warnings
        }
        return quote_data

    except ValueError:
        print("Error: Invalid input. Please enter numeric values for quantities.")
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        if connection:
            connection.close()

def display_inventory_list(only_heroes=True):
    """This function creates and displays a list of all the items in the database, the default option only
    displays "hero" products, with the option to display all products"""

    connection = None
    try:
        # connect to the database
        connection = sqlite3.connect('local_inventory.db')
        connection.row_factory = sqlite3.Row  # Use names, not indices!
        cursor = connection.cursor()

        # select either all the products, or only the hero products depending on the value of only_heroes
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

def handle_quote_actions(quote_data, customer=None):
    """Displays the generated quote and gives the user choices to:
    1. Finalize Order
    2. Modify Quantities
    3. Discard"""

    while True:
        # calculate the grand total here for the display function
        hero_total = quote_data['hero']['price'] * quote_data['quantity']
        accessory_total = sum((acc['price'] * math.ceil(quote_data['quantity'] * acc['quantity_multiplier']))
                        for acc in quote_data['accessories'])
        grand_total = hero_total + accessory_total

        # call the display_quote function, passing the totals to it
        display_quote(quote_data['hero'], quote_data['quantity'], quote_data['accessories'], quote_data['warnings'])

        # if a customer account was selected
        if customer:
            print(f" --- Customer: {customer['customer_name']} --- ")
        else:
            print(f" --- Guest Quote ---")
        print("01: Submit and Finalize Order")
        print("02: Modify Quantities (Add/Remove items)")
        print("03: Discard Quote")

        choice = input("\nEnter Selection: ")

        match choice:
            case "01":
                # submit and finalize order
                if customer:
                    # run a credit check
                    allowed, message = check_credit_status(customer, grand_total)
                    if not allowed:
                        print(f"\n{message}")
                        continue # return to the menu to modify the order or discard it

                    # if the credit check passes, move on to the final step
                    submit_order(quote_data, customer, grand_total)
                    break

            case "02":
                # modify quantities and add or remove items
                # this logic will be built later
                print("Quote modification coming soon...")
            case "03":
                # discard the quote and do not save to order history
                confirmation = input("Are you sure you'd like to discard this quote? (y/n): ")
                if confirmation == "y":
                    print("Quote discarded")
                    break
                else:
                    print(f"You entered {confirmation}, returning to quote options menu...")
                    continue

def start_quote_flow():
    """This function is called when the user wants to generate a quote. It runs all related functions for quote
    generation."""

    # get the product id number
    product_id = int(input("Enter Product ID: "))

    # get the customer account number
    print("\n ----- Customer Selection -----")
    account_number = int(input("Enter Customer Account Number or 0 for Guest: "))
    if account_number != 0:
        current_customer = find_customer(account_number)
        if not current_customer:
            # for now, default to guest mode if the account number isn't found
            print(f"Account {account_number} not found, proceeding as Guest...")

    # begin the quote process
    quote_data = generate_quote(product_id)




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
                generate_quote(p_id)


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