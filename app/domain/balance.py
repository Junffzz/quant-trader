# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import Dict

from app.constants import TradeMarket

@dataclass
class AccountBalance:
    """Account Balance Information"""
    cash: float = 0.0                          # CashBalance(BASE) 可用资金 (相当于资产负债表)
    cash_by_currency: Dict[str, float] = None  # CashBlance(HKD, USD, GBP)
    available_cash: float = 0.0                # AvailableFunds(HKD)
    power: float = 0.0                         # 购买力
    max_power_short: float = None              # Cash Power for Short
    net_cash_power: float = None               # BuyingPower(HKD)
    maintenance_margin: float = None           # MaintMarginReq(HKD)
    unrealized_pnl: float = 0.0                # UnrealizedPnL(HKD)
    realized_pnl: float = 0.0                  # RealizedPnL(HKD)