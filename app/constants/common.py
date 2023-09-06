#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enum import Enum

class MarketEnum(Enum):
    """
    Market.
    """
    A = "A"
    HK = "HK"
    US = "US"

class CurrencyEnum(Enum):
    """
    Currency.
    """
    USD = "USD"
    HKD = "HKD"
    CNY = "CNY"
    CAD = "CAD"


class IntervalEnum(Enum):
    """
    Interval of bar data.
    """
    MINUTE = "1m"
    HOUR = "1h"
    DAILY = "d"
    WEEKLY = "w"
    TICK = "tick"