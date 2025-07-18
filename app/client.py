from typing import Optional

from tinkoff.invest import (
    AsyncClient,
    PostOrderResponse,
    GetLastPricesResponse,
    OrderState,
    GetTradingStatusResponse,
    InstrumentResponse,
)
from tinkoff.invest.async_services import AsyncServices
from tinkoff.invest.services import Services

from app.settings import settings
from app.utils.quotation import quotation_to_float


class TinkoffClient:
    """
    Wrapper for tinkoff.invest.AsyncClient.
    Takes responsibility for choosing correct function to call basing on sandbox mode flag.
    """

    def __init__(self, token: str, sandbox: bool = False):
        self.token = token
        self.sandbox = sandbox
        self.client: Optional[AsyncServices] = None
        self.sync_client: Optional[Services] = None

    async def ainit(self):
        self.client = await AsyncClient(token=self.token, app_name=settings.app_name).__aenter__()

    async def get_operations(self, **kwagrs):
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_operations(**kwagrs)
        return await self.client.operations.get_operations(**kwagrs)

    async def get_orders(self, **kwargs):
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_orders(**kwargs)
        return await self.client.orders.get_orders(**kwargs)

    async def get_portfolio(self, **kwargs):
        if self.sandbox:
            return await self.client.sandbox.get_sandbox_portfolio(**kwargs)
        return await self.client.operations.get_portfolio(**kwargs)

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
                account_id=account_id,
                from_=start_date,
                to=end_date
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to get operations for period {start_date} to {end_date}: {e}")
            return None

    async def get_historical_data(self, account_id: str, days: int = 30):
        """Get historical operations data for the specified number of days"""
        import datetime
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)

        return await self.get_operations_for_period(account_id, start_date, end_date)

    def get_profit_analysis(self, operations_response):
        """Get profit analysis using the new ProfitCalculator"""
        if not operations_response or not operations_response.operations:
            return [], 0.0, []

        from app.utils.profit_calculator import ProfitCalculator
        calculator = ProfitCalculator()

        return calculator.process_operations(operations_response.operations)


client = TinkoffClient(token=settings.token, sandbox=settings.sandbox)
