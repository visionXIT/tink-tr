#!/usr/bin/env python3
"""
Demonstration of the starting position issue and its solution
Shows how the first trade profit calculation can be incorrect without proper starting positions
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
import pytz

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def demonstrate_starting_position_issue():
    """Demonstrate the starting position issue and its solution"""
    print("=" * 80)
    print("STARTING POSITION ISSUE DEMONSTRATION")
    print("=" * 80)

    if client.client is None:
        await client.ainit()

    # Get operations for the last 100 days (where issue typically occurs)
    moscow_tz = pytz.timezone('Europe/Moscow')
    end_date = datetime.datetime.now(moscow_tz)
    start_date = end_date - datetime.timedelta(days=100)

    print(f"Fetching operations from {start_date} to {end_date}")

    try:
        operations_response = await client.get_operations(
            account_id=settings.account_id,
            from_=start_date,
            to=end_date
        )

        if not operations_response or not operations_response.operations:
            print("No operations found for the specified period")
            return

        operations = sorted(operations_response.operations,
                            key=lambda x: x.date)
        print(f"Found {len(operations)} operations")

    except Exception as e:
        print(f"Error fetching operations: {e}")
        return

    # Filter only trading operations to analyze the issue
    trading_operations = [op for op in operations if op.operation_type in [
        OperationType.OPERATION_TYPE_BUY,
        OperationType.OPERATION_TYPE_SELL
    ]]

    print(f"Found {len(trading_operations)} trading operations")

    if not trading_operations:
        print("No trading operations found")
        return

    # Show first few operations
    print("\n📋 FIRST 10 TRADING OPERATIONS:")
    print("-" * 80)
    print(f"{'Date':<17} {'Type':<6} {'FIGI':<12} {'Qty':<6} {'Price':<10} {'Payment':<12}")
    print("-" * 80)

    for i, op in enumerate(trading_operations[:10]):
        op_type = "BUY" if op.operation_type == OperationType.OPERATION_TYPE_BUY else "SELL"
        price = quotation_to_float(op.price)
        payment = quotation_to_float(op.payment)
        figi = op.figi[:12]
        date_str = op.date.strftime('%Y-%m-%d %H:%M')

        print(
            f"{date_str:<17} {op_type:<6} {figi:<12} {op.quantity:<6} {price:<10.2f} {payment:<12.2f}")

    calculator = ProfitCalculator()

    print("\n🔍 PROBLEM ANALYSIS:")
    print("-" * 50)

    # Method 1: Traditional approach (without starting positions)
    print("\n1️⃣ TRADITIONAL APPROACH (WITHOUT STARTING POSITIONS):")
    trades1, total_profit1, _ = calculator.process_operations(
        trading_operations)

    print(f"   Total trades: {len(trades1)}")
    print(f"   Total profit: {total_profit1:.2f} RUB")

    if trades1:
        first_trade = trades1[0]
        print(f"   First trade profit: {first_trade.net_profit:.2f} RUB")
        print(
            f"   First trade details: {first_trade.direction} {first_trade.quantity} @ {first_trade.entry_price:.2f} -> {first_trade.exit_price:.2f}")

        # Check if the first trade has an unusually large loss
        if first_trade.net_profit < -50000:
            print("   ⚠️  WARNING: First trade shows unusually large loss!")
            print("   This is likely due to missing starting position information")

    # Method 2: With auto-detected starting positions
    print("\n2️⃣ WITH AUTO-DETECTED STARTING POSITIONS:")
    trades2, total_profit2, _, starting_positions = calculator.process_operations_with_auto_positions(
        trading_operations)

    print(f"   Total trades: {len(trades2)}")
    print(f"   Total profit: {total_profit2:.2f} RUB")
    print(f"   Auto-detected starting positions: {starting_positions}")

    if trades2:
        first_trade = trades2[0]
        print(f"   First trade profit: {first_trade.net_profit:.2f} RUB")
        print(
            f"   First trade details: {first_trade.direction} {first_trade.quantity} @ {first_trade.entry_price:.2f} -> {first_trade.exit_price:.2f}")

    # Method 3: With calculated starting positions (using current positions)
    print("\n3️⃣ WITH CALCULATED STARTING POSITIONS (USING CURRENT POSITIONS):")
    try:
        trades3, total_profit3, _, calculated_positions = await client.get_profit_analysis_with_auto_positions(
            settings.account_id, start_date, end_date)

        print(f"   Total trades: {len(trades3)}")
        print(f"   Total profit: {total_profit3:.2f} RUB")
        print(f"   Calculated starting positions: {calculated_positions}")

        if trades3:
            first_trade = trades3[0]
            print(f"   First trade profit: {first_trade.net_profit:.2f} RUB")
            print(
                f"   First trade details: {first_trade.direction} {first_trade.quantity} @ {first_trade.entry_price:.2f} -> {first_trade.exit_price:.2f}")
    except Exception as e:
        print(f"   Error calculating with current positions: {e}")

    print("\n📊 COMPARISON OF METHODS:")
    print("-" * 50)
    print(f"Traditional approach:     {total_profit1:.2f} RUB")
    print(f"Auto-detected positions:  {total_profit2:.2f} RUB")
    try:
        print(f"Current positions based:  {total_profit3:.2f} RUB")
    except:
        print("Current positions based:  N/A")

    # Show position analysis for first few instruments
    print("\n🎯 STARTING POSITION ANALYSIS:")
    print("-" * 50)

    position_analysis = calculator.analyze_starting_positions(
        trading_operations)

    # Show first 3 instruments
    for figi, analysis in list(position_analysis.items())[:3]:
        print(f"\nInstrument: {figi}")
        print(
            f"First operation: {analysis['first_operation']['type']} {analysis['first_operation']['quantity']} @ {analysis['first_operation']['price']:.2f}")
        print(f"Possible scenarios:")

        for i, scenario in enumerate(analysis['possible_scenarios'], 1):
            print(f"  {i}. {scenario['description']}")
            print(f"     Starting position: {scenario['starting_position']}")
            print(f"     Crosses zero: {scenario['crosses_zero']}")

    print(f"\n💡 SOLUTION RECOMMENDATIONS:")
    print("-" * 50)
    print("1. Use 'get_profit_analysis_with_auto_positions' method for most accurate results")
    print("2. This method calculates starting positions by working backwards from current positions")
    print("3. It accounts for positions that existed before the analysis period")
    print("4. For real-time applications, consider caching starting positions")
    print("5. The auto-detection method is useful when current positions are unknown")


async def main():
    """Main function"""
    await demonstrate_starting_position_issue()


if __name__ == "__main__":
    asyncio.run(main())
