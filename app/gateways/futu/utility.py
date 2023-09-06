# -*- coding: utf-8 -*-

from futu import (
    TrdMarket,
    TimeInForce,
    TrdSide,
    TrdEnv,
    Plate,
    OrderStatus,
)

from app.constants import Direction, TradeMode, TradeMarket, OrderTimeInForce
from app.constants import OrderStatus as QTOrderStatus
from app.domain.security import Futures


def convert_trade_market_qt2futu(trade_market: TradeMarket) -> TrdMarket:
    """Convert trade mode to Futu"""
    if trade_market == TradeMarket.US:
        return TrdMarket.US
    elif trade_market == TradeMarket.HK:
        return TrdMarket.HK
    elif trade_market == TradeMarket.CN:
        return TrdMarket.CN
    elif trade_market == TradeMarket.FUTURES:
        return TrdMarket.FUTURES
    elif trade_market == TradeMarket.HKCC:
        return TrdMarket.HKCC
    else:
        raise ValueError(f"TradeMarket {trade_market} is not supported.")


def convert_direction_qt2futu(direction: Direction) -> TrdSide:
    """Convert QT direction to Futu"""
    if direction == Direction.SHORT:
        return TrdSide.SELL
    elif direction == Direction.LONG:
        return TrdSide.BUY
    else:
        raise ValueError(f"Direction {direction} is not supported.")


def convert_trade_mode_qt2futu(trade_mode: TradeMode) -> TrdEnv:
    """Convert trade mode to Futu"""
    if trade_mode == TradeMode.SIMULATE:
        return TrdEnv.SIMULATE
    elif trade_mode == TradeMode.LIVETRADE:
        return TrdEnv.REAL
    else:
        raise ValueError(f"TradeMode {trade_mode} is not supported.")


def convert_plate_qt2futu(plate: str) -> Plate:
    """Convert trade mode to Futu"""
    if plate == "ALL":
        return Plate.ALL
    elif plate == "INDUSTRY":
        return Plate.INDUSTRY
    elif plate == "REGION":  # 地域板块（港美股市场的地域分类数据暂为空）
        return Plate.REGION
    elif plate == "CONCEPT":
        return Plate.CONCEPT
    elif plate == "OTHER":
        return Plate.OTHER
    else:
        raise ValueError(f"Plate {plate} is not supported.")


def convert_orderstatus_futu2qt(status: OrderStatus) -> QTOrderStatus:
    """Convert order status to Futu"""
    if status in (
            OrderStatus.NONE,
            OrderStatus.UNSUBMITTED,
            OrderStatus.WAITING_SUBMIT,
            OrderStatus.SUBMITTING,
            OrderStatus.DISABLED,
            OrderStatus.DELETED):
        return QTOrderStatus.UNKNOWN
    elif status in (OrderStatus.SUBMITTED):
        return QTOrderStatus.SUBMITTED
    elif status in (OrderStatus.FILLED_ALL):
        return QTOrderStatus.FILLED
    elif status in (OrderStatus.FILLED_PART):
        return QTOrderStatus.PART_FILLED
    elif status in (
            OrderStatus.CANCELLED_ALL,
            OrderStatus.CANCELLED_PART,
            OrderStatus.CANCELLING_PART):
        return QTOrderStatus.CANCELLED
    elif status in (
            OrderStatus.SUBMIT_FAILED,
            OrderStatus.TIMEOUT,
            OrderStatus.FAILED):
        return QTOrderStatus.FAILED
    else:
        raise ValueError(f"Order status {status} is not recognized.")


def convert_orderTimeInForce_qt2futu(time_in_force: OrderTimeInForce) -> TimeInForce:
    """Convert QT direction to Futu"""
    if time_in_force == OrderTimeInForce.DAY:
        return TimeInForce.DAY
    elif time_in_force == OrderTimeInForce.GTC:
        return TimeInForce.GTC
    else:
        raise ValueError(f"time_in_force {time_in_force} is not supported.")


def get_hk_futures_code(security: Futures) -> str:
    """Use security code and expiry date to determine exact futures code"""
    return security.code.replace("main", security.expiry_date[2:6])
