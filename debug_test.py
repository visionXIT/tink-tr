#!/usr/bin/env python3
"""
Debug test to understand the fee assignment issue
"""
from tinkoff.invest import Quotation
from tinkoff.invest.grpc.operations_pb2 import OperationType
from app.utils.profit_calculator import ProfitCalculator
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


def debug_profit_calculator():
    """Debug the profit calculator"""
    calculator = ProfitCalculator()

    operations = [
        MockOperation("1", OperationType.OPERATION_TYPE_BUY,
                      datetime.datetime(2025, 3, 1, 10, 0),
                      "TEST_FIGI", 100, 10.0, -1000.0),
        MockOperation("2", OperationType.OPERATION_TYPE_SELL,
                      datetime.datetime(2025, 3, 1, 15, 0),
                      "TEST_FIGI", 100, 12.0, 1200.0),
        MockOperation("3", OperationType.OPERATION_TYPE_BROKER_FEE,
                      datetime.datetime(2025, 3, 1, 15, 1),
                      "TEST_FIGI", 0, 0, -5.0)
    ]

    print("Operations:")
    for op in operations:
        print(f"  {op.id}: {op.operation_type} {op.quantity} @ {op.price.units}.{op.price.nano} (payment: {op.payment.units}.{op.payment.nano})")

    print("\nProcessing operations...")

    # Process operations step by step
    for i, operation in enumerate(operations):
        print(f"\nProcessing operation {i+1}: {operation.id}")
        calculator._process_single_operation(operation)

        print(f"  Positions: {dict(calculator.positions)}")
        print(f"  Completed trades: {len(calculator.completed_trades)}")
        print(f"  Fees buffer: {calculator.fees_buffer}")

        if calculator.completed_trades:
            trade = calculator.completed_trades[-1]
            print(
                f"  Last trade: {trade.direction} {trade.quantity} @ {trade.entry_price}->{trade.exit_price} profit={trade.gross_profit} fees={trade.fees} net={trade.net_profit}")

    print(f"\nFinal results:")
    trades, total_profit, _ = calculator.process_operations(operations)

    print(f"Number of trades: {len(trades)}")
    if trades:
        trade = trades[0]
        print(
            f"Trade: {trade.direction} {trade.quantity} @ {trade.entry_price}->{trade.exit_price}")
        print(f"Gross profit: {trade.gross_profit}")
        print(f"Fees: {trade.fees}")
        print(f"Net profit: {trade.net_profit}")

    print(f"Total profit: {total_profit}")


if __name__ == "__main__":
    debug_profit_calculator()
