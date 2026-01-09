from typing import Any, Dict, Optional

from t_tech.invest import (
    AsyncClient,
    Client,
    GetLastPricesResponse,
    GetTradingStatusResponse,
    InstrumentResponse,
    OrderState,
    PostOrderResponse,
)
from t_tech.invest.async_services import AsyncServices
from t_tech.invest.services import Services

from app.settings import settings
from app.utils.quotation import quotation_to_float


class t_techClient:
    """
    Wrapper for t_tech.invest.AsyncClient.
    Takes responsibility for choosing correct function to call basing on sandbox mode flag.
    """

    def __init__(self, token: str, sandbox: bool = False):
        self.token = token
        self.sandbox = sandbox
        self.client: Optional[AsyncServices] = None
        self.sync_client: Optional[Services] = None

    async def ainit(self):
        self.client = await AsyncClient(
            token=self.token, app_name=settings.app_name
        ).__aenter__()

    async def get_operations(self, **kwagrs):
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_operations(**kwagrs)
        return await self.client.operations.get_operations(**kwagrs)

    async def get_operations_by_cursor(self, **kwargs):
        """Get operations using getOperationsByCursor method (returns all operations)"""
        if self.sandbox:
            # Sandbox doesn't support getOperationsByCursor, fallback to regular method
            return await self.client.sandbox.get_sandbox_operations(**kwargs)

        # getOperationsByCursor requires GetOperationsByCursorRequest object
        from t_tech.invest.schemas import GetOperationsByCursorRequest

        # Extract parameters
        account_id = kwargs.get("account_id", "")
        from_date = kwargs.get("from_", None)
        to_date = kwargs.get("to", None)

        # Create request object
        request = GetOperationsByCursorRequest(
            account_id=account_id, from_=from_date, to=to_date
        )

        return await self.client.operations.get_operations_by_cursor(request)

    async def get_orders(self, **kwargs):
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_orders(**kwargs)
        return await self.client.orders.get_orders(**kwargs)

    async def get_portfolio(self, **kwargs):
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_portfolio(**kwargs)
        return await self.client.operations.get_portfolio(**kwargs)

    async def get_positions(self, **kwargs):
        """Get current positions"""
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_positions(**kwargs)
        return await self.client.operations.get_positions(**kwargs)

    async def get_accounts(self):
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_accounts()
        return await self.client.users.get_accounts()

    async def get_all_candles(self, **kwargs):
        async for candle in self.client.get_all_candles(**kwargs):
            yield candle

    async def get_last_prices(self, **kwargs) -> GetLastPricesResponse:
        return await self.client.market_data.get_last_prices(**kwargs)

    async def post_order(self, **kwargs) -> PostOrderResponse:
        if self.sandbox:
            return await self.client.sandbox.post_sandbox_order(**kwargs)
        return await self.client.orders.post_order(**kwargs)

    async def get_order_state(self, **kwargs) -> OrderState:
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_order_state(**kwargs)
        return await self.client.orders.get_order_state(**kwargs)

    async def get_trading_status(self, **kwargs) -> GetTradingStatusResponse:
        return await self.client.market_data.get_trading_status(**kwargs)

    async def get_instrument(self, **kwargs) -> InstrumentResponse:
        return await self.client.instruments.get_instrument_by(**kwargs)

    async def find_instrument(self, **kwagrs):
        return await self.client.instruments.find_instrument(**kwagrs)

    async def get_last_price(self, figi):
        prices = await self.client.market_data.get_last_prices(figi=[figi])
        return quotation_to_float(prices.last_prices[0].price)

    async def get_operations_for_period(self, account_id: str, start_date, end_date):
        """Get operations for a specific period with proper error handling"""
        try:
            return await self.get_operations(
                account_id=account_id, from_=start_date, to=end_date
            )
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to get operations for period {start_date} to {end_date}: {e}"
            )
            return None

    async def get_historical_data(self, account_id: str, days: int = 30):
        """Get historical operations data for the specified number of days"""
        import datetime

        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)

        return await self.get_operations_for_period(account_id, start_date, end_date)

    def get_fixed_profit_analysis(self, operations_response):
        """
        Get profit analysis using the fixed calculator that correctly handles API data types

        This method uses the FixedProfitCalculator which properly handles:
        - MoneyValue conversion (units + nano/1e9)
        - Real operation types from API (15=SELL, 22=BUY, 19=COMMISSION, etc.)
        - Correct profit calculation matching table data
        """
        # Handle both list of operations and response object
        operations = operations_response
        if hasattr(operations_response, "operations"):
            operations = operations_response.operations

        if not operations:
            return {
                "daily_data": {},
                "summary": {
                    "total_days": 0,
                    "total_amount": 0,
                    "total_buy": 0,
                    "total_sell": 0,
                    "total_commission": 0,
                    "total_income": 0,
                    "total_expense": 0,
                    "total_other": 0,
                    "total_trades": 0,
                    "total_operations": 0,
                    "net_profit": 0,
                    "gross_profit": 0,
                    "profit_margin": 0,
                    "trade_volume": 0,
                },
                "table_format": {
                    "total_profit": 0,
                    "total_commission": 0,
                    "total_trades": 0,
                    "profit_percentage": 0,
                    "daily_breakdown": {},
                },
            }

        from app.utils.profit_calculator import ProfitCalculator

        calculator = ProfitCalculator()

        return calculator.get_fixed_profit_analysis(operations)

    async def calculate_starting_positions(self, account_id: str, start_date, end_date):
        """
        Calculate starting positions for a period by working backwards from current positions

        Args:
            account_id: Account ID
            start_date: Start of analysis period
            end_date: End of analysis period (usually now)

        Returns:
            Dict mapping FIGI to starting position
        """
        try:
            # Get current positions
            current_positions_response = await self.get_positions(account_id=account_id)
            current_positions = {}

            if current_positions_response and current_positions_response.positions:
                for position in current_positions_response.positions:
                    figi = position.figi
                    # Convert quantity to integer (lot count)
                    quantity = int(quotation_to_float(position.quantity))
                    current_positions[figi] = quantity

            # Get operations from start_date to end_date
            operations_response = await self.get_operations_for_period(
                account_id, start_date, end_date
            )

            if not operations_response or not operations_response.operations:
                return current_positions

            # Calculate starting positions by working backwards
            starting_positions = current_positions.copy()

            # Process operations in reverse chronological order
            operations = sorted(
                operations_response.operations, key=lambda x: x.date, reverse=True
            )

            from t_tech.invest import OperationType

            for operation in operations:
                if operation.operation_type in [
                    OperationType.OPERATION_TYPE_BUY,
                    OperationType.OPERATION_TYPE_SELL,
                ]:
                    figi = operation.figi
                    quantity = operation.quantity

                    # Initialize position if not exists
                    if figi not in starting_positions:
                        starting_positions[figi] = 0

                    # Reverse the operation:
                    # If it was a BUY, we had fewer shares before → subtract
                    # If it was a SELL, we had more shares before → add
                    if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
                        starting_positions[figi] -= quantity
                    else:  # SELL
                        starting_positions[figi] += quantity

            return starting_positions

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to calculate starting positions: {e}")
            return {}

    async def get_profit_analysis_with_auto_positions(
        self, account_id: str, start_date, end_date
    ):
        """
        Get profit analysis with automatically calculated starting positions

        Args:
            account_id: Account ID
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Tuple of (trades, total_profit, operations, starting_positions)
        """
        try:
            # Calculate starting positions automatically
            starting_positions = await self.calculate_starting_positions(
                account_id, start_date, end_date
            )

            # Get operations for the period
            operations_response = await self.get_operations_for_period(
                account_id, start_date, end_date
            )

            if not operations_response or not operations_response.operations:
                return [], 0.0, [], starting_positions

            # Use ProfitCalculator with starting positions
            from app.utils.profit_calculator import ProfitCalculator

            calculator = ProfitCalculator()

            trades, total_profit, operations = (
                calculator.process_operations_with_starting_positions(
                    operations_response.operations, starting_positions
                )
            )

            return trades, total_profit, operations, starting_positions

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get profit analysis with auto positions: {e}")
            return [], 0.0, [], {}

    def init_sync_client(self):
        """Initialize synchronous client"""
        if self.sync_client is None:
            self.sync_client = Client(token=self.token, app_name=settings.app_name)
        return self.sync_client

    def get_operations_sync(self, **kwargs):
        """Synchronous version of get_operations"""
        client = self.init_sync_client()
        if self.sandbox:
            return client.sandbox.get_sandbox_operations(**kwargs)
        return client.operations.get_operations(**kwargs)

    def get_positions_sync(self, **kwargs):
        """Synchronous version of get_positions"""
        client = self.init_sync_client()
        if self.sandbox:
            return client.sandbox.get_sandbox_positions(**kwargs)
        return client.operations.get_positions(**kwargs)

    def calculate_starting_positions_sync(self, account_id: str, start_date, end_date):
        """
        Synchronous version of calculate_starting_positions
        """
        try:
            # Get current positions
            current_positions_response = self.get_positions_sync(account_id=account_id)
            current_positions = {}

            if current_positions_response and current_positions_response.positions:
                for position in current_positions_response.positions:
                    figi = position.figi
                    # Convert quantity to integer (lot count)
                    quantity = int(quotation_to_float(position.quantity))
                    current_positions[figi] = quantity

            # Get operations from start_date to end_date
            operations_response = self.get_operations_sync(
                account_id=account_id, from_=start_date, to=end_date
            )

            if not operations_response or not operations_response.operations:
                return current_positions

            # Calculate starting positions by working backwards
            starting_positions = current_positions.copy()

            # Process operations in reverse chronological order
            operations = sorted(
                operations_response.operations, key=lambda x: x.date, reverse=True
            )

            from t_tech.invest import OperationType

            for operation in operations:
                if operation.operation_type in [
                    OperationType.OPERATION_TYPE_BUY,
                    OperationType.OPERATION_TYPE_SELL,
                ]:
                    figi = operation.figi
                    quantity = operation.quantity

                    # Initialize position if not exists
                    if figi not in starting_positions:
                        starting_positions[figi] = 0

                    # Reverse the operation:
                    # If it was a BUY, we had fewer shares before → subtract
                    # If it was a SELL, we had more shares before → add
                    if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
                        starting_positions[figi] -= quantity
                    else:  # SELL
                        starting_positions[figi] += quantity

            return starting_positions

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to calculate starting positions: {e}")
            return {}

    def get_profit_analysis_with_auto_positions_sync(
        self, account_id: str, start_date, end_date
    ):
        """
        Synchronous version of get_profit_analysis_with_auto_positions
        """
        try:
            # Calculate starting positions automatically
            starting_positions = self.calculate_starting_positions_sync(
                account_id, start_date, end_date
            )

            # Get operations for the period
            operations_response = self.get_operations_sync(
                account_id=account_id, from_=start_date, to=end_date
            )

            if not operations_response or not operations_response.operations:
                return [], 0.0, [], starting_positions

            # Use ProfitCalculator with starting positions
            from app.utils.profit_calculator import ProfitCalculator

            calculator = ProfitCalculator()

            trades, total_profit, operations = (
                calculator.process_operations_with_starting_positions(
                    operations_response.operations, starting_positions
                )
            )

            return trades, total_profit, operations, starting_positions

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get profit analysis with auto positions: {e}")
            return [], 0.0, [], {}

    def get_profit_analysis_with_auto_detected_positions_sync(
        self, account_id: str, start_date, end_date
    ):
        """
        Получает анализ прибыли с автоматическим определением начальных позиций

        Args:
            account_id: Account ID
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Tuple of (trades, total_profit, operations, detected_starting_positions)
        """
        try:
            # Получаем операции за период
            operations_response = self.get_operations_sync(
                account_id=account_id, from_=start_date, to=end_date
            )

            if not operations_response or not operations_response.operations:
                return [], 0.0, [], {}

            # Используем ProfitCalculator с автоматическим определением позиций
            from app.utils.profit_calculator import ProfitCalculator

            calculator = ProfitCalculator()

            trades, total_profit, operations, starting_positions = (
                calculator.process_operations_with_auto_positions(
                    operations_response.operations
                )
            )

            return trades, total_profit, operations, starting_positions

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to get profit analysis with auto-detected positions: {e}"
            )
            return [], 0.0, [], {}

    async def get_profit_analysis_with_auto_detected_positions(
        self, account_id: str, start_date, end_date
    ):
        """
        Асинхронная версия get_profit_analysis_with_auto_detected_positions_sync
        """
        try:
            # Получаем операции за период
            operations_response = await self.get_operations_for_period(
                account_id, start_date, end_date
            )

            if not operations_response or not operations_response.operations:
                return [], 0.0, [], {}

            # Используем ProfitCalculator с автоматическим определением позиций
            from app.utils.profit_calculator import ProfitCalculator

            calculator = ProfitCalculator()

            trades, total_profit, operations, starting_positions = (
                calculator.process_operations_with_auto_positions(
                    operations_response.operations
                )
            )

            return trades, total_profit, operations, starting_positions

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to get profit analysis with auto-detected positions: {e}"
            )
            return [], 0.0, [], {}

    async def get_all_operations_by_cursor(
        self, account_id: str, target_date=None, batch_size: int = 1000
    ):
        """
        Get all operations up to target_date using cursor pagination

        Args:
            account_id: Account ID
            target_date: Target date to get operations up to (if None, gets all operations)
            batch_size: Number of operations per batch (max 1000)

        Returns:
            List of all operations up to target_date
        """
        if self.sandbox:
            # Sandbox doesn't support getOperationsByCursor, fallback to regular method
            return await self.get_operations(account_id=account_id)

        import logging

        from t_tech.invest.schemas import GetOperationsByCursorRequest

        logger = logging.getLogger(__name__)

        all_operations = []
        cursor = None  # Start with None for first request

        try:
            while True:
                # Create request with cursor
                request = GetOperationsByCursorRequest(
                    account_id=account_id, limit=batch_size
                )

                # Add cursor if we have one
                if cursor:
                    request.cursor = cursor

                # Get batch of operations
                response = await self.client.operations.get_operations_by_cursor(
                    request
                )

                if not response or not response.items:
                    logger.info("No more operations found")
                    break

                # Process operations in this batch
                batch_operations = []
                for item in response.items:
                    # Normalize timezone for comparison
                    item_date = item.date
                    if target_date:
                        # Normalize target_date timezone
                        if target_date.tzinfo is None:
                            import pytz

                            target_date = pytz.UTC.localize(target_date)
                        if item_date.tzinfo is None:
                            import pytz

                            item_date = pytz.UTC.localize(item_date)

                        # Check if we've reached the target date
                        if item_date <= target_date:
                            # We've reached operations before target_date, stop
                            logger.info(
                                f"Reached target date {target_date}, stopping at operation date {item_date}"
                            )
                            # Don't add this operation to the batch
                            continue

                    batch_operations.append(item)

                all_operations.extend(batch_operations)
                logger.info(
                    f"Retrieved {len(batch_operations)} operations in this batch, total: {len(all_operations)}"
                )

                # Check if we've reached target date or no more operations
                if target_date:
                    # Check if any operation in this batch is before or equal to target_date
                    reached_target = False
                    for item in response.items:
                        item_date = item.date
                        if item_date.tzinfo is None:
                            import pytz

                            item_date = pytz.UTC.localize(item_date)
                        if item_date <= target_date:
                            reached_target = True
                            break
                    if reached_target:
                        break

                # Check if we have more operations to fetch
                if not response.has_next:
                    logger.info("No more operations available")
                    break

                # Get cursor for next batch
                cursor = response.next_cursor
                if not cursor:
                    logger.info("No next cursor available")
                    break

        except Exception as e:
            logger.error(f"Error fetching operations by cursor: {e}")
            # Fallback to regular method
            logger.info("Falling back to regular get_operations method")
            return await self.get_operations(account_id=account_id)

        logger.info(f"Total operations retrieved: {len(all_operations)}")
        return all_operations

    async def get_operations_with_limit_offset(
        self,
        account_id: str,
        start_date=None,
        end_date=None,
        limit: int = 1000,
        offset: int = 0,
    ):
        """
        Get operations using limit and offset for pagination

        Args:
            account_id: Account ID
            start_date: Start date for filtering operations
            end_date: End date for filtering operations
            limit: Number of operations to return (max 1000)
            offset: Number of operations to skip

        Returns:
            List of operations for the specified period
        """
        if self.sandbox:
            # Sandbox doesn't support getOperationsByCursor, fallback to regular method
            return await self.get_operations(
                account_id=account_id, from_=start_date, to=end_date
            )

        import logging

        from t_tech.invest.schemas import GetOperationsByCursorRequest

        logger = logging.getLogger(__name__)

        try:
            # Create request with limit (offset is not supported in GetOperationsByCursorRequest)
            # Use limit > 2 to avoid problems with duplicated operations and cursor movement
            # Ensure limit > 2 as per API recommendations
            safe_limit = max(limit, 3)
            request = GetOperationsByCursorRequest(
                account_id=account_id, limit=safe_limit
            )

            # Add date filters if provided
            if start_date:
                request.from_ = start_date
            if end_date:
                request.to = end_date

            # Get operations
            response = await self.client.operations.get_operations_by_cursor(request)

            if not response or not response.items:
                logger.info("No operations found for the specified period")
                return []

            logger.info(f"Retrieved {len(response.items)} operations (limit={limit})")
            return response.items

        except Exception as e:
            logger.error(f"Error fetching operations with limit/offset: {e}")
            # Fallback to regular method
            logger.info("Falling back to regular get_operations method")
            operations_response = await self.get_operations(
                account_id=account_id, from_=start_date, to=end_date
            )
            if operations_response and hasattr(operations_response, "operations"):
                return operations_response.operations
            return []

    async def get_all_operations_for_period(
        self, account_id: str, start_date, end_date
    ):
        """
        Get all operations for a specific period using cursor pagination

        Args:
            account_id: Account ID
            start_date: Start date for the period
            end_date: End date for the period

        Returns:
            List of all operations for the period
        """
        import logging

        logger = logging.getLogger(__name__)

        all_operations = []
        cursor = None
        limit = 1000  # Use limit > 2 to avoid cursor problems

        try:
            while True:
                # Create request with cursor
                from t_tech.invest.schemas import GetOperationsByCursorRequest

                request = GetOperationsByCursorRequest(
                    account_id=account_id, limit=limit
                )

                # Add cursor if we have one
                if cursor:
                    request.cursor = cursor

                # Add date filters if provided
                if start_date:
                    request.from_ = start_date
                if end_date:
                    request.to = end_date

                # Get batch of operations
                response = await self.client.operations.get_operations_by_cursor(
                    request
                )

                if not response or not response.items:
                    logger.info("No more operations found")
                    break

                # Filter operations by date if needed (double-check)
                filtered_operations = []
                for item in response.items:
                    item_date = item.date
                    if start_date and item_date < start_date:
                        continue
                    if end_date and item_date > end_date:
                        continue
                    filtered_operations.append(item)

                all_operations.extend(filtered_operations)
                logger.info(
                    f"Retrieved {len(filtered_operations)} operations, total: {len(all_operations)}"
                )

                # Check if we have more operations to fetch
                if not response.has_next:
                    logger.info("No more operations available")
                    break

                # Get cursor for next batch
                cursor = response.next_cursor
                if not cursor:
                    logger.info("No next cursor available")
                    break

        except Exception as e:
            logger.error(f"Error fetching all operations for period: {e}")
            # Fallback to regular method
            operations_response = await self.get_operations(
                account_id=account_id, from_=start_date, to=end_date
            )
            if operations_response and hasattr(operations_response, "operations"):
                return operations_response.operations
            return []

        logger.info(f"Total operations for period: {len(all_operations)}")
        return all_operations

    async def get_operations_by_cursor(self, **kwargs):
        """Get operations using getOperationsByCursor method (returns all operations)"""
        if self.sandbox:
            # Sandbox doesn't support getOperationsByCursor, fallback to regular method
            return await self.client.sandbox.get_sandbox_operations(**kwargs)

        # getOperationsByCursor requires GetOperationsByCursorRequest object
        from t_tech.invest.schemas import GetOperationsByCursorRequest

        # Extract parameters
        account_id = kwargs.get("account_id", "")
        from_date = kwargs.get("from_", None)
        to_date = kwargs.get("to", None)

        # Create request object
        request = GetOperationsByCursorRequest(
            account_id=account_id, from_=from_date, to=to_date
        )

        return await self.client.operations.get_operations_by_cursor(request)

    async def get_enhanced_profit_analysis(
        self, account_id: str, start_date, end_date, use_current_positions: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced profit analysis with comprehensive position tracking and issue detection

        This method provides the most accurate profit calculation by:
        1. Using current positions to calculate starting positions
        2. Providing detailed analysis of potential issues
        3. Offering recommendations for data quality

        Args:
            account_id: Account ID
            start_date: Start of analysis period
            end_date: End of analysis period
            use_current_positions: Whether to use current positions for more accurate calculation

        Returns:
            Dict with comprehensive analysis including trades, profit, positions, and recommendations
        """
        try:
            # Get current positions if requested
            current_positions = {}
            if use_current_positions:
                current_positions_response = await self.get_positions(
                    account_id=account_id
                )
                if current_positions_response:
                    # The positions response has 'securities' attribute
                    if hasattr(current_positions_response, "securities"):
                        for security in current_positions_response.securities:
                            figi = security.figi
                            # Use 'balance' attribute for securities
                            quantity = int(security.balance)
                            current_positions[figi] = quantity

                    # Also check for futures positions
                    if hasattr(current_positions_response, "futures"):
                        for future in current_positions_response.futures:
                            figi = future.figi
                            # Use 'balance' attribute for futures
                            quantity = int(future.balance)
                            current_positions[figi] = quantity

            # Get operations for the period
            operations_response = await self.get_operations_for_period(
                account_id, start_date, end_date
            )
            if not operations_response or not operations_response.operations:
                return {
                    "trades": [],
                    "total_profit": 0.0,
                    "operations": [],
                    "starting_positions": {},
                    "analysis_report": {
                        "summary": {"total_operations": 0, "total_trades": 0},
                        "data_quality": {"issues_found": 0, "issues": []},
                        "recommendations": [
                            "No operations found for the specified period"
                        ],
                    },
                }

            # Use enhanced profit calculator
            from app.utils.profit_calculator import ProfitCalculator

            calculator = ProfitCalculator()

            trades, total_profit, operations, starting_positions, analysis_report = (
                calculator.get_enhanced_profit_analysis(
                    operations_response.operations,
                    current_positions if use_current_positions else None,
                )
            )

            # Additional analysis
            problematic_trades = calculator.detect_problematic_trades(trades)
            position_history = calculator.get_position_history(
                operations_response.operations, starting_positions
            )

            # Validate position consistency
            validation_result = calculator.validate_position_consistency(
                operations_response.operations,
                starting_positions,
                current_positions if use_current_positions else None,
            )

            return {
                "trades": trades,
                "total_profit": total_profit,
                "operations": operations,
                "starting_positions": starting_positions,
                "current_positions": current_positions,
                "analysis_report": analysis_report,
                "problematic_trades": problematic_trades,
                "position_history": position_history,
                "validation_result": validation_result,
                "method_used": "current_positions"
                if use_current_positions
                else "auto_detection",
            }

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get enhanced profit analysis: {e}")
            return {
                "error": str(e),
                "trades": [],
                "total_profit": 0.0,
                "operations": [],
                "starting_positions": {},
                "analysis_report": {
                    "summary": {"total_operations": 0, "total_trades": 0},
                    "data_quality": {"issues_found": 1, "issues": [f"Error: {str(e)}"]},
                    "recommendations": [
                        "Check your API credentials and account access"
                    ],
                },
            }

    def get_enhanced_profit_analysis_sync(
        self, account_id: str, start_date, end_date, use_current_positions: bool = True
    ) -> Dict[str, Any]:
        """
        Synchronous version of get_enhanced_profit_analysis
        """
        try:
            # Get current positions if requested
            current_positions = {}
            if use_current_positions:
                current_positions_response = self.get_positions_sync(
                    account_id=account_id
                )
                if current_positions_response:
                    # The positions response has 'securities' attribute
                    if hasattr(current_positions_response, "securities"):
                        for security in current_positions_response.securities:
                            figi = security.figi
                            # Use 'balance' attribute for securities
                            quantity = int(security.balance)
                            current_positions[figi] = quantity

                    # Also check for futures positions
                    if hasattr(current_positions_response, "futures"):
                        for future in current_positions_response.futures:
                            figi = future.figi
                            # Use 'balance' attribute for futures
                            quantity = int(future.balance)
                            current_positions[figi] = quantity

            # Get operations for the period
            operations_response = self.get_operations_sync(
                account_id=account_id, from_=start_date, to=end_date
            )

            if not operations_response or not operations_response.operations:
                return {
                    "trades": [],
                    "total_profit": 0.0,
                    "operations": [],
                    "starting_positions": {},
                    "analysis_report": {
                        "summary": {"total_operations": 0, "total_trades": 0},
                        "data_quality": {"issues_found": 0, "issues": []},
                        "recommendations": [
                            "No operations found for the specified period"
                        ],
                    },
                }

            # Use enhanced profit calculator
            from app.utils.profit_calculator import ProfitCalculator

            calculator = ProfitCalculator()

            trades, total_profit, operations, starting_positions, analysis_report = (
                calculator.get_enhanced_profit_analysis(
                    operations_response.operations,
                    current_positions if use_current_positions else None,
                )
            )

            # Additional analysis
            problematic_trades = calculator.detect_problematic_trades(trades)
            position_history = calculator.get_position_history(
                operations_response.operations, starting_positions
            )

            # Validate position consistency
            validation_result = calculator.validate_position_consistency(
                operations_response.operations,
                starting_positions,
                current_positions if use_current_positions else None,
            )

            return {
                "trades": trades,
                "total_profit": total_profit,
                "operations": operations,
                "starting_positions": starting_positions,
                "current_positions": current_positions,
                "analysis_report": analysis_report,
                "problematic_trades": problematic_trades,
                "position_history": position_history,
                "validation_result": validation_result,
                "method_used": "current_positions"
                if use_current_positions
                else "auto_detection",
            }

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get enhanced profit analysis: {e}")
            return {
                "error": str(e),
                "trades": [],
                "total_profit": 0.0,
                "operations": [],
                "starting_positions": {},
                "analysis_report": {
                    "summary": {"total_operations": 0, "total_trades": 0},
                    "data_quality": {"issues_found": 1, "issues": [f"Error: {str(e)}"]},
                    "recommendations": [
                        "Check your API credentials and account access"
                    ],
                },
            }

    async def diagnose_profit_calculation_issues(
        self, account_id: str, start_date, end_date
    ) -> Dict[str, Any]:
        """
        Diagnose profit calculation issues and provide recommendations

        Args:
            account_id: Account ID
            start_date: Start of analysis period
            end_date: End of analysis period

        Returns:
            Dict with diagnostic information and recommendations
        """
        try:
            # Get enhanced analysis
            enhanced_analysis = await self.get_enhanced_profit_analysis(
                account_id, start_date, end_date, use_current_positions=True
            )

            # Get traditional analysis for comparison
            traditional_analysis = (
                await self.get_profit_analysis_with_auto_detected_positions(
                    account_id, start_date, end_date
                )
            )

            diagnosis = {
                "comparison": {
                    "enhanced_profit": enhanced_analysis["total_profit"],
                    # total_profit from tuple
                    "traditional_profit": traditional_analysis[1],
                    "profit_difference": enhanced_analysis["total_profit"]
                    - traditional_analysis[1],
                    "trade_count_enhanced": len(enhanced_analysis["trades"]),
                    # trades from tuple
                    "trade_count_traditional": len(traditional_analysis[0]),
                },
                "issues_detected": enhanced_analysis["analysis_report"]["data_quality"][
                    "issues"
                ],
                "problematic_trades": enhanced_analysis["problematic_trades"],
                "validation_result": enhanced_analysis["validation_result"],
                "recommendations": enhanced_analysis["analysis_report"][
                    "recommendations"
                ],
            }

            # Add severity assessment
            severity = "low"
            if abs(diagnosis["comparison"]["profit_difference"]) > 10000:
                severity = "high"
            elif abs(diagnosis["comparison"]["profit_difference"]) > 1000:
                severity = "medium"

            diagnosis["severity"] = severity

            # Add specific recommendations based on diagnosis
            specific_recommendations = []

            if diagnosis["comparison"]["profit_difference"] < -10000:
                specific_recommendations.append(
                    "Large negative difference detected - likely missing starting position data"
                )

            if len(diagnosis["problematic_trades"]) > 0:
                specific_recommendations.append(
                    f"Found {len(diagnosis['problematic_trades'])} problematic trades"
                )

            if not diagnosis["validation_result"]["valid"]:
                specific_recommendations.append(
                    "Position validation failed - check operation data consistency"
                )

            diagnosis["specific_recommendations"] = specific_recommendations

            return diagnosis

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to diagnose profit calculation issues: {e}")
            return {
                "error": str(e),
                "severity": "unknown",
                "recommendations": ["Unable to perform diagnosis due to error"],
            }


client = t_techClient(token=settings.token, sandbox=settings.sandbox)
