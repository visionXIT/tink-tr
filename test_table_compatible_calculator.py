#!/usr/bin/env python3
"""
Test script to validate the TableExactCalculator against the table data
"""

import datetime
from typing import List
from dataclasses import dataclass

# Mock operation class to simulate Tinkoff API operations


@dataclass
class MockOperation:
    date: datetime.datetime
    payment: float
    type: int
    description: str = ""
    figi: str = ""
    name: str = ""


def create_mock_operations_for_april_week1() -> List[MockOperation]:
    """Create mock operations that exactly match April week 1 data from table"""
    operations = []

    # Based on table analysis, the "earnings" column represents NET profit (after commissions)
    # So we need to create operations that result in the correct net profit

    # Monday 31.03.2025 - net earnings: -1517.15, commission: 345.83
    # This means gross earnings should be: -1517.15 + 345.83 = -1171.32
    operations.extend([
        # Day clearing (10:00-14:00)
        MockOperation(
            date=datetime.datetime(2025, 3, 31, 12, 0),
            payment=-937.22,
            type=26,  # INCOME - day clearing
            description="Variation margin - day clearing"
        ),
        # Evening clearing (14:05-18:50)
        MockOperation(
            date=datetime.datetime(2025, 3, 31, 16, 0),
            payment=-234.10,
            type=26,  # INCOME - evening clearing
            description="Variation margin - evening clearing"
        ),
        # Commission
        MockOperation(
            date=datetime.datetime(2025, 3, 31, 17, 0),
            payment=-345.83,
            type=19,  # COMMISSION
            description="Broker fee"
        ),
    ])

    # Tuesday 01.04.2025 - net earnings: -2379.27, commission: 732.77
    # Gross earnings should be: -2379.27 + 732.77 = -1646.50
    operations.extend([
        MockOperation(
            date=datetime.datetime(2025, 4, 1, 12, 0),
            payment=-957.54,
            type=26,  # INCOME - day clearing
            description="Variation margin - day clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 1, 16, 0),
            payment=-688.96,
            type=26,  # INCOME - evening clearing
            description="Variation margin - evening clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 1, 17, 0),
            payment=-732.77,
            type=19,  # COMMISSION
            description="Broker fee"
        ),
    ])

    # Wednesday 02.04.2025 - net earnings: -2083.03, commission: 552.16
    # Gross earnings should be: -2083.03 + 552.16 = -1530.87
    operations.extend([
        MockOperation(
            date=datetime.datetime(2025, 4, 2, 12, 0),
            payment=-645.50,
            type=26,  # INCOME - day clearing
            description="Variation margin - day clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 2, 16, 0),
            payment=-885.37,
            type=26,  # INCOME - evening clearing
            description="Variation margin - evening clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 2, 17, 0),
            payment=-552.16,
            type=19,  # COMMISSION
            description="Broker fee"
        ),
    ])

    # Thursday 03.04.2025 - net earnings: -947.73, commission: 390.77
    # Gross earnings should be: -947.73 + 390.77 = -556.96
    operations.extend([
        MockOperation(
            date=datetime.datetime(2025, 4, 3, 12, 0),
            payment=659.53,
            type=26,  # INCOME - day clearing
            description="Variation margin - day clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 3, 16, 0),
            payment=-1216.49,
            type=26,  # INCOME - evening clearing
            description="Variation margin - evening clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 3, 17, 0),
            payment=-390.77,
            type=19,  # COMMISSION
            description="Broker fee"
        ),
    ])

    # Friday 04.04.2025 - net earnings: 6855.09, commission: 114.66
    # Gross earnings should be: 6855.09 + 114.66 = 6969.75
    operations.extend([
        MockOperation(
            date=datetime.datetime(2025, 4, 4, 12, 0),
            payment=6067.16,
            type=26,  # INCOME - day clearing
            description="Variation margin - day clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 4, 16, 0),
            payment=902.59,
            type=26,  # INCOME - evening clearing
            description="Variation margin - evening clearing"
        ),
        MockOperation(
            date=datetime.datetime(2025, 4, 4, 17, 0),
            payment=-114.66,
            type=19,  # COMMISSION
            description="Broker fee"
        ),
    ])

    return operations


def test_table_exact_calculator():
    """Test the TableExactCalculator with mock operations"""

    # Import the calculator
    from app.utils.profit_calculator import TableExactCalculator

    # Create calculator instance
    calculator = TableExactCalculator()

    # Create mock operations for April week 1
    operations = create_mock_operations_for_april_week1()

    # Calculate analysis
    result = calculator.get_exact_table_analysis(
        operations, starting_balance=44127.39)

    print("=== TABLE EXACT CALCULATOR TEST ===")
    print(f"Starting balance: {44127.39}")
    print(
        f"Ending balance: {result['balance_progression'].get('2025-04-04', 0)}")

    print("\nDaily breakdown:")
    for date, data in result['daily_data'].items():
        print(f"\n{date}:")
        print(f"  Day clearing: {data['day_clearing']:.2f}")
        print(f"  Evening clearing: {data['evening_clearing']:.2f}")
        print(f"  Commission: {data['commission']:.2f}")
        print(f"  Trades count: {data['trades_count']}")
        print(f"  Total profit: {data['total_profit']:.2f}")

    print(f"\nSummary:")
    print(f"  Total earnings: {result['summary']['total_earnings']:.2f}")
    print(f"  Total commission: {result['summary']['total_commission']:.2f}")
    print(f"  Net profit: {result['summary']['total_profit']:.2f}")
    print(f"  Total trades: {result['summary']['total_trades']}")
    print(
        f"  Total day clearing: {result['summary']['total_day_clearing']:.2f}")
    print(
        f"  Total evening clearing: {result['summary']['total_evening_clearing']:.2f}")

    # Expected values from table
    expected_earnings = -72.09  # From table (this is NET earnings)
    expected_commission = 2136.19  # From table
    expected_net_profit = expected_earnings  # Net profit = net earnings

    print(f"\nExpected from table:")
    print(f"  Net earnings: {expected_earnings:.2f}")
    print(f"  Total commission: {expected_commission:.2f}")
    print(f"  Net profit: {expected_net_profit:.2f}")

    print(f"\nDifference:")
    print(
        f"  Net profit diff: {result['summary']['total_profit'] - expected_net_profit:.2f}")
    print(
        f"  Commission diff: {result['summary']['total_commission'] - expected_commission:.2f}")

    # Check if the result matches the table
    if abs(result['summary']['total_profit'] - expected_net_profit) < 0.01:
        print("✅ SUCCESS: Calculator matches table data!")
    else:
        print("❌ FAILURE: Calculator doesn't match table data")


if __name__ == "__main__":
    test_table_exact_calculator()
