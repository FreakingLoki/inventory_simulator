import pytest
from datetime import datetime
import orders


def test_order_feasibility_ready_now(mock_db):
    """Test that an order requiring less than the on-hand quantity is approved immediately."""
    quote_data = {
        'hero': {
            'id': 100001,
            'name': 'Double-4 Siding',
            'inventory': 87,
            'incoming': 62,
            'restock_date': '2030-04-28'
        },
        'quantity': 50,
        'accessories': "None"
    }

    is_possible, order_date, status = orders.check_order_feasibility(quote_data)

    assert is_possible is True
    assert status == "READY NOW"
    assert order_date == datetime.now().strftime('%Y-%m-%d')


def test_order_feasibility_push_date(mock_db):
    """Test that an order exceeding on-hand stock but covered by incoming stock is delayed."""
    quote_data = {
        'hero': {
            'id': 100001,
            'name': 'Double-4 Siding',
            'inventory': 87,
            'incoming': 62,
            'restock_date': '2030-04-28'
        },
        'quantity': 100,
        'accessories': "None"
    }

    is_possible, order_date, status = orders.check_order_feasibility(quote_data)

    assert is_possible is True
    assert status == "DELAY REQUIRED"
    assert order_date == '2030-04-28'


def test_order_feasibility_rejected(mock_db):
    """Test that an order exceeding all available and incoming stock is rejected."""
    quote_data = {
        'hero': {
            'id': 100001,
            'name': 'Double-4 Siding',
            'inventory': 87,
            'incoming': 62,
            'restock_date': '2030-04-28'
        },
        'quantity': 200,
        'accessories': "None"
    }

    is_possible, order_date, status = orders.check_order_feasibility(quote_data)

    assert is_possible is False
    assert "REJECTED" in status