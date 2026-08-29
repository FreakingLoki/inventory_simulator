import math
import sqlite3

DB_FILE = 'wms_normalized.db'

SIDING_FACTORS = {
    "stick_length": 12.5, "window_j_ft": 13.0, "window_finish_ft": 3.0,
    "door_j_ft": 16.5, "gable_pitch_mult": 1.25, "sqft_per_square": 100.0,
    "corner_post_length": 10.0, "avg_wall_height": 9.0
}
ROOFING_FACTORS = {
    "bundle_per_square": 3.0, "ridge_cap_coverage": 30.0, "starter_coverage": 100.0,
    "ice_water_sqft": 200.0, "ice_water_width_ft": 3.0, "underlayment_sqft": 1000.0,
    "sqft_per_square": 100.0
}
SHEETROCK_FACTORS = {
    "sqft_per_panel": 32.0, "tape_coverage": 50.0, "screws_sqft_per_pound": 150,
    "mud_sqft_per_pail": 600
}
INSULATION_FACTORS = {
    "sqft_per_bag": 50.0, "sqft_per_board": 32.0, "sqft_per_roll": 100.0,
    "sqft_per_wire_box": 200
}


def display_quote(hero, quantity, accessories, warnings=None):
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
            print(f"- {acc['brand']} {acc['name']:.<35} qty: {acc_qty:>3} | ${acc_cost:>10,.2f}")
        print("-" * 60)
        print(f"{'Total Before Accessories:':<45} ${main_total:>12,.2f}")
        print(f"{'Grand Total (Including Accessories):':<45} ${grand_total:>12,.2f}")

    if warnings:
        print("\n" + "!" * 20 + " STOCK ALERTS " + "!" * 20)
        for msg in warnings:
            print(f"{msg}")
        print("!" * 54)
    print("-" * 60 + "\n")


def get_calculation_mode():
    print("\n--- Accessory Calculation Options ---")
    print("01: Standard Estimate (Uses industry-average ratios)")
    print("02: Site-Specific Estimate (Enter window/door/corner counts)")
    print("03: Custom Quantities (Enter exact accessory counts)")
    print("04: Skip Add-ons (Quote hero product only)")
    return int(input("\nSelect Calculation Method: "))


def get_site_specs(category):
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
    specs = get_site_specs(category)
    calculated_results = {}
    final_hero_qty = hero_qty

    if category == "Siding":
        if final_hero_qty is None:
            final_hero_qty = math.ceil(specs['total_wall_sqft'] / SIDING_FACTORS['sqft_per_square'])
        total_j_ft = (specs['windows'] * SIDING_FACTORS['window_j_ft']) + (
                    specs['doors'] * SIDING_FACTORS['door_j_ft']) + (
                                 specs['gable_width'] * SIDING_FACTORS['gable_pitch_mult'])
        calculated_results['J-Channel'] = math.ceil(total_j_ft / SIDING_FACTORS['stick_length']) / final_hero_qty
        calculated_results['Finish Trim'] = math.ceil(
            ((specs['windows'] * SIDING_FACTORS['window_finish_ft']) + specs['foundation_ft']) / SIDING_FACTORS[
                'stick_length']) / final_hero_qty
        posts = math.ceil(SIDING_FACTORS['avg_wall_height'] / SIDING_FACTORS['corner_post_length'])
        calculated_results['Outside Corner Post'] = (specs['outside_corners'] * posts) / final_hero_qty
        calculated_results['Inside Corner Post'] = (specs['inside_corners'] * posts) / final_hero_qty
        calculated_results['Starter Strip'] = math.ceil(
            specs['foundation_ft'] / SIDING_FACTORS['stick_length']) / final_hero_qty

    elif category == "Roofing":
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

    elif category == "Sheetrock":
        if final_hero_qty is None:
            final_hero_qty = math.ceil(specs['total_sqft'] / SHEETROCK_FACTORS['sqft_per_panel'])
        calculated_results['Screws'] = math.ceil(
            specs['total_sqft'] / SHEETROCK_FACTORS['screws_sqft_per_pound']) / final_hero_qty
        calculated_results['Mud'] = math.ceil(
            specs['total_sqft'] / SHEETROCK_FACTORS['mud_sqft_per_pail']) / final_hero_qty
        calculated_results['Tape'] = math.ceil(
            specs['total_sqft'] / SHEETROCK_FACTORS['tape_coverage']) / final_hero_qty

    elif category == "Insulation":
        if final_hero_qty is None:
            final_hero_qty = math.ceil(specs['total_sqft'] / INSULATION_FACTORS['sqft_per_bag'])
        calculated_results['6-mil Poly Vapor Barrier'] = math.ceil(
            specs['total_sqft'] / INSULATION_FACTORS['sqft_per_roll']) / final_hero_qty
        calculated_results['Insulation Fabric Backing'] = math.ceil(
            specs['total_sqft'] / INSULATION_FACTORS['sqft_per_roll']) / final_hero_qty
        calculated_results['Insulation Support Wires'] = math.ceil(
            specs['total_sqft'] / INSULATION_FACTORS['sqft_per_wire_box']) / final_hero_qty

    return final_hero_qty, calculated_results


def generate_quote(product_id):
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        sql_hero = """
            SELECT p.product_id as id, b.brand_name as brand, c.category_name as category, 
                   sc.sub_category_name as sub_category, p.product_name as name, 
                   p.sub_type, p.unit, p.unit_price as price, i.quantity_on_hand as inventory, 
                   i.quantity_incoming as incoming, i.expected_restock_date as restock_date
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

        sql_acc_base = """
            SELECT p.product_id as id, b.brand_name as brand, p.product_name as name, 
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
            cursor.execute(
                sql_acc_base + " AND sc.sub_category_name IN (SELECT required_accessory FROM requirements WHERE category = ?)",
                (item['category'], item['brand'], item['sub_type'], item['category']))
            raw_accs = [dict(row) for row in cursor.fetchall()]
            for acc in raw_accs:
                cursor.execute("SELECT quantity_multiplier FROM requirements WHERE required_accessory = ?",
                               (acc['sub_category'],))
                mult_row = cursor.fetchone()
                acc['quantity_multiplier'] = mult_row['quantity_multiplier'] if mult_row else 0
                final_accessories.append(acc)
        elif mode == 2:
            final_hero_qty, site_multipliers = calculate_site_specific(item['category'], None)
            cursor.execute(sql_acc_base + " AND sc.sub_category_name != 'Hero'",
                           (item['category'], item['brand'], item['sub_type']))
            for row in cursor.fetchall():
                acc_dict = dict(row)
                acc_dict['quantity_multiplier'] = site_multipliers.get(acc_dict['sub_category'], 0)
                if acc_dict['quantity_multiplier'] > 0:
                    final_accessories.append(acc_dict)
        elif mode == 3:
            final_hero_qty = float(input(f"Enter quantity of {item['unit']}s: "))
            cursor.execute(sql_acc_base + " AND sc.sub_category_name != 'Hero'",
                           (item['category'], item['brand'], item['sub_type']))
            print("\n--- Manual Accessory Entry ---")
            for row in cursor.fetchall():
                acc_dict = dict(row)
                user_count = float(input(f"How many {acc_dict['name']}? ") or 0)
                acc_dict['quantity_multiplier'] = user_count / final_hero_qty if final_hero_qty > 0 else 0
                if user_count > 0:
                    final_accessories.append(acc_dict)

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
            "hero": item, "quantity": final_hero_qty,
            "accessories": final_accessories, "warnings": stock_warnings
        }
    except ValueError:
        print("Error: Invalid input. Please enter numeric values.")
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
    finally:
        if connection:
            connection.close()