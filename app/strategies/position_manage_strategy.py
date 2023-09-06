# -*- coding: utf-8 -*-
import math


class SecurityPositionStrategy:
    """
    证券仓位策略
    """

    def __init__(self, count=1, power_cash: float = 0.0, available_cash: float = 0.0):
        self.power_cash = power_cash
        self.available_cash = available_cash
        self.per_weight = float(1) / float(count)

    def get_order_quantity(self, price: float = None) -> int:
        cash = self.power_cash * self.per_weight
        if cash > self.available_cash:
            cash = self.available_cash
        size = cash / price
        return math.floor(size)

    def update_available_cash(self, cash: float = 0.0):
        self.available_cash = cash
