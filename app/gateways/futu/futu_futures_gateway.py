from typing import Dict, List
from datetime import datetime
from datetime import timedelta

import pandas as pd
from futu import (
    RET_OK,
    RET_ERROR,
    OrderBookHandlerBase,
    TradeOrderHandlerBase,
    TradeDealHandlerBase,
    OpenFutureTradeContext,
    SubType,
    OrderType,
    ModifyOrderOp,
    KLType,
    AuType,
    KL_FIELD,
    TrdSide,
    TrdEnv,
    OrderStatus,
    OpenQuoteContext,
    OpenSecTradeContext
)

from app.domain.balance import AccountBalance
from app.domain.security import Security, Futures
from app.gateways.base_gateway import BaseFees
from app.gateways.futu import FutuGateway
from trader_config import GATEWAYS, DATA_PATH, TIME_STEP

FUTUFUTURES = GATEWAYS.get("Futufutures")

class FutuFuturesGateway(FutuGateway):
    """Futu futures gateway"""

    # Minimal time step, which was read from config
    TIME_STEP = TIME_STEP

    # Short interest rate, 0.0 for HK futures
    SHORT_INTEREST_RATE = 0.0

    # Name of the gateway
    NAME = "FUTUFUTURES"

    def __init__(
            self,
            securities: List[Futures],
            gateway_name: str,
            start: datetime = None,
            end: datetime = None,
            fees: BaseFees = BaseFees,
            **kwargs
    ):
        super(FutuGateway, self).__init__(securities, gateway_name)
        self.fees = fees
        self.start = start
        self.end = end
        if "trading_sessions" in kwargs:
            self.trading_sessions = kwargs.get("trading_sessions")

        self.pwd_unlock = FUTUFUTURES["pwd_unlock"]

        self.quote_ctx = OpenQuoteContext(
            host=FUTUFUTURES["host"],
            port=FUTUFUTURES["port"])
        self.connect_quote()
        self.subscribe()

        self.trd_ctx = OpenFutureTradeContext(
            host=FUTUFUTURES["host"], port=FUTUFUTURES["port"])
        self.connect_trade()

    def get_broker_balance(self) -> AccountBalance:
        """Broker balance"""
        ret_code, data = self.trd_ctx.accinfo_query(trd_env=self.futu_trd_env)
        if ret_code:
            print(f"[get_broker_balanc] failed: {data}")
            return
        balance = AccountBalance()
        balance.cash = data["cash"].values[0]
        balance.available_cash = data["available_funds"].values[0]
        balance.maintenance_margin = data["maintenance_margin"].values[0]
        balance.unrealized_pnl = data["unrealized_pl"].values[0]
        balance.max_power_short = data["max_power_short"].values[0]
        balance.net_cash_power = data["net_cash_power"].values[0]
        if not isinstance(balance.max_power_short, float):
            balance.max_power_short = -1
        if not isinstance(balance.net_cash_power, float):
            balance.net_cash_power = -1
        return balance