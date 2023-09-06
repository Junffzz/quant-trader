#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABC
from time import sleep
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import pandas_ta as ta
import exchange_calendars as xcals

from functools import reduce
from app.domain.balance import AccountBalance
from app.domain.position import Position, PositionData
from app.constants import Direction, Offset, OrderSide, OrderType, TradeMode, OrderStatus
from app.domain.data import Bar
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
    """
    quantity_pricision = 0  # 数量精度（ETF数量精度2，最小数量0.01）
    price_pricision = 0  # 价格精度

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
        for gateway_name in self.securities.keys():
            self.gateway_name = gateway_name

        if engine.gateways[self.gateway_name].trade_mode != TradeMode.BACKTEST:
            self.sleep_time = 5
        else:
            self.is_backtest = True

        self.ohlcv: Dict[Security, List] = {}

        self.interval_mode = Interval_mode.GS  # 间隔模式（AS表示等差，GS表示等比）
        self.interval = 0.01  # 网格间隔
        self.num_steps_up = 5  # 向上网格数量
        self.num_steps_down = 5  # 向下网格数量

    def init_strategy(self,
                      start: datetime = None,
                      end: datetime = None,
                      ):
        self.ohlcv = {}
        for security in self.securities[self.gateway_name]:
            self.ohlcv[security] = []

        # 静态缓存
        self.grid_dict = {
            "interval": 0,  # 网格间隔
            "price_central": 0,  # 价格中枢
            "one_grid_quantity": 0,  # 每格数量
            "max_price": 0,  # 网格上限
            "min_price": 0,  # 网格下限
        }

        # 动态缓存
        self.account_dict = {
            "positions_grids": 0,  # 当前持仓格数（正数为多，负数为空）
            "pairing_count": 0,  # 配对次数
            "pair_profit": 0,  # 配对收益
            "positions_cost": 0,  # 持仓成本
            "positions_profit": 0,  # 持仓浮动盈亏
            "pending_prders": [],  # 当前挂单列表
            "up_price": 0,  # 上一格价格
            "down_price": 0,  # 下一格价格
        }

    def get_down_price(self, price):
        '''计算下一格价格'''
        down_price = None
        if self.interval_mode == Interval_mode.GS:
            down_price = price / (1 + self.grid_dict["interval"])
        elif self.interval_mode == Interval_mode.AS:
            down_price = price - self.grid_dict["interval"]
        return round(down_price, self.price_pricision)

    def get_up_price(self, price):
        '''计算上一格价格'''
        if self.interval_mode == Interval_mode.GS:
            up_price = price * (1 + self.grid_dict["interval"])
        elif self.interval_mode == Interval_mode.AS:
            up_price = price + self.grid_dict["interval"]

        return round(up_price, self.price_pricision)

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

        return round(abs(total / p), self.price_pricision)

    def get_positions_profit(self, price):
        '''计算持仓浮动盈亏'''
        positions_profit = (price - self.account_dict["positions_cost"]) * self.account_dict["positions_grids"] * \
                           self.grid_dict[""]
        return round(positions_profit, self.price_pricision)

    def get_max_price(self):
        '''不传max_price时，计算网格最大价格'''
        max_price = 0
        if self.interval_mode == Interval_mode.GS:
            max_price = self.grid_dict["price_central"] * (1 + self.grid_dict["interval"]) ** self.num_steps_up
        elif self.interval_mode == Interval_mode.AS:
            max_price = self.grid_dict["price_central"] + (self.grid_dict["interval"] * self.num_steps_up)

        return round(max_price, self.price_pricision)

    def get_min_price(self):
        '''不传min_price时，计算网格最小价格'''
        min_price = 0
        if self.interval_mode == Interval_mode.GS:
            min_price = self.grid_dict["price_central"] / (1 + self.grid_dict["interval"]) ** self.num_steps_down
        elif self.interval_mode == Interval_mode.AS:
            min_price = self.grid_dict["price_central"] - (self.grid_dict["interval"] * self.num_steps_down)

        return round(min_price, self.price_pricision)

    def get_interval(self):
        max_value = self.max_price
        min_value = self.min_price
        num_elements = self.num_steps

        interval = 0
        if self.interval_mode == Interval_mode.GS:
            interval = (max_value / min_value) ** (1 / (num_elements - 1))
        elif self.interval_mode == Interval_mode.AS:
            interval = (max_value - min_value) / (num_elements - 1)
        return round(1 - interval, 6)

    def get_price_central(self, new_price):
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
        return round(price_central, self.price_pricision)

    def get_one_grid_quantity(self):
        if self.interval == 0:
            return round(self.money / (self.num_steps) / self.grid_dict["price_central"], self.quantity_pricision)
        else:
            return round(self.money / (self.num_steps_up + self.num_steps_down) / self.grid_dict["price_central"],
                         self.quantity_pricision)

    def get_pair_profit(self, price, side):
        if self.interval_mode == Interval_mode.GS:
            if side == "SELL":
                pair_profit = (price / (1 + self.grid_dict["interval"])) * self.grid_dict["interval"] * self.grid_dict[
                    "one_grid_quantity"]
            elif side == "BUY":
                pair_profit = price * self.grid_dict["interval"] * self.grid_dict["one_grid_quantity"]
        elif self.interval_mode == Interval_mode.AS:
            pair_profit = self.grid_dict["interval"] * self.grid_dict["one_grid_quantity"]
        return pair_profit

    def calculate_session_indicator(self, bar: Bar = None) -> pd.Series:
        data = pd.Series(dtype='float64')
        security = bar.security
        # Collect bar data (only keep latest 120 records)
        self.ohlcv[security].append(bar)
        if len(self.ohlcv[security]) > 120:
            self.ohlcv[security].pop(0)

        new_price = float(bar.close)
        if self.interval == 0:  # 参数组合2
            self.grid_dict["interval"] = self.get_interval()
            self.grid_dict["price_central"] = self.get_price_central(new_price)
            self.grid_dict["one_grid_quantity"] = self.get_one_grid_quantity()
            self.grid_dict["max_price"] = self.max_price
            self.grid_dict["min_price"] = self.min_price
            self.account_dict["up_price"] = self.get_up_price(self.grid_dict["price_central"])
            self.account_dict["down_price"] = self.get_down_price(self.grid_dict["price_central"])
        else:
            self.grid_dict["interval"] = self.interval
            self.grid_dict["price_central"] = new_price
            self.grid_dict["one_grid_quantity"] = self.get_one_grid_quantity()
            self.grid_dict["max_price"] = self.get_max_price()
            self.grid_dict["min_price"] = self.get_min_price()
            self.account_dict["up_price"] = self.get_up_price(self.grid_dict["price_central"])
            self.account_dict["down_price"] = self.get_down_price(self.grid_dict["price_central"])

        return data

    def _try_buy(self, ctx: TradingContext = None):
        """
        入场
        """
        if ctx is None:
            return

        gateway_name = ctx.gateway_name
        bar = ctx.bar
        security = bar.security
        if gateway_name is None or security is None or bar is None:
            return

        ohlc = ctx.pre_indicator
        cur_price = bar.open  # 以开盘价下单
        order_instruct = {}

        all_positions = ctx.position.get_all_positions()
        position_num = 0  # 多仓
        for pos in all_positions:
            if pos.direction == Direction.LONG:
                position_num += 1
        if position_num >= self.max_position:
            return

        long_position = ctx.position.get_position(
            security=security, direction=Direction.LONG)
        if long_position:
            return

        grid_region_long = [0.005] * ctx.grid_amount  # 多头每格价格跌幅(网格密度)
        grid_region_short = [0.005] * ctx.grid_amount  # 空头每格价格涨幅(网格密度)
        grid_volume_long = [i for i in range(ctx.grid_amount + 1)]  # 多头每格持仓手数
        grid_volume_short = [i for i in range(ctx.grid_amount + 1)]  # 空头每格持仓手数
        grid_prices_long = [reduce(lambda p, r: p * (1 - r), grid_region_long[:i], ctx.base_price) for i in
                            range(ctx.grid_amount + 1)]  # 多头每格的触发价位列表
        grid_prices_short = [reduce(lambda p, r: p * (1 + r), grid_region_short[:i], ctx.base_price) for i in
                             range(ctx.grid_amount + 1)]  # 空头每格的触发价位列表
        print("策略开始运行, 起始价位: %f, 多头每格持仓手数:%s, 多头每格的价位:%s, 空头每格的价位:%s" % (
            ctx.base_price, grid_volume_long, grid_prices_long, grid_prices_short))

        if ctx.grid_layer > 0 or cur_price <= grid_prices_long[1]:  # 是多头方向
            while True:
                # 如果当前档位小于最大档位,并且最新价小于等于下一个档位的价格: 则设置为下一档位对应的手数后进入下一档位层次
                if ctx.grid_layer < ctx.grid_amount and cur_price <= grid_prices_long[ctx.grid_layer + 1]:
                    quantity = grid_volume_long[ctx.grid_layer + 1]
                    print("最新价: %f, 进入: 多头第 %d 档" % (cur_price, ctx.grid_layer + 1))
                    ctx.grid_layer = ctx.grid_layer + 1
                    continue

                # 如果最新价大于当前档位的价格: 则回退到上一档位
                if cur_price > grid_prices_long[ctx.grid_layer]:
                    # 从下一档位回退到当前档位后, 设置回当前对应的持仓手数
                    quantity = grid_volume_long[ctx.grid_layer + 1]
                    print("最新价: %f, 回退到: 多头第 %d 档" % (cur_price, ctx.grid_layer))
                    return

        if ohlc['ema_fork_signal'] == 1:
            quantity = self.get_order_quantity(bar.close)
            if quantity > 0:
                order_instruct = dict(
                    security=security,
                    price=cur_price,
                    quantity=quantity,  # 购买数量
                    direction=Direction.LONG,
                    offset=Offset.OPEN,
                    order_type=OrderType.MARKET,
                    gateway_name=ctx.gateway_name,
                )
        return order_instruct

    def _try_sell(self, ctx: TradingContext = None):
        """
        止损位：
        1.macd<-0.5
        2.价格低于买入价5%
        """
        gateway_name = ctx.gateway_name
        bar = ctx.bar
        security = bar.security
        if gateway_name is None or security is None or bar is None:
            return

        code = security.code
        turtle_ctx = self.turtle_ctxs[code]
        cur_price = bar.open  # 以开盘价下单
        ohlc = ctx.pre_indicator
        long_position = ctx.position.get_position(
            security=security, direction=Direction.LONG)

        order_instruct = {}
        if not long_position:
            return order_instruct

        order_instruct = dict(
            security=security,
            price=cur_price,
            quantity=quantity,  # 购买数量
            direction=direction,
            offset=offset,
            order_type=OrderType.MARKET,
            gateway_name=ctx.gateway_name,
        )

        return order_instruct

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

            logger.info("is_session is True,bar = ", bar)
            # 处理实时指标
            session_indicator = self.calculate_session_indicator(bar)
            if session_indicator.empty is True or pd.isna(session_indicator['ATR']):
                continue

            code = security.code
            pre_date = calendar.previous_session(bar.datetime.strftime("%Y-%m-%d"), True)

            context = TradingContext(
                position=the_position,
                # long_position=long_position,
                # sort_position=short_position,
                gateway_name=gateway_name,
                bar=bar,
                # pre_indicator=daily_indicator,
                session_indicator=session_indicator
            )

            # 头寸规模单位
            atr_volume = session_indicator['ATR'] * security.lot_size  # 一个市场中代表着每份合约有1ATR变动幅度的美元金额
            capital_control_ratio = 0.01
            NLot = int(balance.cash * capital_control_ratio / atr_volume)

            # self.turtle_ctxs[code].unit = NLot

            order_instruct = {}
            order_instruct = self._try_buy(context)
            if not order_instruct:
                order_instruct = self._try_sell(context)

            if not order_instruct:
                continue

            self.on_order(gateway_name, order_instruct)
            self.on_action(gateway_name, order_instruct)

    def _real_price(self, cur_price: float = None, gateway_price: float = None) -> float:
        if gateway_price is None:
            gateway_price = cur_price
        return gateway_price if self.is_backtest else cur_price

    def update_order(self, order: Order = None):
        if order is None:
            return

        side = ""
        side = order.direction
        price = order.price
        order_id = order.orderid
        # 撤销委托，撤销之前的订单
        if order.direction == Direction.LONG:  # buy
            side = "BUY"
            self.account_dict["positions_grids"] += 1
            # 撤销订单的参数字典
        elif order.direction == Direction.SHORT:  # sell
            side = "SELL"
            self.account_dict["positions_grids"] -= 1

        # 网格配对，将另外一个订单撤销撤销订单
        err = self.engine.cancel_order(orderid=order_id, gateway_name=self.gateway_name)
        if err:
            logger.error(f"Can't cancel order ({order_id}). Error: {err}")
            return
        logger.info(f"Successfully cancel order ({order_id}).")

        # 更新account_dict
        self.account_dict["positions_cost"] = self.get_positions_cost()
        self.account_dict["positions_profit"] = self.get_positions_profit(price)
        if side == "BUY" and self.account_dict["positions_grids"] < 0:
            self.account_dict["pairing_count"] += 1
            self.account_dict["pair_profit"] += self.get_pair_profit(price, side)
        elif side == "SELL" and self.account_dict["positions_grids"] > 0:
            self.account_dict["pairing_count"] += 1
            self.account_dict["pair_profit"] += self.get_pair_profit(price, side)

        # 新建委托
        if price >= self.grid_dict["max_price"] or price <= self.grid_dict["min_price"]:
            # 破网
            self.reset_grid(side)
        else:
            self.account_dict["down_price"] = self.get_down_price(price)
            self.account_dict["up_price"] = self.get_up_price(price)

            down_params = {
                "symbol": self.symbol,
                "side": "BUY",
                "type": "LIMIT",
                "quantity": self.grid_dict["one_grid_quantity"],
                "price": self.account_dict["down_price"],
                "newClientOrderId": self.id_prefix + "buy",
                "timeInForce": "GTC"
            }
            down_params = dict(
                security=order.security,
                price=order.price,
                quantity=order.quantity,  # 购买数量
                direction=Direction.LONG,
                offset=Offset.OPEN,
                order_type=OrderType.MARKET,
                gateway_name=self.gateway_name,
            )
            self.deal_order()
            up_params = {
                "symbol": self.symbol,
                "side": "SELL",
                "type": "LIMIT",
                "quantity": self.grid_dict["one_grid_quantity"],
                "price": self.account_dict["up_price"],
                "newClientOrderId": self.id_prefix + "sell",
                "timeInForce": "GTC"
            }
        # todo：下单请求(两个都下单)

    def on_order(self, gateway_name: str = None, order_instruct: dict = None):
        logger.info(f"Submit order: \n{order_instruct}")
        # 处理订单
        order_id = self.engine.send_order(**order_instruct)
        if order_id == "":
            logger.info("Fail to submit order")
            return

        sleep(self.sleep_time)
        order = self.engine.get_order(
            orderid=order_id, gateway_name=gateway_name)
        logger.info(f"Order ({order_id}) has been sent: {order}")
        # 处理交易
        deals = self.engine.find_deals_with_orderid(
            order_id, gateway_name=gateway_name)
        for deal in deals:
            # 更新持仓
            self.portfolios[gateway_name].update(deal)

        if order.status == OrderStatus.FILLED:
            logger.info(f"Order ({order_id}) has been filled.")
        else:
            err = self.engine.cancel_order(orderid=order_id, gateway_name=gateway_name)
            if err:
                logger.error(f"Can't cancel order ({order_id}). Error: {err}")
                return
            logger.info(f"Successfully cancel order ({order_id}).")

        # 写入数据库
        try:
            if self.is_backtest is False:
                from app.domain.order import OrderService
                order_service = OrderService(engine=self.engine)
                order_service.create_order(order=order, account_id=0,
                                           strategy_name=self.strategy_account + self.strategy_version)
        except:
            logger.exception("strategy create_order fail.", order=order, caller=self)

    def on_action(self, gateway_name: str = None, order_instruct: dict = None):
        if order_instruct is None:
            return

        security = order_instruct.get("security")
        # 更新操作
        self.update_action(gateway_name, action=dict(
            gw=gateway_name,
            sec=security.code,
            side=order_instruct.get("direction").value,
            offset=order_instruct.get("offset").value,
        ))
        plugins = self.engine.get_plugins()
        if "dingtalk" in plugins and not self.is_backtest:
            dingtalk_bot = plugins["dingtalk"].bot
            dingtalk_bot.send_text(f"{datetime.now()} gateway_name:{gateway_name}, has been sent: {order_instruct}")
        logger.info(f"on_action = {order_instruct}")
