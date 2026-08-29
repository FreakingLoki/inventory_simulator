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