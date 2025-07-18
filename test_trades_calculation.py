#!/usr/bin/env python3
"""
Tests for trades calculation to ensure correct profit distribution
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


class TestTradesCalculation(unittest.TestCase):
    """Test cases for trades calculation"""

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

    def test_simple_trade_calculation(self):
        """Test simple buy-sell trade calculation"""
        base_date = datetime.datetime(2025, 1, 1, 10, 0, 0)

        # Create operations: buy 100 shares at 10.00, sell 100 shares at 12.00
        operations = [
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FIGI001", 100, 10.0, -1000.0, base_date
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FIGI001", 100, 12.0, 1200.0, base_date +
                datetime.timedelta(hours=1)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FIGI001", 0, 0.0, -10.0, base_date +
                datetime.timedelta(minutes=1)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FIGI001", 0, 0.0, -10.0, base_date +
                datetime.timedelta(hours=1, minutes=1)
            ),
        ]

        trades, total_profit, processed_operations = self.calculator.process_operations(
            operations)

        # Should have 1 trade
        self.assertEqual(len(trades), 1)

        trade = trades[0]
        self.assertEqual(trade.figi, "FIGI001")
        self.assertEqual(trade.quantity, 100)
        self.assertEqual(trade.entry_price, 10.0)
        self.assertEqual(trade.exit_price, 12.0)
        self.assertEqual(trade.direction, "LONG")

        # Gross profit should be (12.0 - 10.0) * 100 = 200.0
        self.assertEqual(trade.gross_profit, 200.0)

        # Fees should be 20.0 (10.0 + 10.0)
        self.assertEqual(trade.fees, 20.0)

        # Net profit should be 200.0 - 20.0 = 180.0
        self.assertEqual(trade.net_profit, 180.0)

        # Total profit should equal net profit of the trade
        self.assertEqual(total_profit, 180.0)

    def test_multiple_trades_different_volumes(self):
        """Test multiple trades with different volumes get proportional fees"""
        base_date = datetime.datetime(2025, 1, 1, 10, 0, 0)

        # Create operations:
        # Trade 1: buy 100 shares at 10.00, sell 100 shares at 11.00 (small trade)
        # Trade 2: buy 1000 shares at 20.00, sell 1000 shares at 22.00 (large trade)
        operations = [
            # Trade 1
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FIGI001", 100, 10.0, -1000.0, base_date
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FIGI001", 100, 11.0, 1100.0, base_date +
                datetime.timedelta(hours=1)
            ),

            # Trade 2
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FIGI002", 1000, 20.0, -20000.0, base_date +
                datetime.timedelta(hours=2)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FIGI002", 1000, 22.0, 22000.0, base_date +
                datetime.timedelta(hours=3)
            ),

            # Total fees: 100.0
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FIGI001", 0, 0.0, -50.0, base_date +
                datetime.timedelta(minutes=1)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FIGI002", 0, 0.0, -50.0, base_date +
                datetime.timedelta(hours=2, minutes=1)
            ),
        ]

        trades, total_profit, processed_operations = self.calculator.process_operations(
            operations)

        # Should have 2 trades
        self.assertEqual(len(trades), 2)

        # Find trades
        trade1 = next(t for t in trades if t.figi == "FIGI001")
        trade2 = next(t for t in trades if t.figi == "FIGI002")

        # Trade 1: gross profit = (11.0 - 10.0) * 100 = 100.0
        self.assertEqual(trade1.gross_profit, 100.0)

        # Trade 2: gross profit = (22.0 - 20.0) * 1000 = 2000.0
        self.assertEqual(trade2.gross_profit, 2000.0)

        # Trade 2 should have higher fees due to larger volume
        self.assertGreater(trade2.fees, trade1.fees)

        # Total fees should be 100.0
        self.assertAlmostEqual(trade1.fees + trade2.fees, 100.0, places=2)

        # Net profits should be different (not equal like before)
        self.assertNotEqual(trade1.net_profit, trade2.net_profit)

        # Total profit should be sum of net profits
        self.assertAlmostEqual(
            total_profit, trade1.net_profit + trade2.net_profit, places=2)

    def test_variation_margin_distribution(self):
        """Test that variation margin is distributed proportionally"""
        base_date = datetime.datetime(2025, 1, 1, 10, 0, 0)

        # Create operations with variation margin
        operations = [
            # Trade 1: small trade
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FIGI001", 100, 10.0, -1000.0, base_date
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FIGI001", 100, 11.0, 1100.0, base_date +
                datetime.timedelta(hours=1)
            ),

            # Trade 2: large trade
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FIGI002", 1000, 20.0, -20000.0, base_date +
                datetime.timedelta(hours=2)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FIGI002", 1000, 22.0, 22000.0, base_date +
                datetime.timedelta(hours=3)
            ),

            # Variation margin: 500.0
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
                "", 0, 0.0, 500.0, base_date + datetime.timedelta(hours=4)
            ),

            # Fees: 100.0
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FIGI001", 0, 0.0, -100.0, base_date +
                datetime.timedelta(minutes=1)
            ),
        ]

        trades, total_profit, processed_operations = self.calculator.process_operations(
            operations)

        # Should have 2 trades
        self.assertEqual(len(trades), 2)

        # Find trades
        trade1 = next(t for t in trades if t.figi == "FIGI001")
        trade2 = next(t for t in trades if t.figi == "FIGI002")

        # Both trades should have positive impact from variation margin
        # But trade2 should get more margin due to larger volume
        trade1_margin_impact = trade1.net_profit - \
            (trade1.gross_profit - trade1.fees)
        trade2_margin_impact = trade2.net_profit - \
            (trade2.gross_profit - trade2.fees)

        self.assertGreater(trade1_margin_impact, 0)  # Should be positive
        self.assertGreater(trade2_margin_impact, 0)  # Should be positive
        # Trade2 should get more
        self.assertGreater(trade2_margin_impact, trade1_margin_impact)

        # Total margin impact should be close to 500.0
        self.assertAlmostEqual(trade1_margin_impact +
                               trade2_margin_impact, 500.0, places=2)

    def test_zero_profit_trades(self):
        """Test handling of zero profit trades"""
        base_date = datetime.datetime(2025, 1, 1, 10, 0, 0)

        # Create operations with zero profit
        operations = [
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FIGI001", 100, 10.0, -1000.0, base_date
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FIGI001", 100, 10.0, 1000.0, base_date +
                datetime.timedelta(hours=1)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FIGI001", 0, 0.0, -10.0, base_date +
                datetime.timedelta(minutes=1)
            ),
        ]

        trades, total_profit, processed_operations = self.calculator.process_operations(
            operations)

        # Should have 1 trade
        self.assertEqual(len(trades), 1)

        trade = trades[0]
        self.assertEqual(trade.gross_profit, 0.0)
        self.assertEqual(trade.fees, 10.0)
        self.assertEqual(trade.net_profit, -10.0)  # Loss due to fees

    def test_short_position_calculation(self):
        """Test short position calculation"""
        base_date = datetime.datetime(2025, 1, 1, 10, 0, 0)

        # Create operations: sell 100 shares at 12.00, buy 100 shares at 10.00 (short position)
        operations = [
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_SELL,
                "FIGI001", 100, 12.0, 1200.0, base_date
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BUY,
                "FIGI001", 100, 10.0, -1000.0, base_date +
                datetime.timedelta(hours=1)
            ),
            self.create_mock_operation(
                OperationType.OPERATION_TYPE_BROKER_FEE,
                "FIGI001", 0, 0.0, -20.0, base_date +
                datetime.timedelta(minutes=1)
            ),
        ]

        trades, total_profit, processed_operations = self.calculator.process_operations(
            operations)

        # Should have 1 trade
        self.assertEqual(len(trades), 1)

        trade = trades[0]
        self.assertEqual(trade.figi, "FIGI001")
        self.assertEqual(trade.quantity, 100)
        # Entry price is sell price for short
        self.assertEqual(trade.entry_price, 12.0)
        # Exit price is buy price for short
        self.assertEqual(trade.exit_price, 10.0)
        self.assertEqual(trade.direction, "SHORT")

        # Gross profit should be (12.0 - 10.0) * 100 = 200.0 (profit from short)
        self.assertEqual(trade.gross_profit, 200.0)

        # Net profit should be 200.0 - 20.0 = 180.0
        self.assertEqual(trade.net_profit, 180.0)


class TestTradesIntegration(unittest.TestCase):
    """Integration tests with real-like scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.calculator = ProfitCalculator()

    def test_realistic_trading_scenario(self):
        """Test realistic trading scenario with multiple instruments and operations"""
        base_date = datetime.datetime(2025, 1, 1, 10, 0, 0)

        # Simulate a day of trading with multiple instruments
        operations = [
            # Morning: Buy SBER
            Mock(operation_type=OperationType.OPERATION_TYPE_BUY, figi="SBER", quantity=100,
                 price=Quotation(units=250, nano=0), payment=Quotation(units=-25000, nano=0),
                 date=base_date, id="buy_sber_1", instrument_uid="SBER"),

            # Broker fee for SBER buy
            Mock(operation_type=OperationType.OPERATION_TYPE_BROKER_FEE, figi="SBER", quantity=0,
                 price=Quotation(units=0, nano=0), payment=Quotation(units=-25, nano=0),
                 date=base_date + datetime.timedelta(minutes=1), id="fee_sber_1", instrument_uid="SBER"),

            # Afternoon: Sell SBER
            Mock(operation_type=OperationType.OPERATION_TYPE_SELL, figi="SBER", quantity=100,
                 price=Quotation(units=255, nano=0), payment=Quotation(units=25500, nano=0),
                 date=base_date + datetime.timedelta(hours=4), id="sell_sber_1", instrument_uid="SBER"),

            # Broker fee for SBER sell
            Mock(operation_type=OperationType.OPERATION_TYPE_BROKER_FEE, figi="SBER", quantity=0,
                 price=Quotation(units=0, nano=0), payment=Quotation(units=-25, nano=0),
                 date=base_date + datetime.timedelta(hours=4, minutes=1), id="fee_sber_2", instrument_uid="SBER"),

            # Variation margin accrual
            Mock(operation_type=OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN, figi="", quantity=0,
                 price=Quotation(units=0, nano=0), payment=Quotation(units=100, nano=0),
                 date=base_date + datetime.timedelta(hours=6), id="varmargin_1", instrument_uid=""),
        ]

        trades, total_profit, processed_operations = self.calculator.process_operations(
            operations)

        # Should have 1 trade
        self.assertEqual(len(trades), 1)

        trade = trades[0]
        self.assertEqual(trade.figi, "SBER")
        self.assertEqual(trade.quantity, 100)
        self.assertEqual(trade.entry_price, 250.0)
        self.assertEqual(trade.exit_price, 255.0)
        self.assertEqual(trade.direction, "LONG")

        # Gross profit: (255 - 250) * 100 = 500
        self.assertEqual(trade.gross_profit, 500.0)

        # Fees: 25 + 25 = 50
        self.assertEqual(trade.fees, 50.0)

        # Net profit: 500 - 50 + 100 (variation margin) = 550
        self.assertEqual(trade.net_profit, 550.0)

        # Total profit should equal net profit
        self.assertEqual(total_profit, 550.0)


if __name__ == '__main__':
    unittest.main()
