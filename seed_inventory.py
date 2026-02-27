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


# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    all_data = []

    # define brands
    brands = [
        {"name": "Vertex Premium", "markup": 1.25, "start_id": 100000},
        {"name": "EcoShield", "markup": 1.0, "start_id": 150000}
    ]

    # use the generators to add the product from each brand
    for b in brands:
        siding = SidingCategory(b['name'], b['markup'], b['start_id'])
        siding.generate_siding()
        all_data.extend(siding.products)

    # write to the CSV file
    if all_data:
        with open('products.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
            writer.writeheader()
            writer.writerows(all_data)
        print(f"Success! {len(all_data)} products generated using Class-Based logic.")