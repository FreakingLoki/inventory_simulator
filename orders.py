import sqlite3
import math
from datetime import datetime
import quotes
import customers

DB_FILE = 'wms_normalized.db'


def get_next_invoice_number():
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()
    cursor.execute("SELECT MAX(invoice_number) FROM orders;")
    result = cursor.fetchone()[0]
    connection.close()
    return result + 1 if result else 1001


def check_order_feasibility(quote_data):
    latest_restock_date = datetime.now()
    requires_delay = False
    hero = quote_data['hero']
    hero_needed = quote_data['quantity']

    if hero_needed > hero['inventory']:
        if not hero['incoming'] or hero_needed > (hero['inventory'] + hero['incoming']):
            return False, None, f"REJECTED: '{hero['name']}' requires {hero_needed}, but warehouse only has {hero['inventory']} on hand and {hero['incoming'] or 0} incoming."
        requires_delay = True
        hero_date = datetime.strptime(hero['restock_date'], '%Y-%m-%d') if hero['restock_date'] else datetime.now()
        latest_restock_date = max(latest_restock_date, hero_date)

    if quote_data['accessories'] != "None":
        for acc in quote_data['accessories']:
            acc_needed = math.ceil(quote_data['quantity'] * acc['quantity_multiplier'])
            if acc_needed > acc['inventory']:
                if not acc['incoming'] or acc_needed > (acc['inventory'] + acc['incoming']):
                    return False, None, f"REJECTED: '{acc['name']}' requires {acc_needed}, but warehouse only has {acc['inventory']} on hand and {acc['incoming'] or 0} incoming."
                requires_delay = True
                acc_date = datetime.strptime(acc['restock_date'], '%Y-%m-%d') if acc['restock_date'] else datetime.now()
                latest_restock_date = max(latest_restock_date, acc_date)

    if requires_delay:
        return True, latest_restock_date.strftime('%Y-%m-%d'), "DELAY REQUIRED"
    return True, datetime.now().strftime('%Y-%m-%d'), "READY NOW"


def submit_order(quote_data, customer, grand_total, order_date):
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    invoice_nbr = get_next_invoice_number()
    acct_num = customer['account_number'] if customer else 0

    try:
        cursor.execute("INSERT INTO orders (invoice_number, account_number, order_date) VALUES (?, ?, ?)",
                       (invoice_nbr, acct_num, order_date))

        def deduct_inventory(item_id, qty_needed):
            cursor.execute("SELECT quantity_on_hand, quantity_incoming FROM inventory_status WHERE product_id = ?",
                           (item_id,))
            on_hand, incoming = cursor.fetchone()
            if qty_needed <= on_hand:
                cursor.execute(
                    "UPDATE inventory_status SET quantity_on_hand = quantity_on_hand - ? WHERE product_id = ?",
                    (qty_needed, item_id))
            else:
                remainder = qty_needed - on_hand
                cursor.execute("""
                    UPDATE inventory_status 
                    SET quantity_on_hand = 0, quantity_incoming = quantity_incoming - ? 
                    WHERE product_id = ?
                """, (remainder, item_id))

        hero_id = int(quote_data['hero']['id'])
        cursor.execute(
            "INSERT INTO order_items (invoice_number, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
            (invoice_nbr, hero_id, quote_data['quantity'], quote_data['hero']['price']))
        deduct_inventory(hero_id, quote_data['quantity'])

        if quote_data['accessories'] != "None":
            for acc in quote_data['accessories']:
                acc_id = int(acc['id'])
                qty_needed = math.ceil(quote_data['quantity'] * acc['quantity_multiplier'])
                cursor.execute(
                    "INSERT INTO order_items (invoice_number, product_id, quantity, price_at_sale) VALUES (?, ?, ?, ?)",
                    (invoice_nbr, acc_id, qty_needed, acc['price']))
                deduct_inventory(acc_id, qty_needed)

        if customer:
            cursor.execute("UPDATE customers SET unpaid_balance = unpaid_balance + ? WHERE account_number = ?",
                           (grand_total, acct_num))

        connection.commit()
        print(f"\n[SUCCESS] Invoice #{invoice_nbr} successfully logged for {order_date}.")
        print(f"Inventory updated and ${grand_total:,.2f} charged to record.")
    except sqlite3.Error as e:
        connection.rollback()
        print(f"Transaction failed! Changes rolled back. Error: {e}")
    finally:
        connection.close()


def handle_quote_actions(quote_data, customer=None):
    while True:
        hero_total = quote_data['hero']['price'] * quote_data['quantity']
        accessory_total = 0
        if quote_data['accessories'] != "None":
            accessory_total = sum((acc['price'] * math.ceil(quote_data['quantity'] * acc['quantity_multiplier']))
                                  for acc in quote_data['accessories'])
        grand_total = hero_total + accessory_total

        quotes.display_quote(quote_data['hero'], quote_data['quantity'], quote_data['accessories'],
                             quote_data['warnings'])

        print(f" --- Customer: {customer['customer_name'] if customer else 'Guest'} --- ")
        print("01: Submit and Finalize Order")
        print("02: Modify Quantities (Add/Remove items)")
        print("03: Discard Quote")

        choice = input("\nEnter Selection: ")
        match choice:
            case "01":
                if customer:
                    allowed, message = customers.check_credit_status(customer, grand_total)
                    if not allowed:
                        print(f"\n{message}")
                        continue

                is_possible, order_date, status_msg = check_order_feasibility(quote_data)
                if not is_possible:
                    print(f"\n[!] ORDER BLOCKED: {status_msg}\nPlease modify quantities or discard the quote.")
                    continue

                if order_date != datetime.now().strftime('%Y-%m-%d'):
                    print(
                        f"\n[!] INVENTORY SHORTAGE: This order exceeds current on-hand stock.\nThe earliest we can fulfill this entire order is: {order_date}")
                    if input("Would you like to reserve this stock and push the order date? (y/n): ").lower() != 'y':
                        print("Order cancelled by user.")
                        continue

                submit_order(quote_data, customer, grand_total, order_date)
                break
            case "02":
                print("Quote modification coming soon...")
            case "03":
                if input("Are you sure you'd like to discard this quote? (y/n): ").lower() == "y":
                    print("Quote discarded")
                    break


def start_quote_flow():
    product_id = input("Enter Product ID: ").strip()
    if not product_id:
        print("Invalid Product ID.")
        return
    print("\n ----- Customer Selection -----")
    account_number = input("Enter Customer Account Number or 0 for Guest: ").strip()
    current_customer = customers.find_customer(account_number) if account_number and account_number != "0" else None

    quote_data = quotes.generate_quote(product_id)
    if quote_data:
        handle_quote_actions(quote_data, current_customer)


def get_invoice_data(invoice_number):
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        sql_query = """
            SELECT o.invoice_number, o.order_date as date, o.account_number, 
                   b.brand_name as brand, p.product_name as name, 
                   oi.quantity, p.unit, (oi.quantity * oi.price_at_sale) as line_total,
                   c.customer_name
            FROM orders o
            JOIN order_items oi ON o.invoice_number = oi.invoice_number
            JOIN products p ON oi.product_id = p.product_id
            JOIN brands b ON p.brand_id = b.brand_id
            LEFT JOIN customers c ON o.account_number = c.account_number
            WHERE o.invoice_number = ?
        """
        cursor.execute(sql_query, (invoice_number,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows] if rows else None
    except sqlite3.Error as e:
        print(f"Error fetching invoice data:\n{e}")
        return None
    finally:
        if connection:
            connection.close()


def display_invoice(invoice_data):
    if not invoice_data:
        print("\n[!] No invoice data to display.")
        return
    header = invoice_data[0]
    customer = header['customer_name'] if header['customer_name'] else "GUEST"

    print("\n" + "=" * 60)
    print(f"{'INVOICE: #' + str(header['invoice_number']):^60}")
    print(f"{'Date: ' + header['date']:^60}")
    print(f"{'Customer: ' + customer:^60}")
    print("=" * 60)

    grand_total = 0
    for row in invoice_data:
        print(
            f"- {row['brand']} {row['name']:.<35} {row['quantity']:>5} {row['unit']:<6} | ${row['line_total']:>10,.2f}")
        grand_total += row['line_total']

    print("-" * 60)
    print(f"{'TOTAL DUE:':>48} ${grand_total:>10,.2f}")
    print("=" * 60 + "\n")


def get_recent_orders_summary():
    connection = None
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        sql_query = """
            SELECT o.invoice_number, o.order_date as date, 
                   COALESCE(c.customer_name, 'GUEST') as customer,
                   SUM(oi.quantity * oi.price_at_sale) as order_total
            FROM orders o
            JOIN order_items oi ON o.invoice_number = oi.invoice_number
            LEFT JOIN customers c ON o.account_number = c.account_number
            GROUP BY o.invoice_number
            ORDER BY o.invoice_number DESC
        """
        cursor.execute(sql_query)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        return None
    finally:
        if connection:
            connection.close()


def display_order_ledger(summary_data):
    print("\n" + "=" * 70)
    print(f"{'SALES LEDGER / ORDER HISTORY':^70}")
    print("=" * 70)
    print(f"{'INV #':<10} | {'Date':<12} | {'Customer':<25} | {'Total'}")
    print("-" * 70)
    for row in summary_data:
        print(f"{row['invoice_number']:<10} | {row['date']:<12} | "
              f"{row['customer']:<25} | ${row['order_total']:>10,.2f}")
    print("=" * 70)


def order_history_manager():
    while True:
        summary = get_recent_orders_summary()
        if not summary:
            print("\n[!] No order history found.")
            break
        display_order_ledger(summary)
        choice = input("\nEnter Invoice # to view details (or 'q' to return to Main Menu): ").strip()

        if choice.lower() == 'q' or not choice:
            break

        invoice_data = get_invoice_data(choice)
        if invoice_data:
            display_invoice(invoice_data)
            input("Press Enter to return to the Ledger...")
        else:
            print(f"Invoice #{choice} not found.")