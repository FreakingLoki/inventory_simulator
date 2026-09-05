import pytest
from unittest.mock import patch
import customers

def test_add_customer(mock_db):
    """Test adding a new customer successfully."""
    # Patch intercepts the two input() calls and feeds them these strings in order
    with patch('builtins.input', side_effect=['Delta Lumber', '750']):
        customers.add_customer()

    # Verify the customer was saved to the database correctly
    customer = customers.find_customer(1001)
    assert customer is not None
    assert customer['customer_name'] == 'Delta Lumber'
    assert customer['credit_limit'] == 750.0
    assert customer['unpaid_balance'] == 0.0

def test_find_customer(mock_db):
    """Test finding an existing customer."""
    # Setup: manually insert "Fred's Lumer" to match your CSV seed data
    cursor = mock_db.cursor()
    cursor.execute("""
        INSERT INTO customers (account_number, customer_name, credit_limit, unpaid_balance, last_payment_date) 
        VALUES (1006, 'Fred''s Lumer', 6000, 1565.48, '2026-03-12')
    """)
    mock_db.commit()

    customer = customers.find_customer(1006)
    assert customer is not None
    assert customer['customer_name'] == "Fred's Lumer"
    assert customer['unpaid_balance'] == 1565.48

def test_check_credit_status():
    """Test the credit check logic directly (no database required)."""
    # Using Circuit Contractor Supply's baseline numbers
    mock_customer = {'credit_limit': 5000.0, 'unpaid_balance': 1673.06}

    # Order under limit (5000 - 1673.06 = 3326.94 available)
    approved, msg = customers.check_credit_status(mock_customer, 1000.0)
    assert approved is True
    assert msg == "Credit approved."

    # Order over limit
    denied, msg = customers.check_credit_status(mock_customer, 4000.0)
    assert denied is False
    assert "Credit Denied" in msg

def test_record_payment(mock_db):
    """Test recording a payment updates the ledger and creates a transaction record."""
    cursor = mock_db.cursor()
    # Setup: insert Juniper Lumber
    cursor.execute("""
        INSERT INTO customers (account_number, customer_name, credit_limit, unpaid_balance) 
        VALUES (1010, 'Juniper Lumber', 25000, 6190.8)
    """)
    mock_db.commit()

    # Mock inputs: Account Number (1010), then Payment Amount (190.80)
    with patch('builtins.input', side_effect=['1010', '190.80']):
        customers.record_payment()

    # Verify customer balance decreased to exactly 6000
    updated_cust = customers.find_customer(1010)
    assert updated_cust['unpaid_balance'] == 6000.0

    # Verify the payments table logged the permanent transaction
    cursor.execute("SELECT payment_amount FROM payments WHERE account_number = 1010")
    payment = cursor.fetchone()
    assert payment is not None
    assert payment[0] == 190.80