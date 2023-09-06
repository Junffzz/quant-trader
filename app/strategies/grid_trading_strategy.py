#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing
from abc import ABC
from time import sleep
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass, asdict
from enum import Enum

import pandas as pd
import pandas_ta as ta
import exchange_calendars as xcals

from functools import reduce
from app.domain.balance import AccountBalance
from app.domain.position import Position, PositionData
from app.constants import Direction, Offset, OrderTimeInForce, OrderType, TradeMode, OrderStatus
from app.domain.data import Bar
from app.domain.order import Order
from app.domain.engine import Engine
from app.domain.security import Stock, Security
from app.utils import logger
from app.strategies.base_strategy import BaseStrategy
from app.utils.tasks import SingleTask, LoopRunTask

from multiprocessing import Process, freeze_support

# 策略代码总共分为三大部分，1)PARAMS变量 2)initialize函数 3)handle_data函数
# 请根据指示阅读。或者直接点击运行回测按钮，进行测试，查看策略效果。

# 策略名称：网格交易策略
# 策略详细介绍：https://wequant.io/study/strategy.grid_trading.html
# https://www.shinnytech.com/blog/grid-trading/
# 关键词：高抛低吸、逐步建仓。
# 方法：
# 1)设定一个基础价格，并围绕基础价格设置价格网格;
# 2)在相应价格位置调整仓位至相应水平(高位减仓，低位加仓);
# 3)在价格的波动中赚取收益。

# 阅读1，首次阅读可跳过:
# PARAMS用于设定程序参数，回测的起始时间、结束时间、滑点误差、初始资金和持仓。
# 可以仿照格式修改，基本都能运行。如果想了解详情请参考新手学堂的API文档。
PARAMS = {
    "start_time": "2017-06-01 00:00:00",
    "end_time": "2017-07-01 00:00:00",
    "commission": 0.001,  # 此处设置交易佣金
    "slippage": 0.001,  # 此处设置交易滑点
    "account_initial": {"huobi_cny_cash": 100000,
                        "huobi_cny_eth": 0},
}

GRID_SIDE_BUY: str = "BUY"
GRID_SIDE_SELL: str = "SELL"
GRID_SIDE_RESET: str = "RESET"


class Interval_mode(Enum):
    AS = "arithmetic_sequence"  # 等差
    GS = "geometric_sequence"  # 等比


@dataclass
class TradingContext:
    """交易信号上下文"""
    position: Position = None
    base_price: float = None
    grid_layer: int = 0  # 当前所在第几个档位层次;layer > 0 表示多头方向, layer < 0 表示空头方向
    grid_amount = 10  # 网格在多头、空头方向的格子(档位)数量
    grid_long_ratio: float = 0.05  # 网格多头变动比例
    grid_short_ratio: float = 0.05  # 网格空头变动比例
    # 止损线，用户自定义的变量，可以被handle_data使用
    portfolio_stop_loss = 0.00
    # 用户自定义变量，记录下是否已经触发止损
    stop_loss_triggered = False
    # 止盈线，用户自定义的变量，可以被handle_data使用
    portfolio_stop_win = 5.0
    # 用户自定义变量，记录下是否已经触发止盈
    stop_win_triggered = False
    gateway_name: str = None
    # security: Security = None
    bar: Bar = None
    pre_indicator: pd.Series = None  # 日维度指标
    session_indicator: pd.Series = None  # 当前交易日


@dataclass
class TradingOrderParam:
    security: Security = None
    price: float = 0
    quantity: float = 0
    direction: Direction = None
    offset: Offset = None
    order_type: OrderType = None
    time_in_force: OrderTimeInForce = None,
    new_client_order_id: str = ""
    gateway_name: str = ""


class GridTradingStrategy(BaseStrategy, ABC):
    """
    策略说明（B站）
    参数组合1：
    1.交易标的
    2.投入资金
    3.间隔模式

    4.间隔距离
    5.向上格子数
    6.向下格子数

    参数组合2：
    1.交易标的
    2.投入资金
    3.间隔模式

    4.格子总数
    5.网格上轨
    6.网格下轨

    每次有bar事件过来：
    1.撤销委托（网格上轨单和网格下轨单，其中一个成交，另一个要撤销）
    2.更新持仓格子数
    3.更新持仓成本
    4.更新盈亏

    流程：
    1.初始化时根据现在的价格生成网格交易单（2单），提交限价单直到触发。（注：配合技术指标确认什么时候开始首次初始化网格单）
    2.有bar事件时校验上一次网格交易订单状态：如果其中一个交易单成交，撤销另一个交易单，并生成下一个网格交易单（update_order）
    3.回测模式下（不支持限价单）：
    """
    quantity_precision = 0  # 数量精度（ETF数量精度2，最小数量0.01）
    price_precision = 2  # 价格精度

    grid_dict = {}  # 网格参数（静态缓存）
    account_dict = {}  # 网格状态（动态缓存）

    def __init__(self,
                 securities: Dict[str, List[Stock]],
                 strategy_account: str,
                 strategy_version: str,
                 init_strategy_account_balance: Dict[str, AccountBalance],
                 init_strategy_position: Dict[str, Position],
                 engine: Engine,
                 **kwargs
                 ):
        super().__init__(
            securities=securities,
            strategy_account=strategy_account,
            strategy_version=strategy_version,
            init_strategy_account_balance=init_strategy_account_balance,
            init_strategy_position=init_strategy_position,
            engine=engine,
            **kwargs
        )
        # security list
        self.securities = securities
        # execution engine
        self.engine = engine
        # portfolios
        # self.portfolios = engine.portfolios
        self.is_backtest = False
        # For simulation/live trading, set the waiting time > 0
        self.sleep_time = 0
        self.gateway_name = None
        self.pre_pair_orders = {}  # 前配对新鲜
        for gateway_name in self.securities.keys():
            self.gateway_name = gateway_name
            self.pre_pair_orders[gateway_name] = {}

        if engine.gateways[self.gateway_name].trade_mode != TradeMode.BACKTEST:
            self.sleep_time = 3
        else:
            self.is_backtest = True

        self.ohlcv: Dict[Security, List] = {}

        self.money = 100000
        self.id_prefix = "grid_trading_strategy_"
        self.interval_mode = Interval_mode.GS  # 间隔模式（AS表示等差，GS表示等比）
        self.interval = 0.02  # 网格间隔
        self.num_steps_up = 5  # 向上网格数量
        self.num_steps_down = 5  # 向下网格数量

        # self.num_steps = 50  # 网格总数
        # self.max_price = 3000
        # self.min_price = 1000

    def init_strategy(self,
                      start: datetime = None,
                      end: datetime = None,
                      ):
        self.ohlcv = {}
        for security in self.securities[self.gateway_name]:
            self.ohlcv[security] = []
            self.pre_pair_orders[self.gateway_name][security.code] = {}

        # 静态缓存
        self.grid_dict = {
            "interval": 0,  # 网格间隔
            "price_central": 0.0,  # 价格中枢(起始价格)
            "one_grid_quantity": 0,  # 每格数量
            "max_price": 0.0,  # 网格上限
            "min_price": 0.0,  # 网格下限
            "grid_down_count": 0,  # 网格向下的次数
            "grid_up_count": 0  # 网格向上的次数
        }

        # 动态缓存
        self.account_dict = {
            "positions_grids": 0,  # 当前持仓格数（正数为多，负数为空）
            "pairing_count": 0,  # 配对次数
            "pair_profit": 0,  # 配对收益
            "positions_cost": 0,  # 持仓成本
            "positions_profit": 0,  # 持仓浮动盈亏
            "pending_prders": [],  # 当前挂单列表
            "up_price": 0.0,  # 上一格价格
            "down_price": 0.0,  # 下一格价格
        }

    def stop(self):
        self.status = False
        # self.stop_del_order()

    def stop_del_order(self, security: Security):
        # 将当前挂单进行清理
        for side in self.account_dict["pending_prders"]:
            pass
            # del_params={
            #     "symbol":self.symbol,
            #     "origClientOrderId":self.id_prefix+side
            # }
            # err = self.engine.cancel_order(orderid=order_id, gateway_name=self.gateway_name)
            # if err:
            #     logger.error(f"Can't cancel order ({order_id}). Error: {err}")
            #     continue

        if self.account_dict["positions_grids"] > 0:
            quantity = self.grid_dict["one_grid_quantity"] * abs(self.account_dict["positions_grids"])
            # SELL
            params = TradingOrderParam(
                security=security,
                price=self.account_dict["down_price"],
                quantity=quantity,
                direction=Direction.SHORT,
                offset=Offset.CLOSE,
                order_type=OrderType.MARKET,
                gateway_name=self.gateway_name,
                new_client_order_id=self.id_prefix + GRID_SIDE_SELL
            )
            self._submit_order(params, GRID_SIDE_SELL)
        elif self.account_dict["positions_grids"] < 0:
            quantity = self.grid_dict["one_grid_quantity"] * abs(self.account_dict["positions_grids"])
            # BUY
            params = TradingOrderParam(
                security=security,
                price=self.account_dict["down_price"],
                quantity=quantity,
                direction=Direction.LONG,
                offset=Offset.OPEN,
                order_type=OrderType.MARKET,
                gateway_name=self.gateway_name,
                new_client_order_id=self.id_prefix + GRID_SIDE_BUY
            )
            self._submit_order(params, GRID_SIDE_BUY)

    def get_down_price(self, price: float) -> float:
        '''计算下一格价格'''
        down_price = None
        if self.interval_mode == Interval_mode.GS:
            down_price = price / (1 + self.grid_dict["interval"])
        elif self.interval_mode == Interval_mode.AS:
            down_price = price - self.grid_dict["interval"]
        return round(down_price, self.price_precision)

    def get_up_price(self, price: float) -> float:
        '''计算上一格价格'''
        if self.interval_mode == Interval_mode.GS:  # 等比
            up_price = price * (1 + self.grid_dict["interval"])
        elif self.interval_mode == Interval_mode.AS:  # 等差
            up_price = price + self.grid_dict["interval"]

        return round(up_price, self.price_precision)

    def get_positions_cost(self):
        '''计算持仓成本'''
        total = 0
        p = self.account_dict["positions_grids"]
        c = self.grid_dict["price_central"]

        if p < 0:
            for i in range(-p):
                c = self.get_up_price(c)
                total += c
        elif p > 0:
            for i in range(p):
                c = self.get_down_price(c)
                total += c
        elif p == 0:
            return 0

        return round(abs(total / p), self.price_precision)

    def get_positions_profit(self, price):
        '''计算持仓浮动盈亏'''
        positions_profit = (price - self.account_dict["positions_cost"]) * self.account_dict["positions_grids"] * \
                           self.grid_dict["one_grid_quantity"]
        return round(positions_profit, self.price_precision)

    def get_max_price(self):
        '''不传max_price时，计算网格最大价格'''
        max_price = 0
        if self.interval_mode == Interval_mode.GS:  # 等比
            max_price = self.grid_dict["price_central"] * (1 + self.grid_dict["interval"]) ** self.num_steps_up
        elif self.interval_mode == Interval_mode.AS:  # 等差
            max_price = self.grid_dict["price_central"] + (self.grid_dict["interval"] * self.num_steps_up)

        return round(max_price, self.price_precision)

    def get_min_price(self):
        '''不传min_price时，计算网格最小价格'''
        min_price = 0
        if self.interval_mode == Interval_mode.GS:
            min_price = self.grid_dict["price_central"] / (1 + self.grid_dict["interval"]) ** self.num_steps_down
        elif self.interval_mode == Interval_mode.AS:
            min_price = self.grid_dict["price_central"] - (self.grid_dict["interval"] * self.num_steps_down)

        return round(min_price, self.price_precision)

    def get_interval(self):
        """
        参数组合2使用
        """
        max_value = self.max_price
        min_value = self.min_price
        num_elements = self.num_steps

        interval = 0
        if self.interval_mode == Interval_mode.GS:
            interval = (max_value / min_value) ** (1 / (num_elements - 1))
        elif self.interval_mode == Interval_mode.AS:
            interval = (max_value - min_value) / (num_elements - 1)
        return round(1 - interval, 6)

    def get_price_central(self, new_price) -> float:
        '''不传interval时，计算price_central'''
        max_value = self.max_price
        min_value = self.min_price
        num_elements = self.num_steps

        if self.interval_mode == Interval_mode.GS:
            interval = (max_value / min_value) ** (1 / (num_elements - 1))
            price_list = [min_value * (interval ** i) for i in range(num_elements)]
        elif self.interval_mode == Interval_mode.AS:
            interval = (max_value - min_value) / (num_elements - 1)
            price_list = [min_value + (interval * i) for i in range(num_elements)]

        price_central = min(price_list, key=lambda x: abs(x - new_price))
        return round(price_central, self.price_precision)

    def get_one_grid_quantity(self):
        """
        资金不变，这样容易资金利用率低
        """
        if self.interval == 0:
            return round(self.money / (self.num_steps) / self.grid_dict["price_central"], self.quantity_precision)
        else:
            return round(self.money / (self.num_steps_up + self.num_steps_down) / self.grid_dict["price_central"],
                         self.quantity_precision)

    def get_pair_profit(self, price, side) -> float:
        if self.interval_mode == Interval_mode.GS:
            if side == GRID_SIDE_SELL:
                pair_profit = (price / (1 + self.grid_dict["interval"])) * self.grid_dict["interval"] * self.grid_dict[
                    "one_grid_quantity"]
            elif side == GRID_SIDE_BUY:
                pair_profit = price * self.grid_dict["interval"] * self.grid_dict["one_grid_quantity"]
        elif self.interval_mode == Interval_mode.AS:
            pair_profit = self.grid_dict["interval"] * self.grid_dict["one_grid_quantity"]
        return pair_profit

    def reset_grid(self, security: Security = None, new_price: float = 0):
        '''破网处理'''
        # 清仓
        params: TradingOrderParam = None
        # 清仓数量
        quantity = self.grid_dict["one_grid_quantity"] * abs(self.account_dict["positions_grids"])
        if self.account_dict["positions_grids"] > 0:  # 如果是多头持仓
            side = "SELL"  # 清仓方向
            params = TradingOrderParam(
                security=security,
                price=new_price,  # 市价单价格为当前的bar价格
                quantity=quantity,
                direction=Direction.SHORT,
                offset=Offset.CLOSE,
                order_type=OrderType.MARKET,
                time_in_force=OrderTimeInForce.GTC,
                new_client_order_id=self.id_prefix + GRID_SIDE_RESET + GRID_SIDE_SELL,
                gateway_name=self.gateway_name,
            )
        elif self.account_dict["positions_grids"] < 0:
            side = "BUY"
            params = TradingOrderParam(
                security=security,
                price=new_price,  # 市价单价格为当前的bar价格
                quantity=quantity,
                direction=Direction.LONG,
                offset=Offset.OPEN,
                order_type=OrderType.MARKET,
                time_in_force=OrderTimeInForce.GTC,
                new_client_order_id=self.id_prefix + GRID_SIDE_RESET + GRID_SIDE_BUY,
                gateway_name=self.gateway_name,
            )

        if params:
            order_id = self._submit_order(params, GRID_SIDE_RESET)
            if not order_id:
                logger.error(f"reset_grid fail. deal_order. params= {params}")
            order = self._listen_order_deals_for_portfolios(order_id, self.gateway_name)
            if order.status == OrderStatus.FILLED or OrderStatus.PART_FILLED:
                logger.info(f"reset_grid->_listen_order_deals_for_portfolios order={order}", caller=self)

        # 计算清仓盈亏
        if new_price <= 0:
            logger.error("reset_grid:new_price is 0.")
            return

        self.account_dict["positions_profit"] = self.get_positions_profit(new_price)
        self.account_dict["positions_grids"] = 0
        logger.info(f"网格策略发生破网\n 运行结果{self.account_dict}")

        # 重置网格参数或停止策略
        self._init_grid_strategy(security, new_price)
        # self.stop()

    def _init_grid_strategy(self, security: Security = None, new_price: float = 0):
        if not security:
            return

        self.grid_dict["grid_down_count"] = 0
        self.grid_dict["grid_up_count"] = 0

        if self.interval == 0:  # 参数组合2
            self.grid_dict["interval"] = self.get_interval()
            self.grid_dict["price_central"] = self.get_price_central(new_price)
            self.grid_dict["one_grid_quantity"] = self.get_one_grid_quantity()
            self.grid_dict["max_price"] = self.max_price
            self.grid_dict["min_price"] = self.min_price
            self.account_dict["up_price"] = self.get_up_price(self.grid_dict["price_central"])
            self.account_dict["down_price"] = self.get_down_price(self.grid_dict["price_central"])
        else:
            # 参数组合1
            self.grid_dict["interval"] = self.interval
            self.grid_dict["price_central"] = new_price
            self.grid_dict["one_grid_quantity"] = self.get_one_grid_quantity()
            self.grid_dict["max_price"] = self.get_max_price()
            self.grid_dict["min_price"] = self.get_min_price()
            self.account_dict["up_price"] = self.get_up_price(self.grid_dict["price_central"])
            self.account_dict["down_price"] = self.get_down_price(self.grid_dict["price_central"])

        # 初始化委托单
        down_params = TradingOrderParam(
            security=security,
            price=self.account_dict["down_price"],
            quantity=self.grid_dict["one_grid_quantity"],
            direction=Direction.LONG,
            offset=Offset.OPEN,
            order_type=OrderType.LIMIT,
            time_in_force=OrderTimeInForce.GTC,
            gateway_name=self.gateway_name,
            new_client_order_id=self.id_prefix + GRID_SIDE_BUY,
        )
        down_orderid = self._submit_order(down_params, GRID_SIDE_BUY)

        # 初始化网格，没有卖单
        # up_params = TradingOrderParam(
        #     security=security,
        #     price=self.account_dict["up_price"],
        #     quantity=self.grid_dict["one_grid_quantity"],
        #     direction=Direction.SHORT,
        #     offset=Offset.CLOSE,
        #     order_type=OrderType.LIMIT,
        #     time_in_force=OrderTimeInForce.GTC,
        #     gateway_name=self.gateway_name,
        #     new_client_order_id=self.id_prefix + GRID_SIDE_SELL
        # )
        # up_orderid = self._submit_order(up_params)

        if down_orderid != "":
            self.account_dict["pending_prders"] = ["buy"]

    def calculate_session_indicator(self, bar: Bar = None) -> pd.Series:
        data = pd.Series(dtype='float64')
        security = bar.security
        # Collect bar data (only keep latest 120 records)
        self.ohlcv[security].append(bar)
        if len(self.ohlcv[security]) > 120:
            self.ohlcv[security].pop(0)

        return data

    async def on_bar(self, quote_data: Dict[str, Dict[Security, Bar]]):
        logger.info("-" * 30 + "Enter on_bar" + "-" * 30)
        logger.info(quote_data)
        gateway_name = self.gateway_name
        if gateway_name not in quote_data:
            return

        # check balance
        balance = self.get_strategy_account_balance(gateway_name)
        logger.info(f"strategy_balance={balance}")
        # broker_balance = self.engine.get_broker_balance(
        #     gateway_name=gateway_name)
        # logger.info(f"{broker_balance}")

        # check position
        the_position = self.get_strategy_position(gateway_name)
        # logger.info(f"positions = {positions}")

        # broker_positions = self.engine.get_all_broker_positions(
        #     gateway_name=gateway_name)
        # logger.info(f"{broker_positions}")

        # send orders
        for security in quote_data[gateway_name]:
            if security not in self.securities[gateway_name]:
                continue

            bar = quote_data[gateway_name][security]
            calendar = xcals.get_calendar("XNYS")
            if self.is_backtest is False and calendar.is_open_on_minute(
                    (bar.datetime + timedelta(hours=-8)).strftime("%Y-%m-%d %H:%M")) is False:
                continue

            cur_price = bar.close
            logger.info("is_session is True,bar = ", bar)
            # 处理实时指标
            session_indicator = self.calculate_session_indicator(bar)
            # if session_indicator.empty is True or pd.isna(session_indicator['ATR']):
            #     continue

            if len(self.account_dict["pending_prders"]) == 0:
                new_price = float(bar.close)
                self._init_grid_strategy(security, new_price)
            else:
                '''
                1.检测上一次网格的订单状态：如果上一次网格其中一个订单成交，则更新下一次网格
                2.回测模式下：先校验价格，再检测订单状态
                '''
                side = ""
                price = 0.0
                order: Order = None

                for k, pre_orderid in self.pre_pair_orders[self.gateway_name][security.code].items():
                    is_check_order = True
                    order = self.engine.get_order(orderid=pre_orderid, gateway_name=gateway_name)
                    if self.is_backtest:
                        if (k == GRID_SIDE_BUY and cur_price > order.price) or (
                                k == GRID_SIDE_SELL and cur_price < order.price):
                            is_check_order = False

                    if is_check_order:
                        order = self._listen_order_deals_for_portfolios(pre_orderid, gateway_name)
                        if order.status == OrderStatus.FILLED or OrderStatus.PART_FILLED:
                            side = k
                            price = order.filled_avg_price
                            break

                if not side:
                    if cur_price >= self.grid_dict["max_price"] or cur_price <= self.grid_dict["min_price"]:
                        # 破网
                        # 前一个订单没有触发破网的时候
                        self.reset_grid(security, cur_price)
                        logger.warn("reset_grid bar info", security=security, price=cur_price,
                                    max_price=self.grid_dict["max_price"],
                                    min_price=self.grid_dict["min_price"], caller=self)
                    return

                if price >= self.grid_dict["max_price"] or price <= self.grid_dict["min_price"]:
                    logger.warn("reset_grid")
                self._update_order(security, side, price)
        return

    def _real_price(self, cur_price: float = None, gateway_price: float = None) -> float:
        if gateway_price is None:
            gateway_price = cur_price
        return gateway_price if self.is_backtest else cur_price

    def _update_order(self, security: Security = None, side: str = None, price: float = 0.0):
        """
        side:挂单成交的方向
        price:挂单成交的价格
        cancel_orderid:两个挂单，另一个挂单要撤销

        tips:
        1.允许是否资金可以购买
        """

        cancel_orderid = ""
        if side == GRID_SIDE_BUY and GRID_SIDE_SELL in self.pre_pair_orders[self.gateway_name][security.code]:
            cancel_orderid = self.pre_pair_orders[self.gateway_name][security.code][GRID_SIDE_SELL]
        elif side == GRID_SIDE_SELL and GRID_SIDE_BUY in self.pre_pair_orders[self.gateway_name][security.code]:
            cancel_orderid = self.pre_pair_orders[self.gateway_name][security.code][GRID_SIDE_BUY]

        # 网格单更新，则上一次的字典更新
        self.pre_pair_orders[self.gateway_name][security.code] = {}
        # 撤销委托，撤销之前的订单
        if side == GRID_SIDE_BUY:  # buy
            self.account_dict["positions_grids"] += 1
            # self.grid_dict["grid_down_count"] += 1  # stock有效
            # 撤销订单的参数字典
        elif side == GRID_SIDE_SELL:  # sell
            self.account_dict["positions_grids"] -= 1
            # self.grid_dict["grid_up_count"] += 1  # stock有效

        if cancel_orderid:
            # 网格配对，将另外一个订单撤销撤销订单
            err = self.engine.cancel_order(orderid=cancel_orderid, gateway_name=self.gateway_name)
            if err:
                logger.error(f"Can't cancel order ({cancel_orderid}). Error: {err}")
                return
            # 将挂单列表设置为空
            self.account_dict["pending_prders"] = []
            logger.info(f"Successfully cancel order ({cancel_orderid}).")

        # 更新account_dict
        self.account_dict["positions_cost"] = self.get_positions_cost()
        self.account_dict["positions_profit"] = self.get_positions_profit(price)
        if side == GRID_SIDE_BUY and self.account_dict["positions_grids"] < 0:
            self.account_dict["pairing_count"] += 1
            self.account_dict["pair_profit"] += self.get_pair_profit(price, side)
        elif side == GRID_SIDE_SELL and self.account_dict["positions_grids"] > 0:
            self.account_dict["pairing_count"] += 1
            self.account_dict["pair_profit"] += self.get_pair_profit(price, side)

        # 新建委托
        if price >= self.grid_dict["max_price"] or price <= self.grid_dict["min_price"]:
            # 破网
            self.reset_grid(security, price)
            logger.warn("reset_grid info", security=security, price=price, max_price=self.grid_dict["max_price"],
                        min_price=self.grid_dict["min_price"], caller=self)
            return
        else:
            self.account_dict["down_price"] = self.get_down_price(price)
            self.account_dict["up_price"] = self.get_up_price(price)

            down_params = TradingOrderParam(
                security=security,
                price=self.account_dict["down_price"],
                quantity=self.grid_dict["one_grid_quantity"],
                direction=Direction.LONG,
                offset=Offset.OPEN,
                order_type=OrderType.LIMIT,
                time_in_force=OrderTimeInForce.GTC,
                gateway_name=self.gateway_name,
                new_client_order_id=self.id_prefix + GRID_SIDE_BUY
            )
            down_orderid = self._submit_order(down_params, GRID_SIDE_BUY)

            if self.account_dict["positions_grids"] > 0:
                up_params = TradingOrderParam(
                    security=security,
                    price=self.account_dict["up_price"],
                    quantity=self.grid_dict["one_grid_quantity"],
                    direction=Direction.SHORT,
                    offset=Offset.CLOSE,
                    order_type=OrderType.LIMIT,
                    time_in_force=OrderTimeInForce.GTC,
                    gateway_name=self.gateway_name,
                    new_client_order_id=self.id_prefix + GRID_SIDE_SELL
                )
                up_orderid = self._submit_order(up_params, GRID_SIDE_SELL)
                if not down_orderid or not up_orderid:
                    logger.error("update_order down or up fail.")

            self.account_dict["pending_prders"] = ["buy", "sell"]

    def _submit_order(self, param: TradingOrderParam = None, side: str = "") -> str:
        # 处理订单
        order_id = self.engine.send_order(param.security,
                                          param.price,
                                          param.quantity,
                                          param.direction,
                                          param.offset,
                                          param.order_type,
                                          param.time_in_force,
                                          param.gateway_name,
                                          param.new_client_order_id)
        if not order_id:
            logger.error("Fail to submit order")
            return ""
        # 缓存网格配对的orderid
        if side == GRID_SIDE_BUY:
            self.pre_pair_orders[param.gateway_name][param.security.code][GRID_SIDE_BUY] = order_id
        elif side == GRID_SIDE_SELL:
            self.pre_pair_orders[param.gateway_name][param.security.code][GRID_SIDE_SELL] = order_id

        return order_id

    def _listen_order_deals_for_portfolios(self, orderid: str, gateway_name: str) -> typing.Optional[Order]:
        """
        监听订单交易变化并更新持仓收益
        """
        if orderid == "":
            return None

        order = None
        for i in range(0, 10):
            order = self.engine.get_order(
                orderid=orderid, gateway_name=gateway_name)
            if not order or order.status == OrderStatus.UNKNOWN:
                sleep(0.02)
                continue
            break

        if not order:
            logger.error("_listen_order_deals_for_portfolios->order is None.")
            return None

        if order.status != OrderStatus.FILLED and order.status != OrderStatus.PART_FILLED:
            return

        # 处理交易
        deals = self.engine.find_deals_with_orderid(
            orderid, gateway_name=gateway_name)
        for deal in deals:
            if not deal:
                continue
            # 更新持仓
            try:
                self.portfolios[gateway_name].update(deal)
            except:
                logger.exception("_listen_order_deals_for_portfolios fail.", deal=deal, caller=self)

        # 记录操作
        order_instruct = TradingOrderParam(
            security=order.security,
            price=order.price,
            quantity=order.quantity,
            direction=order.direction,
            offset=order.offset,
            gateway_name=self.gateway_name,
        )
        self.on_action(gateway_name, order_instruct)
        return order

    def on_order(self, gateway_name: str = None, order_instruct: dict = None):
        logger.info(f"Submit order: \n{order_instruct}")
        # 写入数据库
        # try:
        #     if self.is_backtest is False:
        #         from app.domain.order import OrderService
        #         order_service = OrderService(engine=self.engine)
        #         order_service.create_order(order=order, account_id=0,
        #                                    strategy_name=self.strategy_account + self.strategy_version)
        # except:
        #     logger.exception("strategy create_order fail.", order=order, caller=self)

    def on_action(self, gateway_name: str = None, param: TradingOrderParam = None):
        if param is None:
            return

        security = param.security
        # 更新操作
        self.update_action(gateway_name, action=dict(
            gw=gateway_name,
            sec=security.code,
            side=param.direction.value,
            offset=param.offset.value,
            price=param.price,
            qty=param.quantity,
        ))
        plugins = self.engine.get_plugins()
        if "dingtalk" in plugins and not self.is_backtest:
            dingtalk_bot = plugins["dingtalk"].bot
            dingtalk_bot.send_text(f"{datetime.now()} gateway_name:{gateway_name}, has been sent: {param}")
        logger.info(f"on_action = {param}")
