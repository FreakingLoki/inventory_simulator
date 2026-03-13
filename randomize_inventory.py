# ----- IMPORTS SECTION -----
import random
import pandas as pd
from datetime import datetime, timedelta

# ----- GLOBAL VARIABLES -----

# ----- FUNCTIONS DEFINITIONS -----

def randomize_inventory():
    """This function will randomize the inventory levels and incoming stock levels and dates of all products
     found within the products.csv file"""

    # start by loading the data from the .csv files as DataFrame objects
    products_df = pd.read_csv('products.csv')
    reqs_df = pd.read_csv('requirements.csv')

    # separate the hero products from the accessories
    heroes = products_df[products_df['sub_category'] == 'Hero']

    for index, row in products_df.iterrows():
        # if hero, use the truckload ranges
        # if accessory, find the hero and use the ratio math from requirements.csv

        # randomize restock dates
        # generate a date between today and 6 months out (180 days)
        days_out = random.randint(1, 180)
        restock_date = (datetime.now() + timedelta(days=days_out)).strftime('%m/%d/%Y')

        # update the DataFrame
        # something like:
        # products_df.at[index, 'inventory'] = new_val

    # overwrite the .csv file with the new data
    # something like
    # products_df.to_csv(...)

# ----- EXECUTION BLOCK -----