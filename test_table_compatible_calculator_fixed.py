#!/usr/bin/env python3
"""
Comprehensive test script to validate the TableExactCalculator against all table data
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


def create_mock_operations_for_all_periods() -> List[MockOperation]:
    """Create mock operations for all periods from the tables"""
    operations = []

    # April Period 1: 31.03-04.04 (net profit: -72.09, commission: 2136.19)
    # Monday 31.03.2025 - net earnings: -1517.15, commission: 345.83
    operations.extend([
        MockOperation(datetime.datetime(2025, 3, 31, 12, 0), -
                      937.22, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 3, 31, 16, 0), -
                      234.10, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 3, 31, 17, 0), -
                      345.83, 19, "Commission"),
    ])

    # Tuesday 01.04.2025 - net earnings: -2379.27, commission: 732.77
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 1, 12, 0), -
                      957.54, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 1, 16, 0), -
                      688.96, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 1, 17, 0), -
                      732.77, 19, "Commission"),
    ])

    # Wednesday 02.04.2025 - net earnings: -2083.03, commission: 552.16
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 2, 12, 0), -
                      645.50, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 2, 16, 0), -
                      885.37, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 2, 17, 0), -
                      552.16, 19, "Commission"),
    ])

    # Thursday 03.04.2025 - net earnings: -947.73, commission: 390.77
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 3, 12, 0),
                      659.53, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 3, 16, 0), -
                      1216.49, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 3, 17, 0), -
                      390.77, 19, "Commission"),
    ])

    # Friday 04.04.2025 - net earnings: 6855.09, commission: 114.66
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 4, 12, 0),
                      6067.16, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 4, 16, 0),
                      902.59, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 4, 17, 0), -
                      114.66, 19, "Commission"),
    ])

    # April Period 2: 07.04-11.04 (net profit: -12417.69, commission: 1784.81)
    # Monday 07.04.2025 - net earnings: -3035.10, commission: 423.50
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 7, 12, 0),
                      168.55, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 7, 16, 0), -
                      2780.15, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 7, 17, 0), -
                      423.50, 19, "Commission"),
    ])

    # Tuesday 08.04.2025 - net earnings: -3537.14, commission: 443.33
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 8, 12, 0), -
                      2887.33, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 8, 16, 0), -
                      206.48, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 8, 17, 0), -
                      443.33, 19, "Commission"),
    ])

    # Wednesday 09.04.2025 - net earnings: -1489.98, commission: 181.37
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 9, 12, 0),
                      1512.76, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 9, 16, 0), -
                      2821.37, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 9, 17, 0), -
                      181.37, 19, "Commission"),
    ])

    # Thursday 10.04.2025 - net earnings: 1945.47, commission: 315.97
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 10, 12, 0),
                      4915.88, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 10, 16, 0), -
                      2654.44, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 10, 17, 0), -
                      315.97, 19, "Commission"),
    ])

    # Friday 11.04.2025 - net earnings: -6300.94, commission: 420.64
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 11, 12, 0), -
                      4939.49, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 11, 16, 0), -
                      940.81, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 11, 17, 0), -
                      420.64, 19, "Commission"),
    ])

    # April Period 3: 14.04-18.04 (net profit: -6928.85, commission: 1255.89)
    # Monday 14.04.2025 - net earnings: -2885.41, commission: 261.67
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 14, 12, 0), -
                      1621.23, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 14, 16, 0), -
                      1002.51, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 14, 17, 0), -
                      261.67, 19, "Commission"),
    ])

    # Tuesday 15.04.2025 - net earnings: 117.37, commission: 187.16
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 15, 12, 0),
                      571.10, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 15, 16, 0), -
                      266.57, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 15, 17, 0), -
                      187.16, 19, "Commission"),
    ])

    # Wednesday 16.04.2025 - net earnings: -1756.62, commission: 336.16
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 16, 12, 0), -
                      1629.55, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 16, 16, 0),
                      209.09, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 16, 17, 0), -
                      336.16, 19, "Commission"),
    ])

    # Thursday 17.04.2025 - net earnings: -1974.19, commission: 276.17
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 17, 12, 0), -
                      2015.18, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 17, 16, 0),
                      317.16, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 17, 17, 0), -
                      276.17, 19, "Commission"),
    ])

    # Friday 18.04.2025 - net earnings: -430.00, commission: 194.73
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 18, 12, 0), -
                      319.87, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 18, 16, 0),
                      84.60, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 18, 17, 0), -
                      194.73, 19, "Commission"),
    ])

    # April Period 4: 21.04-25.04 (net profit: 4841.46, commission: 1192.49)
    # Monday 21.04.2025 - net earnings: 248.69, commission: 647.75
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 21, 12, 0), -
                      97.36, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 21, 16, 0),
                      993.80, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 21, 17, 0), -
                      647.75, 19, "Commission"),
    ])

    # Tuesday 22.04.2025 - net earnings: -863.98, commission: 489.18
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 22, 12, 0),
                      40.39, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 22, 16, 0), -
                      415.19, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 22, 17, 0), -
                      489.18, 19, "Commission"),
    ])

    # Wednesday 23.04.2025 - net earnings: 4721.54, commission: 55.56
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 23, 12, 0),
                      1140.48, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 23, 16, 0),
                      3636.62, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 23, 17, 0), -
                      55.56, 19, "Commission"),
    ])

    # Thursday 24.04.2025 - net earnings: -173.99, commission: 0
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 24, 12, 0), -
                      345.94, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 24, 16, 0),
                      171.95, 26, "Evening clearing"),
        # No commission for this day
    ])

    # Friday 25.04.2025 - net earnings: 909.20, commission: 0
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 25, 12, 0),
                      1085.39, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 25, 16, 0), -
                      176.19, 26, "Evening clearing"),
        # No commission for this day
    ])

    # April Period 5: 28.04-30.04 (net profit: 1228.83, commission: 1465.93)
    # Monday 28.04.2025 - net earnings: 1255.62, commission: 329.29
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 28, 12, 0), -
                      24.82, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 28, 16, 0),
                      1609.73, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 28, 17, 0), -
                      329.29, 19, "Commission"),
    ])

    # Tuesday 29.04.2025 - net earnings: 1699.86, commission: 118.98
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 29, 12, 0),
                      1262.92, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 29, 16, 0),
                      555.92, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 29, 17, 0), -
                      118.98, 19, "Commission"),
    ])

    # Wednesday 30.04.2025 - net earnings: -1726.65, commission: 1017.66
    operations.extend([
        MockOperation(datetime.datetime(2025, 4, 30, 12, 0),
                      701.46, 26, "Day clearing"),
        MockOperation(datetime.datetime(2025, 4, 30, 16, 0), -
                      1410.45, 26, "Evening clearing"),
        MockOperation(datetime.datetime(2025, 4, 30, 17, 0), -
                      1017.66, 19, "Commission"),
    ])

    return operations


def test_comprehensive_table_calculator():
    """Test the TableExactCalculator with comprehensive mock operations"""

    # Import the calculator
    from app.utils.profit_calculator import TableExactCalculator

    # Create calculator instance
    calculator = TableExactCalculator()

    # Create mock operations for all periods
    operations = create_mock_operations_for_all_periods()

    # Calculate analysis
    result = calculator.get_exact_table_analysis(
        operations, starting_balance=44127.39)

    print("=== COMPREHENSIVE TABLE EXACT CALCULATOR TEST ===")
    print(f"Starting balance: {44127.39}")
    print(
        f"Ending balance: {result['balance_progression'].get('2025-04-30', 0)}")

    print(f"\nSummary:")
    print(f"  Total earnings: {result['summary']['total_earnings']:.2f}")
    print(f"  Total commission: {result['summary']['total_commission']:.2f}")
    print(f"  Net profit: {result['summary']['total_profit']:.2f}")
    print(f"  Total trades: {result['summary']['total_trades']}")
    print(
        f"  Total day clearing: {result['summary']['total_day_clearing']:.2f}")
    print(
        f"  Total evening clearing: {result['summary']['total_evening_clearing']:.2f}")

    # Expected values from table analysis
    expected_total_profit = -13348.34  # Total for April from table
    expected_total_commission = 7834.31  # Sum of all commissions from table

    print(f"\nExpected from table:")
    print(f"  Total net profit: {expected_total_profit:.2f}")
    print(f"  Total commission: {expected_total_commission:.2f}")

    print(f"\nDifference:")
    print(
        f"  Net profit diff: {result['summary']['total_profit'] - expected_total_profit:.2f}")
    print(
        f"  Commission diff: {result['summary']['total_commission'] - expected_total_commission:.2f}")

    # Check if the result matches the table
    if abs(result['summary']['total_profit'] - expected_total_profit) < 0.01:
        print("✅ SUCCESS: Calculator matches table data!")
    else:
        print("❌ FAILURE: Calculator doesn't match table data")

    # Print daily breakdown for verification
    print(f"\nDaily breakdown (first 5 days):")
    for i, (date, data) in enumerate(sorted(result['daily_data'].items())):
        if i >= 5:  # Only show first 5 days
            break
        print(
            f"  {date}: net={data['total_profit']:.2f}, commission={data['commission']:.2f}")


if __name__ == "__main__":
    test_comprehensive_table_calculator()
