import sqlite3

DB_FILE = 'wms_normalized.db'


def find_customer(account_number):
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM customers WHERE account_number = ?", (account_number,))
        customer = cursor.fetchone()
        return dict(customer) if customer else None
    except Exception as e:
        print(f"Error:\n{e}")
        return None
    finally:
        if connection:
            connection.close()


def check_credit_status(customer, order_total):
    projected_balance = customer['unpaid_balance'] + order_total
    if projected_balance > customer['credit_limit']:
        overage = projected_balance - customer['credit_limit']
        return False, f"Credit Denied: Order Total ${order_total:,.2f} is ${overage:,.2f} over the limit."
    return True, "Credit approved."


def add_customer():
    print(f"\nAdding a new customer...")
    new_customer_name = input("\nEnter the customer's name: ").strip()

    try:
        new_customer_credit_limit = int(input("Enter the customer's credit limit: "))
    except ValueError:
        print("Invalid entry. Credit limit must be a whole number.")
        return

    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM customers WHERE customer_name = ?", (new_customer_name,))
        existing_customer = cursor.fetchone()

        if existing_customer is None:
            cursor.execute("SELECT MAX(account_number) FROM customers")
            max_account = cursor.fetchone()[0]
            new_account_number = (max_account + 1) if max_account else 1001

            cursor.execute("""
                INSERT INTO customers (account_number, customer_name, credit_limit, unpaid_balance) 
                VALUES (?, ?, ?, ?)
            """, (new_account_number, new_customer_name, new_customer_credit_limit, 0.0))

            connection.commit()
            print(
                f"Success! {new_customer_name} added as Account #{new_account_number} with a credit limit of ${new_customer_credit_limit:,}")
        else:
            print("A customer with that name already exists. Customers need to have unique names.")

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
    finally:
        if connection:
            connection.close()