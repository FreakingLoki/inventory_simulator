import sqlite3
from datetime import datetime

DB_FILE = 'wms_normalized.db'


def find_customer(account_number):
    """Fetches a customer's information from the local database"""
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
    """Checks if a customer has enough credit to place an order"""
    projected_balance = customer['unpaid_balance'] + order_total
    if projected_balance > customer['credit_limit']:
        overage = projected_balance - customer['credit_limit']
        return False, f"Credit Denied: Order Total ${order_total:,.2f} is ${overage:,.2f} over the limit."
    return True, "Credit approved."


def add_customer():
    """Adds a new customer to the database as long as that customer doesn't already exist"""
    print(f"\n--- Adding a new customer ---")
    new_customer_name = input("Enter the customer's name: ").strip()

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
                f"[SUCCESS] {new_customer_name} added as Account #{new_account_number} with a credit limit of ${new_customer_credit_limit:,}")
        else:
            print("[!] A customer with that name already exists. Customers need to have unique names.")

    except sqlite3.Error as e:
        print(f"Database Error:\n{e}")
    finally:
        if connection:
            connection.close()


def record_payment():
    """Records a payment the customer has made and updates their available/unpaid credit balances"""
    print(f"\n--- Record Customer Payment ---")
    account_number = input("Enter Customer Account Number: ").strip()
    customer = find_customer(account_number)

    if not customer:
        print("[!] Customer not found.")
        return

    print(f"Customer: {customer['customer_name']}")
    print(f"Current Unpaid Balance: ${customer['unpaid_balance']:,.2f}")

    try:
        payment_amount = float(input("Enter payment amount: $"))
        if payment_amount <= 0:
            print("Payment must be greater than zero.")
            return
    except ValueError:
        print("Invalid entry. Please enter a valid dollar amount.")
        return

    payment_date = datetime.now().strftime('%Y-%m-%d')
    connection = None

    try:
        connection = sqlite3.connect(DB_FILE)
        cursor = connection.cursor()

        # 1. Log the permanent transaction record
        cursor.execute("""
            INSERT INTO payments (account_number, payment_amount, payment_date) 
            VALUES (?, ?, ?)
        """, (account_number, payment_amount, payment_date))

        # 2. Update the active customer ledger
        cursor.execute("""
            UPDATE customers 
            SET unpaid_balance = unpaid_balance - ?, 
                last_payment_date = ?
            WHERE account_number = ?
        """, (payment_amount, payment_date, account_number))

        connection.commit()
        new_balance = customer['unpaid_balance'] - payment_amount
        print(f"[SUCCESS] ${payment_amount:,.2f} applied to account. New balance: ${new_balance:,.2f}")

    except sqlite3.Error as e:
        if connection:
            connection.rollback()
        print(f"Database Error: Transaction rolled back.\n{e}")
    finally:
        if connection:
            connection.close()


def customer_management_menu():
    """Displays the customer management menu"""
    while True:
        print(f"\n--- Customer Management ---")
        print("01: Look Up Customer Account")
        print("02: Add New Customer")
        print("03: Record a Payment")
        print("04: Return to Main Menu")

        choice = input("\nEnter Selection: ")

        match choice:
            case '01':
                acct = input("\nEnter Account Number: ").strip()
                cust = find_customer(acct)
                if cust:
                    print(
                        f"\nCustomer: {cust['customer_name']} | Limit: ${cust['credit_limit']:,.2f} | Balance: ${cust['unpaid_balance']:,.2f}")
                else:
                    print("[!] Customer not found.")
            case '02':
                add_customer()
            case '03':
                record_payment()
            case '04':
                break
            case _:
                print("Invalid selection.")