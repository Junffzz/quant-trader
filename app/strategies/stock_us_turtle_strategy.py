from abc import ABC
from time import sleep
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass

import pandas as pd
import pandas_ta as ta

from multiprocessing import Process, freeze_support

import exchange_calendars as xcals

from app.domain.balance import AccountBalance
from app.domain.position import Position, PositionData
from app.constants import Direction, Offset, OrderSide, OrderType, TradeMode, OrderStatus
from app.domain.data import Bar
from app.domain.engine import Engine
from app.domain.security import Stock, Security
from app.utils import logger
from app.strategies.base_strategy import BaseStrategy
from app.utils.tasks import SingleTask, LoopRunTask

@dataclass
class TurtleContext:
    sys1_entry = 20  # 通道1周期
    sys2_entry = 55  # 通道2周期
    atr_period = 20  # art波幅周期
    last_buy_price = 0  # 上一次买入价
    hold_flag = False  # 是否持有头寸标志
    limit_unit = 3  # 限制最多买入的单元数
    unit = 0
    add_time = 0  # 买入次数
    max_risk_ratio = 0.5  # 最高风险度


@dataclass
class TradeStrategyContext:
    """交易信号上下文"""
    long_position: PositionData = None
    sort_position: PositionData = None
    gateway_name: str = None
    bar: Bar = None
    pre_session_data: pd.Series = None  # 前日维度指标
    session_indicator: pd.Series = None  # 当前交易日


class StockUSTurtleStrategy(BaseStrategy, ABC):
    """
    海龟交易策略
    """

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
        self._dKline_df = pd.DataFrame()  # pd.DataFrame
        # security list
        self.securities = securities
        # execution engine
        self.engine = engine
        # portfolios
        # self.portfolios = engine.portfolios  # engine的投资组合覆盖策略的投资组合
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
        # 海龟参数
        self.turtle_ctxs: Dict[str, TurtleContext] = {}

    def init_strategy(self):
        for security in self.engine.gateways[self.gateway_name].securities:
            self.ohlcv[security] = []
            # 海龟上下文
            self.turtle_ctxs[security.code]: TurtleContext = TurtleContext()

        SingleTask.run(self.daily_indicator_callback)
        # 注册定时任务
        if self.is_backtest is False:
            LoopRunTask.register(self.daily_indicator_callback, 60 * 60)

    async def daily_indicator_callback(self, *args, **kwargs):
        """
        加载k线策略
        """
        from app.domain.stores.security_market_storer import SecurityMarketStorer
        storer = SecurityMarketStorer(local=False)

        gateway_name = self.gateway_name
        if self.is_backtest:
            data = self.engine.gateways[gateway_name].get_kline_data(self.securities[gateway_name])
        else:
            today = datetime.today()
            start = today - timedelta(120)  # 120日之前
            end = today
            data = storer.get_kline_data(self.securities[gateway_name], start=start, end=end)
        for security in self.securities[gateway_name]:
            df = data.loc[data['code'] == security.code].sort_values('time_key')
            self.dispatch_kline_indicator(security, df)
            self._dKline_df = pd.concat([self._dKline_df, df], ignore_index=True)

        # 重建索引
        self._dKline_df.set_index(['code', 'time_key'], inplace=True)
        self._dKline_df = self._dKline_df.sort_index()

        return

    def dispatch_kline_indicator(self, security: Security = None, df: pd.DataFrame = None):
        tech_strategy = ta.Strategy(
            name="Momo and Volatility",
            description="SMA 50,200, BBANDS, RSI, MACD and Volume SMA 20",
            ta=[
                {"kind": "ema", "length": 10},
                {"kind": "ema", "length": 20},
                {"kind": "ema", "length": 60},
                {"kind": "kdj", "col_names": ("KDJ_K", "KDJ_D", "KDJ_J")},
                {"kind": "kdj", "signal": 6, "col_names": ("KD_MACD_K", "KD_MACD_D", "KD_MACD_J")},
                {"kind": "macd", "asmode": False, "col_names": ("MACD_DIF", "MACD", "MACD_DEA")},
            ]
        )
        freeze_support()
        df.ta.strategy(tech_strategy)

        n1 = self.turtle_ctxs[security.code].sys1_entry
        n2 = self.turtle_ctxs[security.code].sys2_entry
        # 唐奇安通道
        df['don_high_n1'] = df['high'].rolling(n1).max()
        df['don_low_n1'] = df['low'].rolling(n1).min()
        df['don_high_n2'] = df['high'].rolling(n2).max()
        df['don_low_n2'] = df['low'].rolling(n2).min()
        # 止盈点10日
        df['dc_stop_profit'] = df['low'].rolling(10).min()

        df['dc_sys1_up_cross'] = False
        df['dc_sys1_down_cross'] = False
        # 突破sys1
        df.loc[(df['high'] > df.shift(1)['don_high_n1']) & (
                df.shift(1)['high'] <= df.shift(1).shift(1)['don_high_n1']), 'dc_sys1_up_cross'] = True
        df.loc[(df['low'] < df.shift(1)['don_low_n1']) & (
                df.shift(1)['low'] >= df.shift(1).shift(1)['don_low_n1']), 'dc_sys1_down_cross'] = True
        # 突破sys2
        df['dc_sys2_up_cross'] = False
        df['dc_sys2_down_cross'] = False
        df.loc[(df['high'] > df.shift(1)['don_high_n2']), 'dc_sys2_up_cross'] = True
        df.loc[(df['low'] < df.shift(1)['don_low_n2']), 'dc_sys2_down_cross'] = True

        # 平均波动性
        # ATR(df, 21)

    def calculate_session_indicator(self, bar: Bar = None) -> pd.Series:
        data = pd.Series(dtype='float64')
        security = bar.security
        # Collect bar data (only keep latest 120 records)
        self.ohlcv[security].append(bar)
        if len(self.ohlcv[security]) > 120:
            self.ohlcv[security].pop(0)

        code = security.code
        df = self._dKline_df.loc[code]

        if self.is_backtest is False:
            bar_ohlc = pd.DataFrame({
                "time_key": [bar.datetime.strftime("%Y-%m-%d 00:00:00")],
                "code": [code],
                "open": [bar.open],
                "high": [bar.high],
                "low": [bar.low],
                "close": [bar.close],
            })
            df.reset_index(inplace=True)
            df['code'] = code
            df = pd.concat([df, bar_ohlc], ignore_index=True)
            df = df.tail(60)
            df.set_index(['code', 'time_key'], inplace=True)
        else:
            idx = pd.IndexSlice
            df = df.loc[idx[:bar.datetime.strftime("%Y-%m-%d 00:00:00")]]

        atr_period = self.turtle_ctxs[security.code].atr_period
        if len(df) <= atr_period:
            return data

        df.ta.atr(length=atr_period, mamode='sma', col_names="ATR", append=True)
        data = df.loc[bar.datetime.strftime("%Y-%m-%d 00:00:00")]
        return data

    async def on_bar(self, cur_data: Dict[str, Dict[Security, Bar]]):
        logger.info("-" * 30 + "Enter on_bar" + "-" * 30)
        logger.info("cur_data=", cur_data)
        gateway_name = self.gateway_name
        if gateway_name not in cur_data:
            return

        # check balance
        # balance = self.engine.get_balance(gateway_name=gateway_name)
        # logger.info(f"{balance}")
        strategy_balance = self.get_strategy_account_balance(gateway_name)
        broker_balance = self.engine.get_broker_balance(
            gateway_name=gateway_name)
        logger.info(f"{broker_balance}")

        # check position
        positions = self.engine.get_all_positions(
            gateway_name=gateway_name)
        logger.info(f"positions = {positions}")
        # broker_positions = self.engine.get_all_broker_positions(
        #     gateway_name=gateway_name)
        # logger.info(f"{broker_positions}")

        # send orders
        for security in cur_data[gateway_name]:
            if security not in self.securities[gateway_name]:
                continue

            bar = cur_data[gateway_name][security]
            # todo: 获取股票交易日历，并判断是否在交易日内
            calendar = xcals.get_calendar("XNYS")
            if calendar.is_session(bar.datetime.strftime("%Y-%m-%d")) is False:
                continue

            # 处理实时指标
            session_indicator = self.calculate_session_indicator(bar)
            if session_indicator.empty is True or pd.isna(session_indicator['ATR']):
                continue

            code = security.code
            pre_date = calendar.previous_session(bar.datetime.strftime("%Y-%m-%d"), True)
            pre_session_data = self._dKline_df.loc[
                (code, pre_date.strftime("%Y-%m-%d 00:00:00"))].squeeze()

            # 仓位
            long_position = self.engine.get_position(
                security=security, direction=Direction.LONG, gateway_name=gateway_name)
            short_position = self.engine.get_position(
                security=security, direction=Direction.SHORT, gateway_name=gateway_name)

            strategy_ctx = TradeStrategyContext(
                long_position=long_position,
                sort_position=short_position,
                gateway_name=gateway_name,
                bar=bar,
                pre_session_data=pre_session_data,
                session_indicator=session_indicator,
            )

            # 头寸规模单位
            atr_volume = session_indicator['ATR'] * security.lot_size  # 一个市场中代表着每份合约有1ATR变动幅度的美元金额
            capital_control_ratio = 0.01
            NLot = int(strategy_balance.cash * capital_control_ratio / atr_volume)

            self.turtle_ctxs[code].unit = NLot

            # 开仓
            order_instruct = self._try_open(strategy_ctx)
            if not order_instruct:
                order_instruct = self._try_close(strategy_ctx)

            if not order_instruct:
                continue
            # 更新操作
            self.update_action(gateway_name, action=dict(
                gw=gateway_name,
                sec=security.code,
                side=order_instruct.get("direction").value,
                offset=order_instruct.get("offset").value,
            ))
            self.on_order(gateway_name, order_instruct)

    def _try_open(self, ctx: TradeStrategyContext = None) -> dict:
        """
        开仓策略
        """
        if ctx is None:
            return {}
        # 仓位为空才能开仓
        if ctx.long_position or ctx.sort_position:
            return {}

        bar = ctx.bar
        security = bar.security
        code = security.code

        cur_price = bar.close

        order_instruct = {}
        # 入场：今日突破，前一日未突破
        if self._real_price(cur_price, bar.high) > ctx.pre_session_data['don_high_n1'] and not \
                ctx.pre_session_data['dc_sys1_up_cross'] and ctx.pre_session_data['EMA_10'] > ctx.pre_session_data[
            'EMA_20'] and bar.high > ctx.pre_session_data['EMA_60']:
            # 通过均线过滤无效突破
            quantity = self.turtle_ctxs[code].unit
            self.turtle_ctxs[code].add_time += 1
            self.turtle_ctxs[code].hold_flag = True
            cur_price = self._real_price(cur_price, bar.high)
            self.turtle_ctxs[code].last_buy_price = cur_price
            order_instruct = dict(
                security=security,
                price=cur_price,
                quantity=quantity,  # 购买数量
                direction=Direction.LONG,
                offset=Offset.OPEN,
                order_type=OrderType.MARKET,
                gateway_name=ctx.gateway_name,
            )

        # 做空（期货、期权、外汇）
        # if self._gateway_real_price(bar.close, bar.low) < ctx.pre_session_data['don_low_n1'] and not \
        # ctx.pre_session_data['dc_sys1_down_cross']:
        #     signal = "SELL"
        return order_instruct

    def _try_close(self, ctx: TradeStrategyContext = None) -> dict:
        """
        交易策略
        """
        if ctx is None:
            return {}
        # 仓位为空才能开仓
        if ctx.long_position is None or not ctx.long_position:
            return {}

        bar = ctx.bar
        security = bar.security
        code = security.code
        turtle_ctx = self.turtle_ctxs[code]
        cur_price = bar.close

        order_instruct = {}

        quantity = 0.0
        direction = None
        offset = None
        # 开仓、加仓
        # 加仓、止损、止盈
        # 加仓策略: 如果是多仓且行情最新价在上一次建仓（或者加仓）的基础上又上涨了0.5N，就再加一个Unit的多仓,并且风险度在设定范围内(以防爆仓)
        if self._real_price(cur_price, bar.high) >= turtle_ctx.last_buy_price + 0.5 * ctx.session_indicator[
            'ATR'] and turtle_ctx.add_time < turtle_ctx.limit_unit:
            quantity = ctx.long_position.quantity + turtle_ctx.unit
            direction = Direction.LONG
            offset = Offset.OPEN
            self.turtle_ctxs[code].hold_flag = True
            cur_price = self._real_price(cur_price, bar.high)
            self.turtle_ctxs[code].last_buy_price = cur_price
            self.turtle_ctxs[code].add_time += 1

        # 止损策略: 如果是多仓且行情最新价在上一次建仓（或者加仓）的基础上又下跌了2N，就卖出全部头寸止损
        elif self._real_price(cur_price, bar.low) <= turtle_ctx.last_buy_price - 2 * ctx.session_indicator['ATR']:
            quantity = ctx.long_position.quantity
            direction = Direction.SHORT
            offset = Offset.CLOSE
            self.turtle_ctxs[code].hold_flag = False
            self.turtle_ctxs[code].add_time = 0
            cur_price = self._real_price(cur_price, bar.low)
        # 止盈策略: 如果是多仓且行情最新价跌破了10日唐奇安通道的下轨，就清空所有头寸结束策略,离场
        elif self._real_price(cur_price, bar.low) <= ctx.pre_session_data['dc_stop_profit']:
            quantity = ctx.long_position.quantity
            direction = Direction.SHORT
            offset = Offset.CLOSE
            self.turtle_ctxs[code].hold_flag = False
            self.turtle_ctxs[code].add_time = 0
            cur_price = self._real_price(cur_price, bar.low)

        if quantity <= 0 or direction is None or offset is None:
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

    def _real_price(self, cur_price: float = None, gateway_price: float = None) -> float:
        if gateway_price is None:
            gateway_price = cur_price
        return gateway_price if self.is_backtest else cur_price

    def on_order(self, gateway_name: str = None, order_instruct: dict = None):
        logger.info(f"Submit order: \n{order_instruct}", caller=self)
        # 处理订单
        order_id = self.engine.send_order(**order_instruct)
        if order_id == "":
            logger.info("Fail to submit order")
            return

        sleep(self.sleep_time)
        order = self.engine.get_order(
            orderid=order_id, gateway_name=gateway_name)
        logger.info(f"Order ({order_id}) has been sent: {order}", caller=self)
        # get activated plugins
        plugins = self.engine.get_plugins()
        if "dingtalk" in plugins and not self.is_backtest:
            dingtalk_bot = plugins["dingtalk"].bot
            dingtalk_bot.send_text(f"{datetime.now()} Order ({order_id}) has been sent: {order}")

        # 处理交易
        deals = self.engine.find_deals_with_orderid(
            order_id, gateway_name=gateway_name)
        for deal in deals:
            # 更新持仓
            self.portfolios[gateway_name].update(deal)

        if order.status == OrderStatus.FILLED:
            logger.info(f"Order ({order_id}) has been filled.", caller=self)
        else:
            err = self.engine.cancel_order(orderid=order_id, gateway_name=gateway_name)
            if err:
                logger.error(f"Can't cancel order ({order_id}). Error: {err}", caller=self)
                return
            logger.info(f"Successfully cancel order ({order_id}).", caller=self)
