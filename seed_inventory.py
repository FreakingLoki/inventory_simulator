import csv
import math


class BaseCategory:
    """The blueprint for all product categories."""

    def __init__(self, brand_name, markup, start_id):
        self.brand_name = brand_name
        self.markup = markup
        self.current_id = start_id
        self.products = []

    def get_next_id(self):
        self.current_id += 1
        return self.current_id

    def add_product(self, category, sub_category, name, sub_type, unit, base_price, inventory=50):
        """ Helper method to format and store a product entry"""
        self.products.append({
            "id": self.get_next_id(),
            "brand": self.brand_name,
            "category": category,
            "sub_category": sub_category,
            "name": name,
            "sub_type": sub_type,
            "unit": unit,
            "price": round(base_price * self.markup, 2),
            "inventory": inventory,
            "incoming": 0,
            "restock_date": "0/00/0000"
        })


class SidingCategory(BaseCategory):
    """Specific logic for generating Siding and its unique accessories."""

    def generate_siding(self):
        profiles = {
            "Double-4": 180.00,
            "Board and Batten": 210.00,
            "Dutchlap": 195.00,
            "Shake-Style": 280.00
        }
        standard_colors = ["Snow White", "Pebble", "Sandstone", "Midnight Blue", "Sage Green", "Honeycrisp", "Iron Grey",
                           "Sky Blue", "Coffe", "Olive", "Burgundy", "Sunset"]

        # 1. Generate Hero Profiles
        for profile, price in profiles.items():
            for color in standard_colors:
                self.add_product("Siding", "Hero", f"{profile} Siding", color, "Square", price)

        # 2. Generate Standard Accessories
        acc_types = {"J-Channel": 12.50, "Finish Trim": 15.00, "Starter Strip": 10.00, "Trim Nails (1lb)": 8.50}
        for acc, price in acc_types.items():
            for color in standard_colors:
                self.add_product("Siding", acc, acc, color, "PC", price, inventory=100)

        # 3. Special Stone-Style Section
        stone_colors = ["Dark Grey", "Light Grey", "Sandy Tan"]
        for color in stone_colors:
            self.add_product("Siding", "Hero", "Luxury Stone-Style Siding", color, "Square", 450.00)
            # Stone-specific accessories
            self.add_product("Siding", "Stone Ledge", "Stone Ledge", color, "PC", 45.00)
            self.add_product("Siding", "Stone Corner", "Stone Corner", color, "PC", 65.00)


class RoofingCategory(BaseCategory):
    """Specific logic for generating Shingle Roofing and accessories."""

    def generate_roofing(self):
        # Define styles based on brand tier
        # We can check the markup to decide which styles to add
        styles = {"3-Tab": 90.00}  # Everyone gets budget 3-tab

        if self.markup >= 1.15:  # Mid-tier and Premium get the fancy stuff
            styles["Architectural"] = 125.00
            styles["Executive Slate-Style"] = 210.00

        colors = ["Onyx Black", "Estate Grey", "Weathered Wood", "Brick Red", "Forest Green", "Desert Tan"]

        # 1. Generate Hero Shingles
        for style, price in styles.items():
            for color in colors:
                # Shingles are sold by the 'Bundle' (usually 3 bundles per square)
                self.add_product("Roofing", "Hero", f"{style} Shingles", color, "Bundle", price)

        # 2. Generate Brand-Specific Accessories
        # These are usually standard colors or universal
        accessories = {
            "Ridge Cap": 45.00,  # Matches colors
            "Starter Strip": 35.00,  # Universal/Black
            "Ice and Water Shield": 85.00,  # Roll
            "Synthetic Underlayment": 110.00  # Roll
        }

        for acc, price in accessories.items():
            if acc == "Ridge Cap":
                for color in colors:
                    self.add_product("Roofing", acc, acc, color, "Bundle", price)
            else:
                # These are universal items, usually don't need color matching
                self.add_product("Roofing", acc, acc, "Universal", "Roll", price)

class SheetrockCategory(BaseCategory):
    """Specific logic for generating Drywall/Sheetrock and accessories."""
    def generate_sheetrock(self):
        # 1. Generate the Boards (Hero Products)
        # Structure: {Sub-category: (Base Price, Thickness/Description, Sub-Type)}
        boards = {
            "Thin Profile": (14.50, "1/4-inch x 4x8", "Standard"),
            "Standard Profile": (16.00, "1/2-inch x 4x8", "Standard"),
            "Moisture Resistant": (21.00, "1/2-inch x 4x8", "Green"),
            "Fire Resistant": (24.00, "5/8-inch x 4x8", "Type X")
        }

        for sub, details in boards.items():
            price, size, sub_type = details
            self.add_product(
                category="Sheetrock",
                sub_category="Hero",
                name=f"{size} {sub}",
                sub_type=sub_type,
                unit="Sheet",
                base_price=price
            )

        # 2. Generate Accessories
        # Screws
        self.add_product("Sheetrock", "Screws", "1-1/4 inch Drywall Screws", "Standard", "Box", 12.00)
        self.add_product("Sheetrock", "Screws", "1-5/8 inch Drywall Screws", "Type X", "Box", 12.00)

        # Joint Compound (Mud)
        self.add_product("Sheetrock", "Mud", "All-Purpose Joint Compound", "Standard", "Bucket", 18.00)
        self.add_product("Sheetrock", "Mud", "Heavy Duty Taping Compound", "Standard", "Bucket",
                         22.00)  # Optional secondary
        self.add_product("Sheetrock", "Mud", "Moisture Resistant Mud", "Green", "Bucket", 28.00)

        # Tape
        self.add_product("Sheetrock", "Tape", "Fiberglass Mesh Tape", "Universal", "Roll", 7.50)

class InsulationCategory(BaseCategory):
    """Logic for generating various insulation types and accessories."""
    def generate_insulation(self):
        # 1. Hero Products
        # Material: (Base Price, Unit, List of R-Values)
        styles = {
            "Fiberglass Batt": (45.00, "Bag", ["R-13", "R-19", "R-30"]),
            "Woodfiber Batt": (65.00, "Bag", ["R-13", "R-21", "R-30"]), # TimberHP style
            "Blowing Wool": (35.00, "Bag", ["R-38", "R-49", "R-60"]),
            "Rigid Foamboard": (32.00, "Sheet", ["R-5", "R-7.5", "R-10"])
        }

        for style, details in styles.items():
            price, unit, r_values = details
            for r in r_values:
                # We'll use the R-Value in the 'sub_type'
                self.add_product(
                    category="Insulation",
                    sub_category="Hero",
                    name=f"{style} Insulation",
                    sub_type=r,
                    unit=unit,
                    base_price=price
                )

        # 2. Accessories
        accessories = {
            "6-mil Poly Vapor Barrier": (95.00, "Roll"),
            "Insulation Fabric Backing": (120.00, "Roll"),
            "Insulation Support Wires": (15.00, "Box")
        }

        for acc, details in accessories.items():
            price, unit = details
            # CHANGE: Use 'acc' (the name) as the sub_category so SQL can JOIN it
            self.add_product("Insulation", acc, acc, "Universal", unit, price)


def write_requirements():
    """ a function for populating the requirements.csv file with the "default" option quote multipliers"""

    reqs = [
        # Siding
        {"category": "Siding", "required_accessory": "Starter Strip", "quantity_multiplier": 2.0},
        {"category": "Siding", "required_accessory": "J-Channel", "quantity_multiplier": 2.0},
        {"category": "Siding", "required_accessory": "Finish Trim", "quantity_multiplier": 1.0},
        {"category": "Siding", "required_accessory": "Trim Nails (1lb)", "quantity_multiplier": 0.66},

        # Roofing (Multipliers based on Bundles)
        {"category": "Roofing", "required_accessory": "Ridge Cap", "quantity_multiplier": 0.25},
        {"category": "Roofing", "required_accessory": "Starter Strip", "quantity_multiplier": 0.20},
        {"category": "Roofing", "required_accessory": "Ice and Water Shield", "quantity_multiplier": 0.15},
        {"category": "Roofing", "required_accessory": "Synthetic Underlayment", "quantity_multiplier": 0.10},

        # Sheetrock
        {"category": "Sheetrock", "required_accessory": "Screws", "quantity_multiplier": 0.03},
        # 1 box per 33 sheets
        {"category": "Sheetrock", "required_accessory": "Mud", "quantity_multiplier": 0.33},
        {"category": "Sheetrock", "required_accessory": "Tape", "quantity_multiplier": 0.10},

         # Insulation
        {"category": "Insulation", "required_accessory": "6-mil Poly Vapor Barrier", "quantity_multiplier": 0.05},
        {"category": "Insulation", "required_accessory": "Insulation Fabric Backing", "quantity_multiplier": 0.05}
    ]

    with open('requirements.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["category", "required_accessory", "quantity_multiplier"])
        writer.writeheader()
        writer.writerows(reqs)

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    all_data = []

    brands = [
        {"name": "Vertex Premium", "markup": 1.40, "s_id": 100000, "r_id": 200000},
        {"name": "Summit Mid-Tier", "markup": 1.15, "s_id": 130000, "r_id": 230000},
        {"name": "EcoShield Budget", "markup": 1.00, "s_id": 160000, "r_id": 260000}
    ]

    for b in brands:
        # Siding & Roofing for all
        siding = SidingCategory(b['name'], b['markup'], b['s_id'])
        siding.generate_siding()
        all_data.extend(siding.products)

        roofing = RoofingCategory(b['name'], b['markup'], b['r_id'])
        roofing.generate_roofing()
        all_data.extend(roofing.products)

        # Budget-specific lines
        if b['name'] == "EcoShield Budget":
            # Sheetrock (300k range)
            drywall = SheetrockCategory(b['name'], b['markup'], 300000)
            drywall.generate_sheetrock()
            all_data.extend(drywall.products)

            # Insulation (400k range)
            insul = InsulationCategory(b['name'], b['markup'], 400000)
            insul.generate_insulation()
            all_data.extend(insul.products)

    # write to the CSV file
    if all_data:
        with open('products.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
            writer.writeheader()
            writer.writerows(all_data)
        print(f"Success! {len(all_data)} products generated using Class-Based logic.")

    # add the requirements.csv information
    write_requirements()