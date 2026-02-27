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

    def add_product(self, category, sub_category, name, color, unit, base_price, inventory=50):
        """Helper to format and store a product entry."""
        price = round(base_price * self.markup, 2)
        self.products.append({
            "id": self.get_next_id(),
            "brand": self.brand_name,
            "category": category,
            "sub_category": sub_category,
            "name": name,
            "color": color,
            "unit": unit,
            "price": price,
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
        acc_types = {"J-Channel": 12.50, "Finish Trim": 15.00}
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
            "Ice & Water Shield": 85.00,  # Roll
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
        # Structure: {Sub-category: (Base Price, Thickness/Description, Color/Type)}
        boards = {
            "Thin Profile": (14.50, "1/4-inch x 4x8", "Standard"),
            "Standard Profile": (16.00, "1/2-inch x 4x8", "Standard"),
            "Moisture Resistant": (21.00, "1/2-inch x 4x8", "Green"),
            "Fire Resistant": (24.00, "5/8-inch x 4x8", "Type X")
        }

        for sub, details in boards.items():
            price, size, color = details
            self.add_product(
                category="Sheetrock",
                sub_category="Hero",
                name=f"{size} {sub}",
                color=color,
                unit="Sheet",
                base_price=price
            )

        # 2. Generate Accessories
        # Screws
        screw_types = ["1-1/4 inch Drywall Screws", "1-5/8 inch Drywall Screws"]
        for screw in screw_types:
            self.add_product("Sheetrock", "Screws", screw, "Zinc", "Box", 12.00)

        # Joint Compound (Mud)
        mud_types = {
            "All-Purpose Joint Compound": 18.00,
            "Heavy Duty Taping Compound": 22.00,
            "Moisture Resistant Mud": 28.00
        }
        for mud, price in mud_types.items():
            self.add_product("Sheetrock", "Mud", mud, "White", "Bucket", price)

        # Tape
        self.add_product("Sheetrock", "Tape", "Fiberglass Mesh Tape", "White", "Roll", 7.50)

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    all_data = []

    # 1. Define the 3-Tier Brand Strategy
    brands = [
        {"name": "Vertex Premium", "markup": 1.40, "siding_id": 100000, "roofing_id": 200000},
        {"name": "Summit Mid-Tier", "markup": 1.15, "siding_id": 130000, "roofing_id": 230000},
        {"name": "EcoShield Budget", "markup": 1.00, "siding_id": 160000, "roofing_id": 260000}
    ]

    for b in brands:
        # Siding Generation
        siding = SidingCategory(b['name'], b['markup'], b['siding_id'])
        siding.generate_siding()
        all_data.extend(siding.products)

        # Roofing Generation
        roofing = RoofingCategory(b['name'], b['markup'], b['roofing_id'])
        roofing.generate_roofing()
        all_data.extend(roofing.products)

        # Only EcoShield gets the Sheetrock line
        if b['name'] == "EcoShield Budget":
            sheetrock = SheetrockCategory(b['name'], b['markup'], 300000)
            sheetrock.generate_sheetrock()
            all_data.extend(sheetrock.products)

    # write to the CSV file
    if all_data:
        with open('products.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
            writer.writeheader()
            writer.writerows(all_data)
        print(f"Success! {len(all_data)} products generated using Class-Based logic.")