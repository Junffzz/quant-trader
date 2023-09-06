# -*- coding: utf-8 -*-

from dataclasses import dataclass
from datetime import datetime

from app.constants import Direction, Offset, OrderType
from app.domain.security import Security

# 交易
@dataclass
class Deal:
    """Done deal/execution"""
    security: Security
    direction: Direction
    offset: Offset
    order_type: OrderType
    updated_time: datetime = None
    filled_avg_price: float = 0
    filled_quantity: int = 0
    dealid: str = ""
    orderid: str = ""
