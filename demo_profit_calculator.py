#!/usr/bin/env python3
"""
Demonstration of the new profit calculation system
"""
from tinkoff.invest import Quotation
from tinkoff.invest.grpc.operations_pb2 import OperationType
from app.utils.profit_calculator import ProfitCalculator
from typing import List
from dataclasses import dataclass
import datetime
import os
import sys
os.environ['TESTING'] = '1'  # Set testing flag

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class MockOperation:
    """Mock operation for testing"""
    id: str
    operation_type: OperationType
    date: datetime.datetime
    figi: str
    quantity: int
    price: Quotation
    payment: Quotation

    def __init__(self, id: str, operation_type: OperationType, date: datetime.datetime,
                 figi: str, quantity: int, price: float, payment: float):
        self.id = id
        self.operation_type = operation_type
        self.date = date
        self.figi = figi
        self.quantity = quantity
        self.price = Quotation(
            units=int(price), nano=int((price % 1) * 1000000000))
        self.payment = Quotation(
            units=int(payment), nano=int((payment % 1) * 1000000000))


def create_sample_operations() -> List[MockOperation]:
    """Create sample operations based on the spreadsheet data"""
    operations = []

    # March operations
    operations.append(MockOperation(
        id="1", operation_type=OperationType.OPERATION_TYPE_BUY,
        date=datetime.datetime(2025, 3, 31, 10, 0),
        figi="BBG004730N88", quantity=2, price=4.25, payment=-8.50
    ))

    operations.append(MockOperation(
        id="2", operation_type=OperationType.OPERATION_TYPE_SELL,
        date=datetime.datetime(2025, 3, 31, 15, 0),
        figi="BBG004730N88", quantity=2, price=4.20, payment=8.40
    ))

    operations.append(MockOperation(
        id="3", operation_type=OperationType.OPERATION_TYPE_BROKER_FEE,
        date=datetime.datetime(2025, 3, 31, 15, 1),
        figi="BBG004730N88", quantity=0, price=0, payment=-0.10
    ))

    # April operations
    operations.append(MockOperation(
        id="4", operation_type=OperationType.OPERATION_TYPE_BUY,
        date=datetime.datetime(2025, 4, 7, 10, 15),
        figi="BBG004730N88", quantity=3, price=4.30, payment=-12.90
    ))

    operations.append(MockOperation(
        id="5", operation_type=OperationType.OPERATION_TYPE_SELL,
        date=datetime.datetime(2025, 4, 7, 16, 15),
        figi="BBG004730N88", quantity=3, price=4.35, payment=13.05
    ))

    operations.append(MockOperation(
        id="6", operation_type=OperationType.OPERATION_TYPE_BROKER_FEE,
        date=datetime.datetime(2025, 4, 7, 16, 16),
        figi="BBG004730N88", quantity=0, price=0, payment=-0.15
    ))

    # Large profitable trade
    operations.append(MockOperation(
        id="7", operation_type=OperationType.OPERATION_TYPE_BUY,
        date=datetime.datetime(2025, 4, 21, 11, 0),
        figi="BBG004730N88", quantity=100, price=4.20, payment=-420.00
    ))

    operations.append(MockOperation(
        id="8", operation_type=OperationType.OPERATION_TYPE_SELL,
        date=datetime.datetime(2025, 4, 25, 14, 0),
        figi="BBG004730N88", quantity=100, price=4.72, payment=472.00
    ))

    operations.append(MockOperation(
        id="9", operation_type=OperationType.OPERATION_TYPE_BROKER_FEE,
        date=datetime.datetime(2025, 4, 25, 14, 1),
        figi="BBG004730N88", quantity=0, price=0, payment=-1.50
    ))

    return operations


def demonstrate_profit_calculator():
    """Demonstrate the profit calculator capabilities"""
    print("=" * 80)
    print("TINK TRADING BOT - PROFIT CALCULATOR DEMONSTRATION")
    print("=" * 80)

    # Create sample operations
    operations = create_sample_operations()

    print(f"\n📊 SAMPLE OPERATIONS ({len(operations)} total):")
    print("-" * 60)
    for i, op in enumerate(operations, 1):
        op_type = {
            15: "BUY",
            22: "SELL",
            19: "BROKER_FEE"
        }.get(op.operation_type, "UNKNOWN")

        if op.quantity > 0:
            print(f"{i:2d}. {op.date.strftime('%Y-%m-%d %H:%M')} | {op_type:10s} | {op.quantity:3d} @ {op.price.units + op.price.nano/1e9:.2f} | Payment: {op.payment.units + op.payment.nano/1e9:.2f}")
        else:
            print(f"{i:2d}. {op.date.strftime('%Y-%m-%d %H:%M')} | {op_type:10s} | Fee: {abs(op.payment.units + op.payment.nano/1e9):.2f}")

    # Initialize calculator
    calculator = ProfitCalculator()

    # Process operations
    print("\n🔄 PROCESSING OPERATIONS...")
    trades, total_profit, _ = calculator.process_operations(operations)

    # Display results
    print(f"\n📈 TRADE RESULTS:")
    print("-" * 80)
    print(f"{'#':<3} {'Entry':<16} {'Exit':<16} {'Dir':<6} {'Qty':<6} {'Entry$':<8} {'Exit$':<8} {'Gross$':<10} {'Fees$':<8} {'Net$':<10}")
    print("-" * 80)

    for i, trade in enumerate(trades, 1):
        print(f"{i:<3} {trade.entry_time.strftime('%Y-%m-%d %H:%M'):<16} {trade.exit_time.strftime('%Y-%m-%d %H:%M'):<16} "
              f"{trade.direction:<6} {trade.quantity:<6} {trade.entry_price:<8.2f} {trade.exit_price:<8.2f} "
              f"{trade.gross_profit:<10.2f} {trade.fees:<8.2f} {trade.net_profit:<10.2f}")

    print("-" * 80)
    print(f"{'TOTAL PROFIT:':<70} {total_profit:.2f}")

    # Period analysis
    print(f"\n📅 MONTHLY PROFIT ANALYSIS:")
    print("-" * 60)
    monthly_periods = calculator.get_monthly_profit_analysis(operations)

    for period in monthly_periods:
        print(f"{period.start_date.strftime('%Y-%m')}: "
              f"Profit: {period.net_profit:.2f}, "
              f"Trades: {period.trades_count}, "
              f"Win/Loss: {period.winning_trades}/{period.losing_trades}")

    # Statistics
    print(f"\n📊 STATISTICS:")
    print("-" * 40)
    winning_trades = len([t for t in trades if t.net_profit > 0])
    losing_trades = len([t for t in trades if t.net_profit < 0])
    total_fees = sum(t.fees for t in trades)

    print(f"Total Trades: {len(trades)}")
    print(f"Winning Trades: {winning_trades}")
    print(f"Losing Trades: {losing_trades}")
    print(
        f"Win Rate: {winning_trades/len(trades)*100:.1f}%" if trades else "N/A")
    print(f"Total Fees: {total_fees:.2f}")
    print(
        f"Average Profit per Trade: {total_profit/len(trades):.2f}" if trades else "N/A")

    print(f"\n✅ Demonstration completed successfully!")
    print("=" * 80)


def demonstrate_api_integration():
    """Demonstrate API integration with the new system"""
    print(f"\n🔗 API INTEGRATION EXAMPLES:")
    print("-" * 40)

    print("1. Get 30-day profit analysis:")
    print("   GET /api/profit-analysis?days=30")

    print("\n2. Get March 2025 profit analysis:")
    print("   GET /api/period-profit?start_date=2025-03-01T00:00:00&end_date=2025-03-31T23:59:59&starting_balance=44127.39")

    print("\n3. Sample API Response:")
    print("""   {
       "total_profit": 195.0,
       "trades_count": 3,
       "winning_trades": 2,
       "losing_trades": 1,
       "average_profit_per_trade": 65.0,
       "monthly_analysis": [...],
       "weekly_analysis": [...],
       "recent_trades": [...]
   }""")


if __name__ == "__main__":
    demonstrate_profit_calculator()
    demonstrate_api_integration()
