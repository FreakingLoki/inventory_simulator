# ----- IMPORTS SECTION -----
import random
import math
import pandas as pd
from datetime import datetime, timedelta

# ----- GLOBAL VARIABLES -----

# ----- FUNCTIONS DEFINITIONS -----

def randomize_inventory():
    """Randomizes inventory levels based on corporate delivery rules (hosted in the .csv files) and
     hero-accessory ratios."""

    products_df = pd.read_csv('products.csv')
    reqs_df = pd.read_csv('requirements.csv')
    rules_df = pd.read_csv('delivery_rules.csv')

    # create a lookup dictionary for rules: {Category: {unit_per_truck, min_stock}}
    rules_lookup = rules_df.set_index('category').to_dict('index')

    # loop through the products dataframe
    for index, row in products_df.iterrows():
        # grab the category and sub_category of the current product
        category = row['category']
        sub_category = row['sub_category']

        # ----- handle hero products
        if sub_category == "Hero":
            # get the restock rules from the dictionary
            rule = rules_lookup.get(category)
            if rule:
                # set inventory between min_stock and a full truck
                products_df.at[index, 'inventory'] = random.randint(rule['min_stock'], rule['unit_per_truck'])

                # 50% chance of an incoming shipment
                if random.choice([True, False]):
                    products_df.at[index, 'incoming'] = random.randint(rule['min_stock'], rule['unit_per_truck'] // 2)
                    # set the restock date to a random date between tomorrow and 3 months out
                    days_out = random.randint(1, 90)
                    products_df.at[index, 'restock_date'] = (datetime.now() + timedelta(days=days_out)).strftime(
                        '%m/%d/%Y')
                else:
                    # if the coin-flip is tails, there is no incoming order for this product
                    products_df.at[index, 'incoming'] = 0
                    products_df.at[index, 'restock_date'] = "0/00/0000"

        # ----- handle accessories
        else:
            # find the parent Hero for this specific brand and category
            brand_hero = products_df[(products_df['brand'] == row['brand']) &
                                     (products_df['sub_category'] == 'Hero')].iloc[0]

            # get the multiplier for this accessory
            match_req = reqs_df[(reqs_df['category'] == category) &
                                (reqs_df['required_accessory'] == sub_category)]

            if not match_req.empty:
                mult = match_req.iloc[0]['quantity_multiplier']

                #  randomize current Inventory (hero stock * multiplier * variance)
                ideal_stock = brand_hero['inventory'] * mult
                variance = random.uniform(0.85, 1.15)
                products_df.at[index, 'inventory'] = int(ideal_stock * variance)

                # tie incoming stock to the hero's shipment
                # if the Hero has a shipment coming, the accessories should too
                if brand_hero['incoming'] > 0:
                    # accessory incoming = hero incoming * multiplier
                    # add a little variance here to keep things interesting
                    acc_incoming = math.ceil(brand_hero['incoming'] * mult * random.uniform(0.9, 1.1))
                    products_df.at[index, 'incoming'] = acc_incoming
                    products_df.at[index, 'restock_date'] = brand_hero['restock_date']
                else:
                    products_df.at[index, 'incoming'] = 0
                    products_df.at[index, 'restock_date'] = "0/00/0000"

    # save the results back to the source CSV
    products_df.to_csv('products.csv', index=False)
    print(f"Success! {len(products_df)} inventory levels randomized.")

# ----- EXECUTION BLOCK -----

if __name__ == "__main__":
    print(f"Beginning inventory randomization...")
    randomize_inventory()