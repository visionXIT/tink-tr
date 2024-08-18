from pathlib import Path
from typing import Optional

from tinkoff.invest import (
    AsyncClient,
    Client,
    PostOrderResponse,
    GetLastPricesResponse,
    OrderState,
    GetTradingStatusResponse,
    InstrumentResponse,
)
from tinkoff.invest.async_services import AsyncServices
from tinkoff.invest.caching.market_data_cache.cache_settings import MarketDataCacheSettings
from tinkoff.invest.services import MarketDataCache, Services

from app.settings import settings


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
        self.market_data_cache: Optional[MarketDataCache] = None

    async def ainit(self):
        self.client = await AsyncClient(token=self.token, app_name=settings.app_name).__aenter__()
        if settings.use_candle_history_cache:
            self.sync_client = Client(
                token=self.token, app_name=settings.app_name).__enter__()
            self.market_data_cache = MarketDataCache(
                settings=MarketDataCacheSettings(
                    base_cache_dir=Path("market_data_cache")),
                services=self.sync_client,
            )

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


client = TinkoffClient(token=settings.token, sandbox=False)
