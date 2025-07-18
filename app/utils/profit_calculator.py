import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import logging

from tinkoff.invest.grpc.operations_pb2 import OperationType
from app.utils.quotation import quotation_to_float


logger = logging.getLogger(__name__)


@dataclass
class TradingSession:
    """Represents a trading session with multiple operations"""
    session_id: str
    figi: str
    instrument_name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    operations: List[Dict[str, Any]]  # All operations in this session
    total_quantity_sold: int
    total_quantity_bought: int
    total_sell_amount: float  # Total received from sells
    total_buy_amount: float   # Total paid for buys
    gross_profit: float
    fees: float
    variation_margin: float
    net_profit: float
    direction: str  # 'SHORT' for sell-first sessions


@dataclass
class Trade:
    """Represents a completed trade (buy-sell pair) - kept for backward compatibility"""
    trade_id: str
    figi: str
    instrument_name: str
    entry_time: datetime.datetime
    exit_time: datetime.datetime
    entry_price: float
    exit_price: float
    quantity: int
    direction: str  # 'LONG' or 'SHORT'
    gross_profit: float
    fees: float
    net_profit: float
    entry_operation_id: str
    exit_operation_id: str
    # New fields for session-based calculation
    session_data: Optional[TradingSession] = None
    variation_margin: float = 0.0


@dataclass
class PeriodProfit:
    """Represents profit for a specific time period"""
    start_date: datetime.datetime
    end_date: datetime.datetime
    starting_balance: float
    ending_balance: float
    total_profit: float
    total_fees: float
    net_profit: float
    profit_percentage: float
    trades_count: int
    winning_trades: int
    losing_trades: int


class ProfitCalculator:
    """Advanced profit calculation system for trading operations"""

    def __init__(self, timezone_offset: int = 3):
        self.timezone_offset = timezone_offset
        self.reset()

    def reset(self):
        """Reset the calculator state"""
        self.positions = defaultdict(list)  # figi -> list of operations
        self.completed_trades = []
        self.fees_buffer = []
        self.margin_operations = []
        self.trading_sessions = []  # New: completed trading sessions

    def correct_timezone(self, date: datetime.datetime) -> datetime.datetime:
        """Apply timezone correction"""
        return date + datetime.timedelta(hours=self.timezone_offset)

    def process_operations(self, operations: List[Any]) -> Tuple[List[Trade], float, List[Any]]:
        """
        Process a list of operations and calculate trades and profit using session-based logic

        Args:
            operations: List of trading operations from Tinkoff API

        Returns:
            Tuple of (completed_trades, total_profit, all_processed_operations)
        """
        return self.process_operations_with_starting_positions(operations, {})

    def process_operations_with_starting_positions(self, operations: List[Any], starting_positions: Dict[str, int] = None) -> Tuple[List[Trade], float, List[Any]]:
        """
        Process a list of operations and calculate trades and profit using session-based logic
        with support for known starting positions

        Args:
            operations: List of trading operations from Tinkoff API
            starting_positions: Dict mapping FIGI to starting position (positive = long, negative = short)

        Returns:
            Tuple of (completed_trades, total_profit, all_processed_operations)
        """
        if starting_positions is None:
            starting_positions = {}

        self.reset()

        # Sort operations by date (oldest first)
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Separate trading operations from fees and margin operations
        trading_operations = []
        for operation in sorted_operations:
            if operation.operation_type == OperationType.OPERATION_TYPE_BROKER_FEE:
                self._process_fee_operation(operation)
            elif operation.operation_type in [
                OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN
            ]:
                self._process_margin_operation(operation)
            elif operation.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL
            ]:
                trading_operations.append(operation)

        # Group trading operations into sessions with starting positions
        self._group_operations_into_sessions(
            trading_operations, starting_positions)

        # Convert sessions to trades (for backward compatibility)
        self._convert_sessions_to_trades()

        # Calculate total profit
        total_profit = sum(trade.net_profit for trade in self.completed_trades)

        return self.completed_trades, total_profit, sorted_operations

    def analyze_starting_positions(self, operations: List[Any]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze operations to provide insights about possible starting positions.

        This method helps determine what the starting position might have been
        for each FIGI by analyzing the first operation and potential position changes.

        Args:
            operations: List of trading operations from Tinkoff API

        Returns:
            Dict mapping FIGI to analysis results containing:
            - first_operation: Details about the first operation
            - possible_scenarios: List of possible starting positions and their implications
        """
        if not operations:
            return {}

        # Sort operations by date (oldest first)
        sorted_operations = sorted(operations, key=lambda x: x.date)

        # Group by FIGI
        figi_operations = defaultdict(list)
        for op in sorted_operations:
            if op.operation_type in [OperationType.OPERATION_TYPE_BUY, OperationType.OPERATION_TYPE_SELL]:
                figi_operations[op.figi].append(op)

        analysis = {}

        for figi, ops in figi_operations.items():
            first_op = ops[0]

            # Calculate what happens with different starting positions
            scenarios = []

            # Scenario 1: Starting from 0 (traditional assumption)
            scenarios.append({
                'starting_position': 0,
                'description': 'Начинаем с нулевой позиции (традиционное предположение)',
                'first_operation_result': first_op.quantity if first_op.operation_type == OperationType.OPERATION_TYPE_BUY else -first_op.quantity,
                'crosses_zero': False
            })

            # Scenario 2: Starting position that would make first operation cross zero
            if first_op.operation_type == OperationType.OPERATION_TYPE_BUY:
                # If first operation is BUY, maybe we had a short position
                scenarios.append({
                    'starting_position': -first_op.quantity,
                    'description': f'Начинаем с короткой позиции -{first_op.quantity} лотов (первая операция закрывает позицию)',
                    'first_operation_result': 0,
                    'crosses_zero': True
                })

                # Or maybe we had an even larger short position
                scenarios.append({
                    'starting_position': -(first_op.quantity * 2),
                    'description': f'Начинаем с короткой позиции -{first_op.quantity * 2} лотов (первая операция частично закрывает)',
                    'first_operation_result': -first_op.quantity,
                    'crosses_zero': False
                })
            else:
                # If first operation is SELL, maybe we had a long position
                scenarios.append({
                    'starting_position': first_op.quantity,
                    'description': f'Начинаем с длинной позиции +{first_op.quantity} лотов (первая операция закрывает позицию)',
                    'first_operation_result': 0,
                    'crosses_zero': True
                })

                # Or maybe we had an even larger long position
                scenarios.append({
                    'starting_position': first_op.quantity * 2,
                    'description': f'Начинаем с длинной позиции +{first_op.quantity * 2} лотов (первая операция частично закрывает)',
                    'first_operation_result': first_op.quantity,
                    'crosses_zero': False
                })

            analysis[figi] = {
                'first_operation': {
                    'type': 'Покупка' if first_op.operation_type == OperationType.OPERATION_TYPE_BUY else 'Продажа',
                    'quantity': first_op.quantity,
                    'price': quotation_to_float(first_op.price),
                    'date': first_op.date,
                    'amount': quotation_to_float(first_op.payment)
                },
                'possible_scenarios': scenarios,
                'total_operations': len(ops)
            }

        return analysis

    def _assign_fees_to_trades(self):
        """Assign fees and variation margin to trades after all operations are processed"""
        if not self.completed_trades:
            return

        # Assign fees and variation margin to each trade individually
        for trade in self.completed_trades:
            # Find fees that should be assigned to this trade
            trade_fees = self._get_fees_for_trade_period(trade)

            # Find variation margin that occurred during this trade
            trade_margin = self._get_variation_margin_for_trade(trade)

            # Assign to trade
            trade.fees = trade_fees
            trade.net_profit = trade.gross_profit - trade.fees + trade_margin

    def _get_fees_for_trade_period(self, trade: Trade) -> float:
        """Get fees that should be assigned to a specific trade based on timing"""
        total_fees = 0.0

        # Convert trade times to original timezone for comparison
        entry_time_original = trade.entry_time - \
            datetime.timedelta(hours=self.timezone_offset)
        exit_time_original = trade.exit_time - \
            datetime.timedelta(hours=self.timezone_offset)

        # Look for unassigned fees that are close in time to this trade
        for fee in self.fees_buffer:
            if not fee['assigned']:
                # Check if fee is within reasonable time window of the trade
                if (entry_time_original <= fee['date'] <= exit_time_original or
                    # 5 minutes
                    abs((fee['date'] - entry_time_original).total_seconds()) <= 300 or
                        abs((fee['date'] - exit_time_original).total_seconds()) <= 300):     # 5 minutes
                    total_fees += fee['amount']
                    fee['assigned'] = True

        return total_fees

    def _get_variation_margin_for_trade(self, trade: Trade) -> float:
        """Get variation margin that occurred during a specific trade"""
        total_margin = 0.0

        # Convert trade times to original timezone for comparison
        entry_time_original = trade.entry_time - \
            datetime.timedelta(hours=self.timezone_offset)
        exit_time_original = trade.exit_time - \
            datetime.timedelta(hours=self.timezone_offset)

        # Look for unassigned margin operations that occurred during this trade
        for margin in self.margin_operations:
            if not margin['assigned']:
                # Check if margin operation occurred during the trade period
                if entry_time_original <= margin['date'] <= exit_time_original:
                    total_margin += margin['amount']
                    margin['assigned'] = True

        return total_margin

    def _process_single_operation(self, operation: Any):
        """Process a single operation"""
        if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
            self._process_buy_operation(operation)
        elif operation.operation_type == OperationType.OPERATION_TYPE_SELL:
            self._process_sell_operation(operation)
        elif operation.operation_type == OperationType.OPERATION_TYPE_BROKER_FEE:
            self._process_fee_operation(operation)
        elif operation.operation_type in [
            OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
            OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN
        ]:
            self._process_margin_operation(operation)

    def _process_buy_operation(self, operation: Any):
        """Process a buy operation"""
        # Check if we have any open short positions that this buy can close
        buy_quantity = operation.quantity

        while buy_quantity > 0:
            # Find the oldest unprocessed short position
            short_position = self._find_oldest_short(
                operation.figi, buy_quantity)

            if not short_position:
                # No short position to close, this is a regular buy
                break

            # Calculate the quantity to close
            quantity_to_close = min(buy_quantity, short_position['quantity'])

            # Create a completed trade for the short position
            trade = self._create_trade(
                short_position, operation, quantity_to_close, 'SHORT'
            )

            self.completed_trades.append(trade)

            # Update quantities
            buy_quantity -= quantity_to_close
            short_position['quantity'] -= quantity_to_close

            # Mark as processed if fully consumed
            if short_position['quantity'] == 0:
                short_position['processed'] = True

        # If there's remaining buy quantity, store it as a position
        if buy_quantity > 0:
            self.positions[operation.figi].append({
                'type': 'BUY',
                'operation': operation,
                'quantity': buy_quantity,
                'price': quotation_to_float(operation.price),
                'payment': quotation_to_float(operation.payment),
                'date': operation.date,
                'processed': False
            })

    def _process_sell_operation(self, operation: Any):
        """Process a sell operation"""
        # Check if this is a short position first
        if not self.positions[operation.figi]:
            # This is a short sell - no prior buy positions
            self._handle_short_position(operation)
            return

        # Try to match with existing buy operations (FIFO)
        sell_quantity = operation.quantity
        sell_price = quotation_to_float(operation.price)

        while sell_quantity > 0:
            # Find the oldest unprocessed buy operation
            buy_operation = self._find_oldest_buy(
                operation.figi, sell_quantity)

            if not buy_operation:
                # No matching buy operation found, this might be a short position
                self._handle_short_position(operation)
                break

            # Calculate the quantity to close
            quantity_to_close = min(sell_quantity, buy_operation['quantity'])

            # Create a completed trade
            trade = self._create_trade(
                buy_operation, operation, quantity_to_close, 'LONG'
            )

            self.completed_trades.append(trade)

            # Update quantities
            sell_quantity -= quantity_to_close
            buy_operation['quantity'] -= quantity_to_close

            # Mark as processed if fully consumed
            if buy_operation['quantity'] == 0:
                buy_operation['processed'] = True

    def _find_oldest_buy(self, figi: str, needed_quantity: int) -> Optional[Dict]:
        """Find the oldest unprocessed buy operation for a given figi"""
        for position in self.positions[figi]:
            if (position['type'] == 'BUY' and
                not position['processed'] and
                    position['quantity'] > 0):
                return position
        return None

    def _find_oldest_short(self, figi: str, needed_quantity: int) -> Optional[Dict]:
        """Find the oldest unprocessed short position for a given figi"""
        for position in self.positions[figi]:
            if (position['type'] == 'SELL' and
                not position['processed'] and
                    position['quantity'] > 0):
                return position
        return None

    def _handle_short_position(self, sell_operation: Any):
        """Handle short position (sell without prior buy)"""
        # Check if we have any buy operations for this figi that can close the short
        buy_operations = [p for p in self.positions[sell_operation.figi]
                          if p['type'] == 'BUY' and not p['processed']]

        if buy_operations:
            # We have buy operations that can close this short position
            return

        # This is a pure short position - store it for later matching
        self.positions[sell_operation.figi].append({
            'type': 'SELL',
            'operation': sell_operation,
            'quantity': sell_operation.quantity,
            'price': quotation_to_float(sell_operation.price),
            'payment': quotation_to_float(sell_operation.payment),
            'date': sell_operation.date,
            'processed': False
        })

    def _create_trade(self, buy_op: Dict, sell_op: Any, quantity: int, direction: str) -> Trade:
        """Create a Trade object from buy and sell operations"""
        if direction == 'LONG':
            # Standard long position: buy first, then sell
            buy_price = buy_op['price']
            sell_price = quotation_to_float(sell_op.price)
            entry_time = buy_op['date']
            exit_time = sell_op.date
            entry_operation_id = buy_op['operation'].id
            exit_operation_id = sell_op.id
        else:  # SHORT
            # Short position: sell first, then buy to close
            # Buy price is from the closing operation
            buy_price = quotation_to_float(sell_op.price)
            # Sell price is from the opening operation
            sell_price = buy_op['price']
            # Entry time is when we opened the short
            entry_time = buy_op['date']
            exit_time = sell_op.date     # Exit time is when we closed the short
            entry_operation_id = buy_op['operation'].id
            exit_operation_id = sell_op.id

        # Calculate gross profit
        if direction == 'LONG':
            gross_profit = (sell_price - buy_price) * quantity
        else:  # SHORT
            gross_profit = (sell_price - buy_price) * quantity

        # Fees will be assigned later, set to 0 for now
        fees = 0.0

        # Calculate net profit (will be updated after fee assignment)
        net_profit = gross_profit - fees

        return Trade(
            trade_id=f"{entry_operation_id}_{exit_operation_id}",
            figi=sell_op.figi if direction == 'LONG' else buy_op['operation'].figi,
            instrument_name=getattr(
                sell_op, 'instrument_uid', sell_op.figi) if direction == 'LONG' else buy_op['operation'].figi,
            entry_time=self.correct_timezone(entry_time),
            exit_time=self.correct_timezone(exit_time),
            entry_price=sell_price if direction == 'SHORT' else buy_price,
            exit_price=buy_price if direction == 'SHORT' else sell_price,
            quantity=quantity,
            direction=direction,
            gross_profit=gross_profit,
            fees=fees,
            net_profit=net_profit,
            entry_operation_id=entry_operation_id,
            exit_operation_id=exit_operation_id
        )

    def _process_fee_operation(self, operation: Any):
        """Process fee operation"""
        self.fees_buffer.append({
            'operation': operation,
            'amount': abs(quotation_to_float(operation.payment)),
            'date': operation.date,
            'assigned': False
        })

    def _process_margin_operation(self, operation: Any):
        """Process margin operation (variation margin)"""
        self.margin_operations.append({
            'operation': operation,
            'amount': quotation_to_float(operation.payment),
            'date': operation.date,
            'assigned': False
        })

    def _get_fees_for_trade(self, buy_id: str, sell_id: str) -> float:
        """Get fees associated with a specific trade"""
        total_fees = 0.0

        # Look for fees that are close in time to the trade operations
        for fee in self.fees_buffer:
            if not fee['assigned']:
                # Simple heuristic: assign fees to nearby trades
                # In a more sophisticated system, you might match fees by timestamp
                total_fees += fee['amount']
                fee['assigned'] = True
                # Only assign one fee per trade for now
                break

        return total_fees

    def calculate_period_profit_real(self, operations: List[Any],
                                     start_date: datetime.datetime,
                                     end_date: datetime.datetime) -> float:
        """
        Calculate profit for a specific period using real data logic
        This matches the spreadsheet calculation method
        """
        # Ensure dates are timezone-aware if operations have timezone info
        if operations and hasattr(operations[0], 'date') and operations[0].date.tzinfo is not None:
            # Operations have timezone info, ensure our dates do too
            if start_date.tzinfo is None:
                # Assume Moscow timezone (UTC+3)
                import pytz
                moscow_tz = pytz.timezone('Europe/Moscow')
                start_date = moscow_tz.localize(start_date)
            if end_date.tzinfo is None:
                import pytz
                moscow_tz = pytz.timezone('Europe/Moscow')
                end_date = moscow_tz.localize(end_date)

        # Filter operations for the period
        period_operations = [
            op for op in operations
            if start_date <= op.date <= end_date
        ]

        if not period_operations:
            return 0.0

        # Calculate period profit by summing all payments
        total_payment = 0.0

        for operation in period_operations:
            if operation.operation_type in [
                OperationType.OPERATION_TYPE_BUY,
                OperationType.OPERATION_TYPE_SELL,
                OperationType.OPERATION_TYPE_BROKER_FEE,
                OperationType.OPERATION_TYPE_WRITING_OFF_VARMARGIN,
                OperationType.OPERATION_TYPE_ACCRUING_VARMARGIN
            ]:
                payment = quotation_to_float(operation.payment)
                total_payment += payment

        return total_payment

    def calculate_period_profit(self, operations: List[Any],
                                start_date: datetime.datetime,
                                end_date: datetime.datetime,
                                starting_balance: float = 0.0) -> PeriodProfit:
        """
        Calculate profit for a specific time period

        Args:
            operations: List of all operations
            start_date: Start of the period
            end_date: End of the period
            starting_balance: Starting balance for the period

        Returns:
            PeriodProfit object with detailed period analysis
        """
        # Filter operations for the period
        period_operations = [
            op for op in operations
            if start_date <= op.date <= end_date
        ]

        # Process operations for the period
        trades, total_profit, _ = self.process_operations(period_operations)

        # Calculate statistics
        total_fees = sum(trade.fees for trade in trades)
        net_profit = total_profit
        ending_balance = starting_balance + net_profit

        profit_percentage = (net_profit / starting_balance *
                             100) if starting_balance > 0 else 0

        winning_trades = len([t for t in trades if t.net_profit > 0])
        losing_trades = len([t for t in trades if t.net_profit < 0])

        return PeriodProfit(
            start_date=start_date,
            end_date=end_date,
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            total_profit=total_profit,
            total_fees=total_fees,
            net_profit=net_profit,
            profit_percentage=profit_percentage,
            trades_count=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )

    def get_weekly_profit_analysis(self, operations: List[Any]) -> List[PeriodProfit]:
        """Get weekly profit analysis"""
        if not operations:
            return []

        # Sort operations by date
        sorted_ops = sorted(operations, key=lambda x: x.date)

        # Find the date range
        start_date = sorted_ops[0].date
        end_date = sorted_ops[-1].date

        # Generate weekly periods
        periods = []
        current_date = start_date.replace(
            hour=0, minute=0, second=0, microsecond=0)

        # Find the Monday of the first week
        days_since_monday = current_date.weekday()
        week_start = current_date - datetime.timedelta(days=days_since_monday)

        starting_balance = 0.0

        while week_start <= end_date:
            week_end = week_start + \
                datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)

            if week_end > end_date:
                week_end = end_date

            period_profit = self.calculate_period_profit(
                operations, week_start, week_end, starting_balance
            )

            periods.append(period_profit)
            starting_balance = period_profit.ending_balance
            week_start += datetime.timedelta(days=7)

        return periods

    def get_monthly_profit_analysis(self, operations: List[Any]) -> List[PeriodProfit]:
        """Get monthly profit analysis"""
        if not operations:
            return []

        # Sort operations by date
        sorted_ops = sorted(operations, key=lambda x: x.date)

        # Find the date range
        start_date = sorted_ops[0].date
        end_date = sorted_ops[-1].date

        # Generate monthly periods
        periods = []
        current_year = start_date.year
        current_month = start_date.month

        starting_balance = 0.0

        while True:
            month_start = datetime.datetime(current_year, current_month, 1)

            # Calculate last day of month
            if current_month == 12:
                next_month = datetime.datetime(current_year + 1, 1, 1)
            else:
                next_month = datetime.datetime(
                    current_year, current_month + 1, 1)

            month_end = next_month - datetime.timedelta(seconds=1)

            if month_start > end_date:
                break

            if month_end > end_date:
                month_end = end_date

            period_profit = self.calculate_period_profit(
                operations, month_start, month_end, starting_balance
            )

            periods.append(period_profit)
            starting_balance = period_profit.ending_balance

            # Move to next month
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1

        return periods

    def _group_operations_into_sessions(self, trading_operations: List[Any], starting_positions: Dict[str, int] = None):
        """
        Group trading operations into trading sessions.

        Session logic:
        - Session starts with a SELL operation (entry into short position)
        - Session can have multiple SELL operations (pyramiding)
        - Session ends with BUY operation(s) that close the position
        - Sessions are created per FIGI

        Args:
            trading_operations: List of trading operations
            starting_positions: Dict mapping FIGI to starting position (default: empty positions)
        """
        if starting_positions is None:
            starting_positions = {}

        # Group operations by FIGI
        figi_operations = defaultdict(list)
        for op in trading_operations:
            figi_operations[op.figi].append(op)

        # Process each FIGI separately
        for figi, operations in figi_operations.items():
            starting_pos = starting_positions.get(figi, 0)
            self._create_sessions_for_figi(figi, operations, starting_pos)

    def _create_sessions_for_figi(self, figi: str, operations: List[Any], starting_position: int = 0):
        """Create trading sessions for a specific FIGI using universal position tracking"""
        operations = sorted(operations, key=lambda x: x.date)

        current_position = starting_position  # Start with actual position instead of 0
        current_session = None

        for operation in operations:
            operation_qty = operation.quantity

            # Determine operation direction
            if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
                # Buying increases position
                new_position = current_position + operation_qty
                current_session = self._process_position_change(figi, operation, current_position, new_position,
                                                                operation_qty, True, current_session)
                current_position = new_position

            elif operation.operation_type == OperationType.OPERATION_TYPE_SELL:
                # Selling decreases position
                new_position = current_position - operation_qty
                current_session = self._process_position_change(figi, operation, current_position, new_position,
                                                                operation_qty, False, current_session)
                current_position = new_position

        # If there's an active session, finalize it only if it's a completed round-trip
        if current_session is not None:
            # Only finalize if we have both buys and sells (completed round trip)
            if current_session['total_quantity_bought'] > 0 and current_session['total_quantity_sold'] > 0:
                self._finalize_session(current_session)
                self.trading_sessions.append(current_session)
            # Note: Open positions are not included in completed sessions

    def _process_position_change(self, figi: str, operation: Any, old_position: int,
                                 new_position: int, operation_qty: int, is_buy: bool,
                                 current_session: Dict[str, Any]):
        """Process position change and create/update sessions accordingly"""

        # Check if position crosses zero (session boundary)
        if (old_position > 0 and new_position < 0) or (old_position < 0 and new_position > 0):
            # Position crosses zero - need to split the operation

            # Calculate quantity that closes current position
            closing_qty = abs(old_position)
            remaining_qty = operation_qty - closing_qty

            # Close current session with closing quantity
            if current_session is not None:
                if is_buy:
                    self._add_buy_to_session(
                        current_session, operation, closing_qty)
                else:
                    self._add_sell_to_session(
                        current_session, operation, closing_qty)

                self._finalize_session(current_session)
                self.trading_sessions.append(current_session)

            # Start new session with remaining quantity
            if remaining_qty > 0:
                new_session = self._start_new_session(figi, operation)
                if is_buy:
                    self._add_buy_to_session(
                        new_session, operation, remaining_qty)
                else:
                    self._add_sell_to_session(
                        new_session, operation, remaining_qty)
                current_session = new_session

        elif old_position == 0:
            # Starting from zero position - start new session
            current_session = self._start_new_session(figi, operation)
            if is_buy:
                self._add_buy_to_session(
                    current_session, operation, operation_qty)
            else:
                self._add_sell_to_session(
                    current_session, operation, operation_qty)

        else:
            # Continuing in same direction - add to current session
            if current_session is None:
                current_session = self._start_new_session(figi, operation)

            if is_buy:
                self._add_buy_to_session(
                    current_session, operation, operation_qty)
            else:
                self._add_sell_to_session(
                    current_session, operation, operation_qty)

        return current_session

    def _add_buy_to_session(self, session: Dict[str, Any], operation: Any, quantity: int):
        """Add buy operation to session"""
        # Calculate proportional payment based on quantity
        total_payment = abs(quotation_to_float(operation.payment))
        proportional_payment = total_payment * quantity / operation.quantity

        # Create operation record
        op_record = {
            'id': operation.id,
            'type': operation.operation_type,
            'date': operation.date,
            'quantity': quantity,
            'price': quotation_to_float(operation.price),
            'payment': -proportional_payment  # Negative for buy
        }

        session['operations'].append(op_record)
        session['total_quantity_bought'] += quantity
        session['total_buy_amount'] += proportional_payment
        session['end_time'] = operation.date

    def _add_sell_to_session(self, session: Dict[str, Any], operation: Any, quantity: int):
        """Add sell operation to session"""
        # Calculate proportional payment based on quantity
        total_payment = abs(quotation_to_float(operation.payment))
        proportional_payment = total_payment * quantity / operation.quantity

        # Create operation record
        op_record = {
            'id': operation.id,
            'type': operation.operation_type,
            'date': operation.date,
            'quantity': quantity,
            'price': quotation_to_float(operation.price),
            'payment': proportional_payment  # Positive for sell
        }

        session['operations'].append(op_record)
        session['total_quantity_sold'] += quantity
        session['total_sell_amount'] += proportional_payment
        session['end_time'] = operation.date

    def _start_new_session(self, figi: str, first_operation: Any) -> Dict[str, Any]:
        """Start a new trading session"""
        return {
            'session_id': f"{figi}_{first_operation.date.strftime('%Y%m%d_%H%M%S')}_{first_operation.id}",
            'figi': figi,
            'instrument_name': getattr(first_operation, 'instrument_uid', figi),
            'start_time': first_operation.date,
            'end_time': first_operation.date,
            'operations': [],
            'total_quantity_sold': 0,
            'total_quantity_bought': 0,
            'total_sell_amount': 0.0,
            'total_buy_amount': 0.0,
            'direction': 'UNKNOWN'  # Will be determined by first operation
        }

    def _convert_operation_to_dict(self, operation: Any) -> Dict[str, Any]:
        """Convert operation to dictionary for storage"""
        return {
            'id': operation.id,
            'type': operation.operation_type,
            'date': operation.date,
            'quantity': operation.quantity,
            'price': quotation_to_float(operation.price),
            'payment': quotation_to_float(operation.payment)
        }

    def _finalize_session(self, session: Dict[str, Any]):
        """Finalize session by calculating profit and assigning fees/margin"""
        # Determine session direction based on operations
        if session['total_quantity_sold'] > 0 and session['total_quantity_bought'] > 0:
            # Session has both sells and buys - it's a completed round trip
            if session['operations'][0]['type'] == OperationType.OPERATION_TYPE_SELL:
                session['direction'] = 'SHORT'  # Started with sell
            else:
                session['direction'] = 'LONG'   # Started with buy
        else:
            # Incomplete session - determine by what we have
            if session['total_quantity_sold'] > 0:
                session['direction'] = 'SHORT'
            else:
                session['direction'] = 'LONG'

        # Calculate gross profit
        # For completed sessions: profit = total_sell_amount - total_buy_amount
        session['gross_profit'] = session['total_sell_amount'] - \
            session['total_buy_amount']

        # Assign fees for this session
        session['fees'] = self._get_fees_for_session(session)

        # Assign variation margin for this session
        session['variation_margin'] = self._get_variation_margin_for_session(
            session)

        # Calculate net profit
        session['net_profit'] = session['gross_profit'] - \
            session['fees'] + session['variation_margin']

    def _get_fees_for_session(self, session: Dict[str, Any]) -> float:
        """Get fees that should be assigned to a specific session"""
        total_fees = 0.0

        # Convert session times to original timezone for comparison
        start_time_original = session['start_time'] - \
            datetime.timedelta(hours=self.timezone_offset)
        end_time_original = session['end_time'] - \
            datetime.timedelta(hours=self.timezone_offset)

        # Look for unassigned fees that are close in time to this session
        for fee in self.fees_buffer:
            if not fee['assigned']:
                # Check if fee is within the session time window or very close
                fee_date = fee['date']
                fee_figi = getattr(fee['operation'], 'figi', None)

                time_match = (start_time_original <= fee_date <= end_time_original or
                              # 5 minutes
                              abs((fee_date - start_time_original).total_seconds()) <= 300 or
                              abs((fee_date - end_time_original).total_seconds()) <= 300)     # 5 minutes

                # If fee has FIGI, check if it matches session FIGI, otherwise assign by time
                figi_match = (fee_figi is None or fee_figi ==
                              session['figi'] or fee_figi == '')

                if time_match and figi_match:
                    total_fees += fee['amount']
                    fee['assigned'] = True

        return total_fees

    def _get_variation_margin_for_session(self, session: Dict[str, Any]) -> float:
        """Get variation margin that occurred during a specific session"""
        total_margin = 0.0

        # Convert session times to original timezone for comparison
        start_time_original = session['start_time'] - \
            datetime.timedelta(hours=self.timezone_offset)
        end_time_original = session['end_time'] - \
            datetime.timedelta(hours=self.timezone_offset)

        # Look for unassigned margin operations that occurred during this session
        for margin in self.margin_operations:
            if not margin['assigned']:
                # Check if margin operation occurred during the session period
                margin_date = margin['date']
                margin_figi = getattr(margin['operation'], 'figi', None)

                time_match = start_time_original <= margin_date <= end_time_original

                # Variation margin typically doesn't have FIGI or has empty FIGI
                # so we assign by time only
                figi_match = (margin_figi is None or margin_figi ==
                              '' or margin_figi == session['figi'])

                if time_match and figi_match:
                    total_margin += margin['amount']
                    margin['assigned'] = True

        return total_margin

    def _convert_sessions_to_trades(self):
        """Convert trading sessions to Trade objects for backward compatibility"""
        for session in self.trading_sessions:
            # For sessions, we'll create a single Trade object representing the entire session
            trade = self._create_trade_from_session(session)
            self.completed_trades.append(trade)

    def _create_trade_from_session(self, session: Dict[str, Any]) -> Trade:
        """Create a Trade object from a trading session"""
        # Calculate average prices
        avg_sell_price = session['total_sell_amount'] / \
            session['total_quantity_sold'] if session['total_quantity_sold'] > 0 else 0
        avg_buy_price = session['total_buy_amount'] / \
            session['total_quantity_bought'] if session['total_quantity_bought'] > 0 else 0

        # For display purposes, use the total quantity (should be equal for closed sessions)
        # or total_quantity_bought, should be same
        quantity = session['total_quantity_sold']

        # Create session data
        session_data = TradingSession(
            session_id=session['session_id'],
            figi=session['figi'],
            instrument_name=session['instrument_name'],
            start_time=self.correct_timezone(session['start_time']),
            end_time=self.correct_timezone(session['end_time']),
            operations=session['operations'],
            total_quantity_sold=session['total_quantity_sold'],
            total_quantity_bought=session['total_quantity_bought'],
            total_sell_amount=session['total_sell_amount'],
            total_buy_amount=session['total_buy_amount'],
            gross_profit=session['gross_profit'],
            fees=session['fees'],
            variation_margin=session['variation_margin'],
            net_profit=session['net_profit'],
            direction=session['direction']
        )

        # Create Trade object
        trade = Trade(
            trade_id=session['session_id'],
            figi=session['figi'],
            instrument_name=session['instrument_name'],
            entry_time=self.correct_timezone(session['start_time']),
            exit_time=self.correct_timezone(session['end_time']),
            entry_price=avg_sell_price,  # For SHORT: entry is sell price
            exit_price=avg_buy_price,    # For SHORT: exit is buy price
            quantity=quantity,
            direction=session['direction'],
            gross_profit=session['gross_profit'],
            fees=session['fees'],
            net_profit=session['net_profit'],
            entry_operation_id=session['operations'][0]['id'],
            exit_operation_id=session['operations'][-1]['id'],
            session_data=session_data,
            variation_margin=session['variation_margin']
        )

        return trade
