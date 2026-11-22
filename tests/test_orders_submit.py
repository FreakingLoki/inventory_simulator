import sqlite3
from datetime import datetime
import orders
import customers


def test_submit_order_hero_only(mock_db):
    """Test submitting an order with only a hero product locks in the landed cost."""
    # 1. Setup the quote data
    quote_data = {
        'hero': {
            'id': 100001,
            'price': 252.0,
            'base_cost': 150.0,
            'avg_freight_cost': 15.0
        },
        'quantity': 10,
        'accessories': "None"
    }

    # 2. Setup a dummy customer
    customer = {'account_number': 1001, 'unpaid_balance': 0.0}
    grand_total = 2520.0  # 10 * 252.0
    order_date = datetime.now().strftime('%Y-%m-%d')

    # 3. Execute the function
    orders.submit_order(quote_data, customer, grand_total, order_date)

    # 4. Verify the cost was locked into the database
    cursor = mock_db.cursor()
    cursor.execute("SELECT cost_at_sale FROM order_items WHERE product_id = 100001")
    cost_at_sale = cursor.fetchone()[0]

    # Base cost (150) + Freight (15) = 165
    assert cost_at_sale == 165.0


def test_submit_order_with_accessories(mock_db):
    """Test submitting an order with accessories locks in landed costs for all items."""
    # 1. Setup the quote data
    quote_data = {
        'hero': {
            'id': 100001,
            'price': 252.0,
            'base_cost': 150.0,
            'avg_freight_cost': 15.0
        },
        'quantity': 10,
        'accessories': [
            {
                'id': 100002,  # Let's pretend 100002 is a box of nails
                'price': 50.0,
                'base_cost': 30.0,
                'avg_freight_cost': 5.0,
                'quantity_multiplier': 0.1  # Need 1 box for every 10 squares of siding
            }
        ]
    }

    # We need to quickly insert our pretend nail product into the mock database
    cursor = mock_db.cursor()
    cursor.execute("""
        INSERT INTO products (product_id, brand_id, sub_category_id, product_name, sub_type, unit, unit_price, base_cost, avg_freight_cost) 
        VALUES (100002, 1, 2, 'Roofing Nails', 'Universal', 'Box', 50.0, 30.0, 5.0);
    """)
    cursor.execute("""
        INSERT INTO inventory_status (product_id, quantity_on_hand, quantity_incoming, expected_restock_date)
        VALUES (100002, 100, 0, NULL);
    """)
    mock_db.commit()

    # 2. Setup dummy customer
    customer = {'account_number': 1001, 'unpaid_balance': 0.0}
    grand_total = 2570.0  # 2520 + 50
    order_date = datetime.now().strftime('%Y-%m-%d')

    # 3. Execute
    orders.submit_order(quote_data, customer, grand_total, order_date)

    # 4. Verify costs for BOTH items
    cursor.execute("SELECT product_id, cost_at_sale FROM order_items")
    results = cursor.fetchall()

    # Convert results to a dictionary for easy checking
    costs = {row[0]: row[1] for row in results}

    assert costs[100001] == 165.0  # Hero: 150 + 15
    assert costs[100002] == 35.0  # Accessory: 30 + 5