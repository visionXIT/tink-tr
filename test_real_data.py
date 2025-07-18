#!/usr/bin/env python3
"""
Test script to verify profit calculations with real historical data from Tinkoff
"""
from tinkoff.invest.grpc.operations_pb2 import OperationType
from app.utils.quotation import quotation_to_float
from app.utils.profit_calculator import ProfitCalculator
from app.settings import settings
from app.client import client
import os
import sys
import asyncio
import datetime
from typing import List, Dict
import pytz

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def get_recent_operations(days: int = 30):
    """Get recent operations from the last N days"""
    if client.client is None:
        await client.ainit()

    # Define date range for recent operations
    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.datetime.now(moscow_tz)
    start_date = end_date - datetime.timedelta(days=days)

    print(f"Fetching operations from {start_date} to {end_date}")

    try:
        operations_response = await client.get_operations(
            account_id=settings.account_id,
            from_=start_date,
            to=end_date
        )

        if not operations_response or not operations_response.operations:
            print("No operations found for the specified period")
            return []

        # Filter and sort operations
        operations = sorted(operations_response.operations,
                            key=lambda x: x.date)

        print(f"Found {len(operations)} operations")
        return operations

    except Exception as e:
        print(f"Error fetching operations: {e}")
        return []


def show_operations_detail(operations: List):
    """Show detailed information about operations"""
    print(f"\n📋 OPERATIONS DETAIL:")
    print("-" * 90)
    print(f"{'Date':<17} {'Type':<20} {'FIGI':<12} {'Qty':<6} {'Price':<10} {'Payment':<12}")
    print("-" * 90)

    for op in operations:
        op_type_name = get_operation_type_name(op.operation_type)
        payment = quotation_to_float(op.payment)

        if hasattr(op, 'price') and op.price:
            price = quotation_to_float(op.price)
        else:
            price = 0.0

        figi = getattr(op, 'figi', 'N/A')[:12]
        quantity = getattr(op, 'quantity', 0)

        # Convert timezone-aware datetime to string
        date_str = op.date.strftime('%Y-%m-%d %H:%M') if op.date else 'N/A'

        print(f"{date_str:<17} {op_type_name:<20} {figi:<12} {quantity:<6} {price:<10.2f} {payment:<12.2f}")


def calculate_weekly_profits(operations: List) -> Dict:
    """Calculate weekly profits from operations"""
    if not operations:
        return {}

    # Group operations by week
    weekly_operations = {}

    for op in operations:
        # Get the Monday of the week for this operation
        monday = op.date - datetime.timedelta(days=op.date.weekday())
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        week_key = monday.strftime('%Y-%m-%d')

        if week_key not in weekly_operations:
            weekly_operations[week_key] = []
        weekly_operations[week_key].append(op)

    # Calculate profit for each week
    weekly_profits = {}
    calculator = ProfitCalculator()

    for week_key, week_ops in weekly_operations.items():
        # Parse the week_key back to timezone-aware datetime
        moscow_tz = pytz.timezone('Europe/Moscow')
        monday = moscow_tz.localize(
            datetime.datetime.strptime(week_key, '%Y-%m-%d'))
        sunday = monday + \
            datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)

        profit = calculator.calculate_period_profit_real(
            week_ops, monday, sunday)
        weekly_profits[week_key] = profit

    return weekly_profits


def get_operation_type_name(operation_type) -> str:
    """Get human-readable operation type name"""
    type_mapping = {
        OperationType.OPERATION_TYPE_BUY: "BUY",
        OperationType.OPERATION_TYPE_SELL: "SELL",
        OperationType.OPERATION_TYPE_BROKER_FEE: "BROKER_FEE",
        OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN: "VARMARGIN_WRITE_OFF",
        OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN: "VARMARGIN_ACCRUAL",
        OperationType.OPERATION_TYPE_SERVICE_FEE: "SERVICE_FEE",
        OperationType.OPERATION_TYPE_BENEFIT_TAX: "BENEFIT_TAX",
        OperationType.OPERATION_TYPE_MARGIN_FEE: "MARGIN_FEE",
        OperationType.OPERATION_TYPE_BUY_CARD: "BUY_CARD",
        OperationType.OPERATION_TYPE_SELL_CARD: "SELL_CARD",
    }
    return type_mapping.get(operation_type, f"UNKNOWN_{operation_type}")


async def test_with_real_data():
    """Test profit calculations with real data"""
    print("=" * 80)
    print("TESTING PROFIT CALCULATIONS WITH REAL TINKOFF DATA")
    print("=" * 80)

    # Get recent operations
    operations = await get_recent_operations(days=30)

    if not operations:
        print("No operations data available. Cannot test calculations.")
        return

    # Show operations detail (first 20 operations)
    print(f"Showing first 20 operations out of {len(operations)}")
    show_operations_detail(operations[:20])

    # Analyze operation types
    operation_types = {}
    total_payment = 0.0

    for op in operations:
        op_type_name = get_operation_type_name(op.operation_type)
        payment = quotation_to_float(op.payment)

        if op_type_name not in operation_types:
            operation_types[op_type_name] = {'count': 0, 'total_payment': 0.0}

        operation_types[op_type_name]['count'] += 1
        operation_types[op_type_name]['total_payment'] += payment
        total_payment += payment

    print(f"\n📊 OPERATION TYPES SUMMARY:")
    print("-" * 60)
    print(f"{'Type':<20} {'Count':<8} {'Total Payment':<15}")
    print("-" * 60)

    for op_type, data in operation_types.items():
        print(
            f"{op_type:<20} {data['count']:<8} {data['total_payment']:<15.2f}")

    print("-" * 60)
    print(f"{'TOTAL':<20} {len(operations):<8} {total_payment:<15.2f}")

    # Calculate weekly profits
    weekly_profits = calculate_weekly_profits(operations)

    if weekly_profits:
        print(f"\n📈 WEEKLY PROFITS:")
        print("-" * 40)
        print(f"{'Week Starting':<15} {'Profit (RUB)':<12}")
        print("-" * 40)

        total_profit = 0.0
        for week, profit in sorted(weekly_profits.items()):
            print(f"{week:<15} {profit:<12.2f}")
            total_profit += profit

        print("-" * 40)
        print(f"{'TOTAL':<15} {total_profit:<12.2f}")

    # Test the new profit calculator
    calculator = ProfitCalculator()
    trades, trades_total_profit, _ = calculator.process_operations(operations)

    print(f"\n📊 PROFIT CALCULATOR RESULTS:")
    print(f"Total trades completed: {len(trades)}")
    print(f"Total profit from trades: {trades_total_profit:.2f} RUB")

    if trades:
        print(f"\nRecent trades:")
        for i, trade in enumerate(trades[-5:], 1):  # Show last 5 trades
            print(
                f"  {i}. {trade.entry_time.strftime('%Y-%m-%d')} -> {trade.exit_time.strftime('%Y-%m-%d')}")
            print(
                f"     {trade.direction} {trade.quantity} @ {trade.entry_price:.2f} -> {trade.exit_price:.2f}")
            print(
                f"     Gross: {trade.gross_profit:.2f}, Fees: {trade.fees:.2f}, Net: {trade.net_profit:.2f}")

    # Show variation margin summary
    var_margin_total = 0
    var_margin_count = 0

    for op in operations:
        if op.operation_type in [OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                                 OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN]:
            var_margin_total += quotation_to_float(op.payment)
            var_margin_count += 1

    print(f"\n💰 VARIATION MARGIN SUMMARY:")
    print(f"Variation margin operations: {var_margin_count}")
    print(f"Total variation margin: {var_margin_total:.2f} RUB")

    # Compare different calculation methods
    print(f"\n🔍 CALCULATION METHOD COMPARISON:")
    print(f"Direct payment sum: {total_payment:.2f} RUB")
    print(f"Weekly profits sum: {sum(weekly_profits.values()):.2f} RUB")
    print(f"Trade-based profit: {trades_total_profit:.2f} RUB")

    print(f"\n✅ Test completed successfully!")


async def main():
    """Main function"""
    await test_with_real_data()


if __name__ == "__main__":
    asyncio.run(main())
