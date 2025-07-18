import datetime
import pytest
from dataclasses import dataclass
from typing import List

from app.utils.profit_calculator import ProfitCalculator, PeriodProfit
from tinkoff.invest.grpc.operations_pb2 import OperationType
from tinkoff.invest import Quotation


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


def create_mock_operations_march_april() -> List[MockOperation]:
    """Create mock operations for March-April 2025 based on the spreadsheet data"""
    operations = []

    # March operations (based on the provided spreadsheet data)
    # Week 1: March 31 - April 4 (Loss: -72.09)
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
        figi="BBG004730N88", quantity=0, price=0, payment=-0.05
    ))

    # More March operations
    operations.append(MockOperation(
        id="4", operation_type=OperationType.OPERATION_TYPE_BUY,
        date=datetime.datetime(2025, 4, 1, 9, 30),
        figi="BBG004730N88", quantity=2, price=4.26, payment=-8.52
    ))

    operations.append(MockOperation(
        id="5", operation_type=OperationType.OPERATION_TYPE_SELL,
        date=datetime.datetime(2025, 4, 1, 14, 30),
        figi="BBG004730N88", quantity=2, price=4.22, payment=8.44
    ))

    operations.append(MockOperation(
        id="6", operation_type=OperationType.OPERATION_TYPE_BROKER_FEE,
        date=datetime.datetime(2025, 4, 1, 14, 31),
        figi="BBG004730N88", quantity=0, price=0, payment=-0.06
    ))

    # April operations
    operations.append(MockOperation(
        id="7", operation_type=OperationType.OPERATION_TYPE_BUY,
        date=datetime.datetime(2025, 4, 7, 10, 15),
        figi="BBG004730N88", quantity=3, price=4.30, payment=-12.90
    ))

    operations.append(MockOperation(
        id="8", operation_type=OperationType.OPERATION_TYPE_SELL,
        date=datetime.datetime(2025, 4, 7, 16, 15),
        figi="BBG004730N88", quantity=3, price=4.35, payment=13.05
    ))

    operations.append(MockOperation(
        id="9", operation_type=OperationType.OPERATION_TYPE_BROKER_FEE,
        date=datetime.datetime(2025, 4, 7, 16, 16),
        figi="BBG004730N88", quantity=0, price=0, payment=-0.08
    ))

    # Week ending April 25 (Profit: 4841.46 based on spreadsheet)
    operations.append(MockOperation(
        id="10", operation_type=OperationType.OPERATION_TYPE_BUY,
        date=datetime.datetime(2025, 4, 21, 11, 0),
        figi="BBG004730N88", quantity=10, price=4.20, payment=-42.00
    ))

    operations.append(MockOperation(
        id="11", operation_type=OperationType.OPERATION_TYPE_SELL,
        date=datetime.datetime(2025, 4, 25, 14, 0),
        figi="BBG004730N88", quantity=10, price=4.72, payment=47.20
    ))

    operations.append(MockOperation(
        id="12", operation_type=OperationType.OPERATION_TYPE_BROKER_FEE,
        date=datetime.datetime(2025, 4, 25, 14, 1),
        figi="BBG004730N88", quantity=0, price=0, payment=-0.15
    ))

    # Additional operations to test different scenarios
    operations.append(MockOperation(
        id="13", operation_type=OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
        date=datetime.datetime(2025, 4, 28, 18, 0),
        figi="BBG004730N88", quantity=0, price=0, payment=-1.50
    ))

    operations.append(MockOperation(
        id="14", operation_type=OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN,
        date=datetime.datetime(2025, 4, 29, 18, 0),
        figi="BBG004730N88", quantity=0, price=0, payment=1.20
    ))

    return operations


class TestProfitCalculator:
    """Test suite for ProfitCalculator"""

    def setup_method(self):
        """Setup method run before each test"""
        self.calculator = ProfitCalculator()

    def test_basic_long_trade(self):
        """Test basic long trade calculation"""
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

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        assert len(trades) == 1
        trade = trades[0]
        assert trade.direction == "LONG"
        assert trade.quantity == 100
        assert trade.entry_price == 10.0
        assert trade.exit_price == 12.0
        assert trade.gross_profit == 200.0  # (12 - 10) * 100
        assert trade.fees == 5.0
        assert trade.net_profit == 195.0  # 200 - 5
        assert total_profit == 195.0

    def test_basic_short_trade(self):
        """Test basic short trade calculation"""
        operations = [
            MockOperation("1", OperationType.OPERATION_TYPE_SELL,
                          datetime.datetime(2025, 3, 1, 10, 0),
                          "TEST_FIGI", 100, 12.0, 1200.0),
            MockOperation("2", OperationType.OPERATION_TYPE_BUY,
                          datetime.datetime(2025, 3, 1, 15, 0),
                          "TEST_FIGI", 100, 10.0, -1000.0),
            MockOperation("3", OperationType.OPERATION_TYPE_BROKER_FEE,
                          datetime.datetime(2025, 3, 1, 15, 1),
                          "TEST_FIGI", 0, 0, -5.0)
        ]

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        assert len(trades) == 1
        trade = trades[0]
        assert trade.direction == "SHORT"
        assert trade.quantity == 100
        assert trade.entry_price == 12.0  # Short entry price
        assert trade.exit_price == 10.0   # Short exit price
        assert trade.gross_profit == 200.0  # (12 - 10) * 100 for short
        assert trade.fees == 5.0
        assert trade.net_profit == 195.0
        assert total_profit == 195.0

    def test_multiple_trades_same_instrument(self):
        """Test multiple trades on the same instrument"""
        operations = [
            # First trade
            MockOperation("1", OperationType.OPERATION_TYPE_BUY,
                          datetime.datetime(2025, 3, 1, 10, 0),
                          "TEST_FIGI", 100, 10.0, -1000.0),
            MockOperation("2", OperationType.OPERATION_TYPE_SELL,
                          datetime.datetime(2025, 3, 1, 15, 0),
                          "TEST_FIGI", 100, 11.0, 1100.0),
            MockOperation("3", OperationType.OPERATION_TYPE_BROKER_FEE,
                          datetime.datetime(2025, 3, 1, 15, 1),
                          "TEST_FIGI", 0, 0, -2.0),
            # Second trade
            MockOperation("4", OperationType.OPERATION_TYPE_BUY,
                          datetime.datetime(2025, 3, 2, 10, 0),
                          "TEST_FIGI", 50, 11.0, -550.0),
            MockOperation("5", OperationType.OPERATION_TYPE_SELL,
                          datetime.datetime(2025, 3, 2, 15, 0),
                          "TEST_FIGI", 50, 12.0, 600.0),
            MockOperation("6", OperationType.OPERATION_TYPE_BROKER_FEE,
                          datetime.datetime(2025, 3, 2, 15, 1),
                          "TEST_FIGI", 0, 0, -3.0)
        ]

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        assert len(trades) == 2

        # First trade
        assert trades[0].gross_profit == 100.0  # (11 - 10) * 100
        assert trades[0].fees == 2.0
        assert trades[0].net_profit == 98.0

        # Second trade
        assert trades[1].gross_profit == 50.0  # (12 - 11) * 50
        assert trades[1].fees == 3.0
        assert trades[1].net_profit == 47.0

        assert total_profit == 145.0  # 98 + 47

    def test_partial_position_closing(self):
        """Test partial position closing"""
        operations = [
            MockOperation("1", OperationType.OPERATION_TYPE_BUY,
                          datetime.datetime(2025, 3, 1, 10, 0),
                          "TEST_FIGI", 100, 10.0, -1000.0),
            MockOperation("2", OperationType.OPERATION_TYPE_SELL,
                          datetime.datetime(2025, 3, 1, 15, 0),
                          "TEST_FIGI", 60, 12.0, 720.0),
            MockOperation("3", OperationType.OPERATION_TYPE_SELL,
                          datetime.datetime(2025, 3, 1, 16, 0),
                          "TEST_FIGI", 40, 11.0, 440.0),
            MockOperation("4", OperationType.OPERATION_TYPE_BROKER_FEE,
                          datetime.datetime(2025, 3, 1, 16, 1),
                          "TEST_FIGI", 0, 0, -5.0)
        ]

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        assert len(trades) == 2

        # First partial close
        assert trades[0].quantity == 60
        assert trades[0].gross_profit == 120.0  # (12 - 10) * 60

        # Second partial close
        assert trades[1].quantity == 40
        assert trades[1].gross_profit == 40.0  # (11 - 10) * 40

        total_gross = sum(trade.gross_profit for trade in trades)
        assert total_gross == 160.0  # 120 + 40

    def test_march_april_data(self):
        """Test with March-April mock data"""
        operations = create_mock_operations_march_april()

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        # Verify we have the expected number of trades
        assert len(trades) > 0

        # Check that all trades have proper structure
        for trade in trades:
            assert trade.entry_price > 0
            assert trade.exit_price > 0
            assert trade.quantity > 0
            assert trade.direction in ["LONG", "SHORT"]
            assert isinstance(trade.gross_profit, (int, float))
            assert isinstance(trade.fees, (int, float))
            assert isinstance(trade.net_profit, (int, float))

        # The total profit should be the sum of all net profits
        expected_total = sum(trade.net_profit for trade in trades)
        assert abs(total_profit - expected_total) < 0.001

    def test_period_profit_calculation(self):
        """Test period profit calculation"""
        operations = create_mock_operations_march_april()

        # Test March period
        march_start = datetime.datetime(2025, 3, 1)
        march_end = datetime.datetime(2025, 3, 31, 23, 59, 59)

        period_profit = self.calculator.calculate_period_profit(
            operations, march_start, march_end, 44127.39
        )

        assert isinstance(period_profit, PeriodProfit)
        assert period_profit.start_date == march_start
        assert period_profit.end_date == march_end
        assert period_profit.starting_balance == 44127.39
        assert period_profit.trades_count >= 0

    def test_weekly_profit_analysis(self):
        """Test weekly profit analysis"""
        operations = create_mock_operations_march_april()

        weekly_periods = self.calculator.get_weekly_profit_analysis(operations)

        assert len(weekly_periods) > 0

        for period in weekly_periods:
            assert isinstance(period, PeriodProfit)
            assert period.start_date <= period.end_date
            assert isinstance(period.profit_percentage, (int, float))
            assert period.trades_count >= 0

    def test_monthly_profit_analysis(self):
        """Test monthly profit analysis"""
        operations = create_mock_operations_march_april()

        monthly_periods = self.calculator.get_monthly_profit_analysis(
            operations)

        assert len(monthly_periods) > 0

        for period in monthly_periods:
            assert isinstance(period, PeriodProfit)
            assert period.start_date.day == 1  # Should start on first day of month
            assert isinstance(period.profit_percentage, (int, float))
            assert period.trades_count >= 0

    def test_fee_assignment(self):
        """Test that fees are properly assigned to trades"""
        operations = [
            MockOperation("1", OperationType.OPERATION_TYPE_BUY,
                          datetime.datetime(2025, 3, 1, 10, 0),
                          "TEST_FIGI", 100, 10.0, -1000.0),
            MockOperation("2", OperationType.OPERATION_TYPE_SELL,
                          datetime.datetime(2025, 3, 1, 15, 0),
                          "TEST_FIGI", 100, 12.0, 1200.0),
            MockOperation("3", OperationType.OPERATION_TYPE_BROKER_FEE,
                          datetime.datetime(2025, 3, 1, 15, 1),
                          "TEST_FIGI", 0, 0, -5.0),
            MockOperation("4", OperationType.OPERATION_TYPE_BROKER_FEE,
                          datetime.datetime(2025, 3, 1, 15, 2),
                          "TEST_FIGI", 0, 0, -3.0)
        ]

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        assert len(trades) == 1
        # Should have at least some fees assigned
        assert trades[0].fees > 0
        assert trades[0].net_profit == trades[0].gross_profit - trades[0].fees

    def test_empty_operations(self):
        """Test with empty operations list"""
        trades, total_profit, _ = self.calculator.process_operations([])

        assert len(trades) == 0
        assert total_profit == 0

    def test_only_buy_operations(self):
        """Test with only buy operations (no closed positions)"""
        operations = [
            MockOperation("1", OperationType.OPERATION_TYPE_BUY,
                          datetime.datetime(2025, 3, 1, 10, 0),
                          "TEST_FIGI", 100, 10.0, -1000.0),
            MockOperation("2", OperationType.OPERATION_TYPE_BUY,
                          datetime.datetime(2025, 3, 1, 15, 0),
                          "TEST_FIGI", 50, 11.0, -550.0)
        ]

        trades, total_profit, _ = self.calculator.process_operations(
            operations)

        assert len(trades) == 0  # No closed positions
        assert total_profit == 0

    def test_timezone_correction(self):
        """Test timezone correction"""
        test_date = datetime.datetime(2025, 3, 1, 12, 0, 0)
        corrected_date = self.calculator.correct_timezone(test_date)

        expected_date = test_date + datetime.timedelta(hours=3)
        assert corrected_date == expected_date


def test_integration_with_main_calc_trades():
    """Test integration with the main calc_trades function"""
    from app.main import calc_trades

    operations = create_mock_operations_march_april()

    # Test the updated calc_trades function
    trades, total_profit, processed_operations = calc_trades(operations)

    # Verify it returns the expected format
    assert isinstance(trades, list)
    assert isinstance(total_profit, (int, float))
    assert isinstance(processed_operations, list)

    # Check that trades have the expected structure for the UI
    for trade in trades:
        assert "num" in trade
        assert "timeStart" in trade
        assert "timeEnd" in trade
        assert "type" in trade
        assert "figi" in trade
        assert "quantity" in trade
        assert "pt1" in trade  # entry price
        assert "pt2" in trade  # exit price
        assert "result" in trade  # net profit
        assert "gross_profit" in trade
        assert "fees" in trade


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
