# Building Products Quote Generator
A tool for generating quotes for construction jobs with
fictitious pricing and recommended add-ons based on a fictitious warehouse
environment with incoming and outgoing orders.

## Project Motivation
### The Inspiration 
A simple calculator often isn't enough for generating a quote 
for certain products supplied by the building products company 
I currently work for. A siding job (the original inspiration) may
require a multitude of accessories depending on the structure being
sided. Door, window, and gable vent openings have an effect on the
overall amount of required material and accessories (such as J-Channel,
Finish Trim, etc.) that goes beyond a simple ratio.

### The Goal
The ultimate goal for this project is to provide a tool for calculating the
required materials for any siding, roofing, insulation, or sheetrock project. 
The final quote generation step will recommend add-ons for each job that
complement the main "hero" product with the aim to generate additional sales
for the company.

## Key Features
### Accessory Mapping
The accessories that match up with a specific hero product category are
automatically added to a quote if that quote is for a hero product. For
example, an order of 15 square (a square being 100 square feet) of a
specific type of siding requires a specific amount of J-channel to finish
the top edge of the wall, with more to go around openings in the wall such as
doors and windows. Other accessories are added to the quote depending on other
information gathered form the customer by the user.

### Color Matching
Depending on the type of hero product category, the accessories can vary in color,
either matching, or contrasting, or not being applicable (in insulation and
sheetrock). The quote generator has appropriate options for the user depending
on which product category they are generating a quote for.

### Smart Inventory Alerts
The final quote display has a feature to warn users of inventory shortages and
when the on-hand inventory will be replenished should a quote be requested
for more product than is currently on hand.

### Fully Normalized Relational Database Backend
The application runs on a robust, Third Normal Form (3NF) normalized SQLite database. 
This architecture cleanly separates static product catalog descriptions from active 
warehouse logistics (inventory on hand, incoming shipments) and historical transactions. 
By utilizing standard SQL `JOIN` queries, the application retrieves dynamic layouts 
rapidly without risking data redundancy or update anomalies.

### Precision Quoting
Users can choose between four methods for calculating quotes:
- Standard: Uses industry-average ratios for quick estimates
- Site-Specific: Prompts the user for actual job-site measurements for highly accurate material lists
- Custom: Allows for manual entry of specific product counts
- Skip: Quickly generates a quote for only the main product without recommending add-ons.

### Inventory Seeding and Randomization
Early in development, the application utilized a tool for seeding flat `products.csv` files with generated building products to enable easier addition of new lines. Along with `randomize_inventory.py`, these scripts simulated realistic warehouse stock counts and incoming delivery dates, which were eventually migrated into the permanent SQLite relational database.

### Order History
When a user generates a quote for a customer, they have the option to modify, discard, or submit the quote as a finalized order. Submitted orders securely map relational ties between the customer ledger and the purchased items. Because historical invoices lock in the "price at point-of-sale," changing catalog prices in the future will not retroactively alter past financial records. Furthermore, submitting an order natively deducts stock from the warehouse tracking tables.

## Technical Architecture
### The Stack
Python 3.x and standard built-in `sqlite3` for pure SQL transaction handling (with legacy support for `pandas` initializing basic operational rule sets).

### Data Model
The project relies on a 3NF relational layout with 8 core tables:
* **Lookup Tables (`brands`, `categories`, `sub_categories`)**: Independent structures defining hierarchies so categories can exist without products.
* **`products`**: The core catalog containing static descriptions (`id`, `brand_id`, `sub_category_id`, `name`, `sub_type`, `unit`, `unit_price`).
* **`inventory_status`**: The logistical layer tracking fluid data independently (`product_id`, `quantity_on_hand`, `quantity_incoming`, `expected_restock_date`).
* **`customers`**: Client profiles and active credit/balance ledgers.
* **`orders` & `order_items`**: Transactional headers and specific line items tracking historical point-of-sale prices.

The `requirements.csv` and `category_rules.csv` continue to serve as the local "rulebooks" determining how many accessories map to hero products and how color matching is handled per material type.

### Environment Safety
The application features a function called `check_setup()` which verifies the local instance of the virtual environment and checks the integrity of the required SQLite database tables. If any structural problems are detected, it returns False which causes the application to close after warning the user.

## Challenges and Solutions
### Database Normalization Migration
Initially, the project relied heavily on the `pandas` library to load, read, and write entirely from flat `.csv` files. This led to immediate structural issues: if a product price changed, previous order histories would break, and tracking inventory dynamically proved dangerous due to transitive dependencies. 

I successfully designed a fully 3NF normalized schema and wrote a custom ETL (Extract, Transform, Load) script (`migrate.py`) to safely parse the legacy flat data, establish unique primary/foreign key relationships, and construct a robust SQLite database. The application was then refactored to execute native SQL queries rather than in-memory dataframe manipulations, drastically improving transaction safety and performance.

### Scalability
Adding a new product line has been planned for. Thanks to the normalized database design, a new brand or category can be initialized independently in the system, and new products instantly hook into existing validation rules without breaking historical inventory structures.

### The 'Hyphen' Bug
Early in developing the application, when I named the columns, I habitually hyphenated sub-categories instead of using an underscore. This led to an issue where the SQL query tried to subtract the value of a column named `sub` from the value of a column named `category`. I quickly pivoted to standard snake_case styling (`sub_category`) to ensure universal code friendliness.

### The 'color' Category Expansion
While constructing the Siding category, I included a `color` column, as vinyl siding costs often scale with darker pigments. However, as I expanded into Sheetrock and Insulation, "color" became entirely irrelevant compared to "R-Value" or "Thickness". I realized my schema was too rigid. I refactored the database architecture, pivoting the `color` column into a broader `sub_type` attribute. This allowed all product categories to logically utilize the modifier column without forcing attributes that didn't make sense.

## Planned Future Features
### Push Order Dates
If an order is submitted which will drive inventory negative, that order should be pushed out so that its date is *after* enough incoming inventory has been received to fill the entirety of the order. In other words, I need to add a way to protect the system from allowing sales of more product than what is on hand. Stock warnings should be updated to warn the user that their order is being delayed until the warehouse has enough inventory to fill the order.

### Business Analysis Tools
Once the order history component has been built, adding this feature would allow a user to run data analysis tools to draw conclusions about the simulated business. Sales trends, popular items, and more could be useful tools to have.

### Unit Tests
Testing each new update to the function is quickly becoming a large endeavor in itself. Building tests to ensure each piece works as it should, will enable more focus on improving and updating and less focus on re-running the same commands.

### Inventory Control Tools
The program is missing tools for users to manage the inventory of the warehouse. I need to add the ability to modify inventory levels and generate "cycle count" lists for users of the application. Depending on how ambitious I'm feeling I may also add Purchase Order tracking (and generation), which would require each incoming load of each product to have a unique lot number or manufacture date. This would require adding new tables to the SQL database to accommodate the new logistics.

## How to Run
To run this project locally, follow these steps:

1. Clone the Repository

`git clone https://github.com/FreakingLoki/inventory_simulator.git`<br>
`cd inventory_simulator`

2. Set Up a Virtual Environment

`python -m venv venv`<br>
on Windows:<br>
`venv\Scripts\activate`<br>
On macOS/Linux:<br>
`source venv/bin/activate`

3. Install Dependencies

`pip install pandas`

4. Run the Application

`python main.py`