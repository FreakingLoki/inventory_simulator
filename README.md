# Building Products Quote Generator
A tool for generating quotes for construction jobs 
(siding only for now with more to come) with
fictitious pricing and recommended add-ons.

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

### Relational Database Backend
The main "corporate product database" I built for this project is a series of CSV files
which act as a stand in for a company's internal or remote database that stores
information on products including id numbers, amount on hand, incoming orders and dates,
and more. There is also CSV files which act as a rulebook for how many accessories to
recommend to add to an order based on the size of the order. Additionally, there is a CSV
file which lays out the color-matching rules for each product category.

I use the Pandas module to convert these CSVs to a local database (acting as a local copy
of a remote corporate database) into SQL for ease of use and better computational speed.
The local copy of the database is updated every time the user launches the application.

## Technical Architecture
### The Stack
Python 3.14, SQLite, and Pandas for database initialization

### Data Model
The `products.csv` contains the main data for the products the building products company 
has to offer their customers. The `products.csv` table has these columns:
`id`, `category`, `sub_category`, `name`, `color`, `unit`, `price`, `inventory`, 
`incoming`, `restock_date`.

The `requirements.csv` contains a "map" of the required accessories for each
product category and how many of each accessory per unit of hero product
that should be recommended. The `requirements.csv` table has these columns: `category`,
`required_accessory`, `quantity_multiplier`.

The `category_rules.csv` is the rulebook that tells the application how each product
category handles color matching. The `category_rules.csv` table has these columns:
`category`, `color_matching_type`.

### Environment Safety
The application features a functino called `check_setup()` which verifies the local
instance of the virtual environment and the local database. It runs immediately after the 
database is initialized. If any problems are detected it returns False which causes
the application to close after warning the user.

## Challenges and Solutions
### Scalability
Adding a new product line has been planned for. It only requires updating the CSV
files with the product information, the accessory relationships, and the category
color-matching rules.

In the future, I plan to construct a script which auto-generates several 
hundred products and populates the `products.csv` file, then randomizes inventory
levels and restock dates.

Note: The script which generates products has been added, but the randomized
inventory levels has not been added yet.

### The 'Hyphen' Bug
Early in developing the application, when I named the columns in the `products.csv`
file, I habitually hyphenated sub-categories instead of using an underscore (as it is now).
This led to an issue where the SQL JOIN query trying to subtract the value of a column named
`sub` from the value of a column named `category`. I could have left the hyphen and enclosed
the name of the column in square brackets or double quotes, but I decided to rename the column
to `sub_category` to be more universally code friendly.

### The 'color' Category
While constructing the products.csv, I started with the Siding category. As many of us know, 
vinyl siding comes in many different colors with accessories that match (or contrast with) the
main panel color. In general, in the industry, darker colors often cost more than lighter colors.
Because of this trend, I included a `color` colum in the comma separated value file `products.csv`.
For a while, this worked fine, and it continued to work until I approached the sheetrock and
insulation categories. Shingle roofing also comes in various colors, but in sheetrock and insulation,
the color of the product doesn't matter as much as the R-value or the thickness of the product. At first,
I decided to use the `color` column the way it was already being used; as a filter. Then, I realized
it was named poorly, AND I realized that the design of my database was too rigid. I needed to normalize
the database to allow for all the product categories to make logical use of this filter. I had to
adjust the architecture of the project to adapt to the changing needs. At this point I was already using
the `seed_inventory.py` script to generate the `products.csv` file, so the main changes were to that script
and the references to the `color` category in the `main.py` script. I settled on a more suitable name for
this column, `sub_type`, which works better because the color, length, or thickness of a material can
easily be thought of as the sub-type of that product.

### The Accurate Job Lot Quotes Refactor
This took a lot of planning, refactoring and bugfixing. At first, the program only used a simple list of
ratios (using industry averages) to recommend add-ons based on which hero product was being quoted and how
much was being ordered. I had to rewrite the `generate_quote()` function to use a branching flow which
eventually filters down to passing data to a few final checks before passing everything on to
the `display_quote()` function which handles the layout of the quote in the terminal.

## Planned Future Features
### Inventory Script
The main idea here is to randomize the inventory levels (within some logical bounds), 
restock amount, and restock dates of every item in the products.csv file to simulate
a working business. This script could also be used to add new lines of products, new
accessories and act as a general inventory maintenance tool.

### Order History
After a quote is generated, the user should be asked if the customer would like to order
the quoted items. Then, the details should be added (such as a customer account number, 
order date, and shipment address), and the entire set of data (products ordered, amount 
paid, plus the customer information) should be saved to a database. Additionally, a script
will be built to construct some generated historical data.

### Business Analysis Tools
Once the order history component has been built, adding this feature would allow a user to
run data analysis tools to draw conclusions about the simulated business. Sales trends,
popular items, and more could be useful tools to have.

### Unit Tests
Testing each new update to the function is quickly becoming a large endeavor in itself. Building 
tests to ensure each piece works as it should, will enable more focus on improving and updating
and less focus on re-running the same commands.

## How to Run
To run this project locally, follow these steps:

1. Clone the Repository

`git clone [https://github.com/FreakingLoki/inventory_simulator.git](http://github.com/FreakingLoki/inventory_simulator.git)`<br>
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