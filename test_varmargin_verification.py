#!/usr/bin/env python3
"""
Test script to verify variation margin handling - updated for time-based assignment
"""
from tinkoff.invest.grpc.operations_pb2 import OperationType
from app.utils.quotation import Quotation
from app.utils.profit_calculator import ProfitCalculator
import unittest
import datetime
from unittest.mock import Mock
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestVariationMarginHandling(unittest.TestCase):
    """Test variation margin handling specifically"""

    def setUp(self):
        """Set up test fixtures"""
        self.calculator = ProfitCalculator()

    def create_mock_operation(self, op_type: OperationType, figi: str, quantity: int,
                              price: float, payment: float, date: datetime.datetime,
                              operation_id: str = None):
        """Create a mock operation for testing"""
        operation = Mock()
        operation.operation_type = op_type
        operation.figi = figi
        operation.quantity = quantity
        operation.price = Quotation(
            units=int(price), nano=int((price % 1) * 1_000_000_000))
        operation.payment = Quotation(
            units=int(payment), nano=int((payment % 1) * 1_000_000_000))
        operation.date = date
        operation.id = operation_id or f"op_{op_type}_{figi}_{quantity}_{price}"
        operation.instrument_uid = figi
        return operation

    def test_variation_margin_time_based_assignment(self):
        """Test that variation margin is assigned based on trade timing"""
        base_date = datetime.datetime(2025, 7, 16, 10, 0, 0)

        # Create operations with variation margin DURING the trade
        operations = [
            # Buy operation
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FUTNG0725000", 10, 3.53, -35300.0, base_date
            ),
            # Variation margin accrual DURING the trade
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
                "", 0, 0.0, 1000.0, base_date + datetime.timedelta(minutes=30)
            ),
            # Sell operation
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FUTNG0725000", 10, 3.57, 35700.0, base_date +
                datetime.timedelta(hours=1)
            ),
            # Broker fees
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FUTNG0725000", 0, 0.0, -50.0, base_date +
                datetime.timedelta(minutes=1)
            ),
        ]

        # Process operations
        trades, total_profit, processed_operations = self.calculator.process_operations(
            operations)

        # Should have 1 trade
        self.assertEqual(len(trades), 1)

        trade = trades[0]

        # Check that variation margin is included
        expected_gross_profit = (3.57 - 3.53) * 10  # 0.40
        expected_fees = 50.0
        expected_variation_margin = 1000.0  # Occurred during trade
        expected_net_profit = expected_gross_profit - \
            expected_fees + expected_variation_margin

        print(f"Trade details (time-based assignment):")
        print(f"  Entry time: {trade.entry_time}")
        print(f"  Exit time: {trade.exit_time}")
        print(f"  Gross profit: {trade.gross_profit}")
        print(f"  Fees: {trade.fees}")
        print(f"  Net profit: {trade.net_profit}")
        print(f"  Expected net profit: {expected_net_profit}")

        self.assertAlmostEqual(
            trade.gross_profit, expected_gross_profit, places=2)
        self.assertAlmostEqual(trade.fees, expected_fees, places=2)
        self.assertAlmostEqual(trade.net_profit, expected_net_profit, places=2)

        # Total profit should equal the net profit of the trade
        self.assertAlmostEqual(total_profit, expected_net_profit, places=2)

    def test_variation_margin_outside_trade_period(self):
        """Test that variation margin OUTSIDE trade period is not assigned"""
        base_date = datetime.datetime(2025, 7, 16, 10, 0, 0)

        operations = [
            # Buy operation
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FUTNG0725000", 10, 3.53, -35300.0, base_date
            ),
            # Sell operation
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FUTNG0725000", 10, 3.57, 35700.0, base_date +
                datetime.timedelta(hours=1)
            ),
            # Variation margin AFTER the trade (should NOT be assigned)
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
                "", 0, 0.0, 1000.0, base_date + datetime.timedelta(hours=2)
            ),
        ]

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        self.assertEqual(len(trades), 1)
        trade = trades[0]

        # Variation margin should NOT be included (it was after the trade)
        expected_gross_profit = (3.57 - 3.53) * 10  # 0.40
        expected_fees = 0.0  # No fees
        expected_net_profit = expected_gross_profit - \
            expected_fees  # No variation margin

        print(f"Trade details (margin outside period):")
        print(f"  Entry time: {trade.entry_time}")
        print(f"  Exit time: {trade.exit_time}")
        print(f"  Gross profit: {trade.gross_profit}")
        print(f"  Fees: {trade.fees}")
        print(f"  Net profit: {trade.net_profit}")
        print(f"  Expected net profit: {expected_net_profit}")

        self.assertAlmostEqual(trade.net_profit, expected_net_profit, places=2)

    def test_multiple_trades_separate_margins(self):
        """Test that each trade gets its own variation margin"""
        base_date = datetime.datetime(2025, 7, 16, 10, 0, 0)

        operations = [
            # First trade
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FUTNG0725000", 10, 3.50, -35000.0, base_date
            ),
            # Variation margin for first trade
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
                "", 0, 0.0, 500.0, base_date + datetime.timedelta(minutes=15)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FUTNG0725000", 10, 3.60, 36000.0, base_date +
                datetime.timedelta(minutes=30)
            ),

            # Second trade
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FUTSI0725000", 5, 100.0, -50000.0, base_date +
                datetime.timedelta(hours=1)
            ),
            # Variation margin for second trade
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
                "", 0, 0.0, 300.0, base_date +
                datetime.timedelta(hours=1, minutes=15)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FUTSI0725000", 5, 102.0, 51000.0, base_date +
                datetime.timedelta(hours=1, minutes=30)
            ),
        ]

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        self.assertEqual(len(trades), 2)

        # Find trades by instrument
        ng_trade = next(t for t in trades if t.figi == "FUTNG0725000")
        si_trade = next(t for t in trades if t.figi == "FUTSI0725000")

        # Check first trade got first margin
        expected_ng_net = (3.60 - 3.50) * 10 + 500.0  # 1000 + 500 = 1500
        expected_si_net = (102.0 - 100.0) * 5 + 300.0  # 1000 + 300 = 1300

        print(
            f"First trade net profit: {ng_trade.net_profit}, expected: {expected_ng_net}")
        print(
            f"Second trade net profit: {si_trade.net_profit}, expected: {expected_si_net}")

        self.assertAlmostEqual(ng_trade.net_profit, expected_ng_net, places=2)
        self.assertAlmostEqual(si_trade.net_profit, expected_si_net, places=2)


if __name__ == '__main__':
    unittest.main()
