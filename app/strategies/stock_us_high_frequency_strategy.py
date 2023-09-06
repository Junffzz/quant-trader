from abc import ABC
from time import sleep
from datetime import datetime, timedelta
from typing import Dict, List
import math
from dataclasses import dataclass

import pandas as pd
import pandas_ta as ta
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

from app.domain.stores.security_market_storer import SecurityMarketStorer

from multiprocessing import Process, freeze_support


@dataclass
class CutLostPosition:
    """CutLostPosition"""
    datetime: datetime = None
    cut_price: float = None
    high_price: float = None


@dataclass
class TradeSignalContext:
    """交易信号上下文"""
    long_position: PositionData = None
    sort_position: PositionData = None
    gateway_name: str = None
    security: Security = None
    bar: Bar = None
    daily_indicator: pd.Series = None  # 日维度指标
    session_indicator: pd.Series = None  # 当前交易日
    signal: str = None
    quantity: int = 1


class StockUSHighFrequencyStrategy(BaseStrategy, ABC):
    """
    高频策略
    日线判断买卖点，分钟线择时判断
    1.先初始化日线数据

    日K线分析
    入场位：
    1.macd低位金叉
    2.macd_DIF大于0.2，明显向上突然0轴
    3.10日均线发生拐头并和20日均线金叉
    4.KDJ低位金叉，并配合10日均线

    加仓位：
    第一次加40%，第二次加20%，止损而持仓时，又满足开仓条件则按上次止损量开仓，使总持仓量回到止损前的水平

    止损位：
    1.macd高位死叉
    2.低于买入价5%
    3.持仓总亏损达到10%
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
        self.portfolios = engine.portfolios
        self.is_backtest = False
        # For simulation/live trading, set the waiting time > 0
        self.sleep_time = 0
        for gateway_name in engine.gateways:
            if engine.gateways[gateway_name].trade_mode != TradeMode.BACKTEST:
                self.sleep_time = 5
            else:
                self.is_backtest = True

        self.ohlcv = {}
        # 止损位
        self.cut_lost_position = {}

    def init_strategy(self):
        for gateway_name in self.engine.gateways:
            self.ohlcv[gateway_name] = {}
            for security in self.engine.gateways[gateway_name].securities:
                self.ohlcv[gateway_name][security] = []
                # 初始化止损位
                self.cut_lost_position[security.code]: CutLostPosition = CutLostPosition()

        SingleTask.run(self.daily_indicator_callback)
        # 注册定时任务
        if self.is_backtest is False:
            LoopRunTask.register(self.daily_indicator_callback, 60 * 60)

    async def daily_indicator_callback(self, *args, **kwargs):
        """
        加载k线策略
        """
        if self.is_backtest is False:
            today = datetime.today()
            start = today - timedelta(120)  # 120日之前
            end = today

        market = SecurityMarketStorer(local=False)

        for gateway_name in self.engine.gateways:
            data = market.get_kline_data(self.securities[gateway_name], start=start, end=end)
            for security in self.securities[gateway_name]:
                code = security.code.split(".")[1]
                df = data.loc[data['code'] == code].sort_values('time_key')
                self.dispatch_kline_indicator(df)
                self._dKline_df = pd.concat([self._dKline_df, df], ignore_index=True)

        # 重建索引
        self._dKline_df.set_index(['time_key', 'code'], inplace=True)
        self._dKline_df = self._dKline_df.sort_index()

        # await asyncio.sleep(0.01)
        return

    def dispatch_kline_indicator(self, df: pd.DataFrame = None):
        tech_strategy = ta.Strategy(
            name="Momo and Volatility",
            description="SMA 50,200, BBANDS, RSI, MACD and Volume SMA 20",
            ta=[
                {"kind": "ema", "length": 10},
                {"kind": "ema", "length": 20},
                {"kind": "ema", "length": 30},
                {"kind": "ema", "length": 60},
                {"kind": "ema", "length": 90},
                {"kind": "ema", "length": 120},
                {"kind": "kdj", "col_names": ("KDJ_K", "KDJ_D", "KDJ_J")},
                {"kind": "kdj", "signal": 6, "col_names": ("KD_MACD_K", "KD_MACD_D", "KD_MACD_J")},
                {"kind": "macd", "asmode": False, "col_names": ("MACD_DIF", "MACD", "MACD_DEA")},
                {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOLUME"},
            ]
        )
        freeze_support()
        df.ta.strategy(tech_strategy)
        df['MACD'] *= 2  # MACD需要乘以2
        # 当macd DIF>DEA交叉信号
        df.loc[(df['MACD'] > 0) & (df['MACD'].shift(1) < 0), 'macd_fork_signal'] = 1
        df.loc[(df['MACD'] < 0) & (df['MACD'].shift(1) > 0), 'macd_fork_signal'] = 0

        # 当macd红柱发散信号
        df.loc[(df['MACD'] > 0) & (df['MACD'].shift(1) < df['MACD']), 'macd_diffuse_signal'] = 1
        df.loc[(df['MACD'] < 0) & (df['MACD'].shift(1) > df['MACD']), 'macd_diffuse_signal'] = 0

        # 当macd DIF>0.2或DIF<-0.2 且发散发出买卖信号
        df.loc[(df['MACD_DIF'] > 0.2) & (df['MACD_DIF'].shift(1) < df['MACD_DIF']) & (
                df['MACD_DIF'].shift(-1) > df['MACD_DIF']), 'macd_dif_signal'] = 1
        df.loc[(df['MACD_DIF'] < -0.2) & (df['MACD_DIF'].shift(1) > df['MACD_DIF']) & (
                df['MACD_DIF'].shift(-1) < df['MACD_DIF']), 'macd_dif_signal'] = 0

        # 当kd-macd DIF>0.2或DIF<-0.2 且发散发出买卖信号
        df.loc[(df['KD_MACD_K'] < 50) & (df['KD_MACD_K'].shift(1) < df['KD_MACD_K']), 'kdmacd_k_signal'] = 1
        df.loc[(df['KD_MACD_K'] < -0.2) & (df['KD_MACD_K'].shift(1) > df['KD_MACD_K']), 'kdmacd_k_signal'] = 0

        # 均线交叉信号
        df.loc[(df['EMA_10'] > df['EMA_20']) & (df['EMA_10'].shift(1) < df['EMA_20'].shift(1)), 'ema_fork_signal'] = 1
        df.loc[(df['EMA_10'] < df['EMA_20']) & (df['EMA_10'].shift(1) > df['EMA_20'].shift(1)), 'ema_fork_signal'] = 0
        # 均线比较信号
        df.loc[(df['EMA_10'] > df['EMA_20']), 'ema_signal'] = 1
        df.loc[(df['EMA_10'] < df['EMA_20']), 'ema_signal'] = 0

        # 20日趋势
        df.loc[(df['EMA_20'] > df['EMA_20'].shift(1)) & (df['EMA_20'].shift(1) > df['EMA_20'].shift(2)), 'ema20_up'] = 1
        df.loc[(df['EMA_20'] < df['EMA_20'].shift(1)) & (df['EMA_20'].shift(1) < df['EMA_20'].shift(2)), 'ema20_up'] = 0

        # 60日趋势
        df.loc[(df['EMA_60'] > df['EMA_60'].shift(1)) & (df['EMA_60'] > df['EMA_60'].shift(2)) & (
                df['EMA_60'] > df['EMA_60'].shift(3)), 'ema60_up'] = 1
        df.loc[(df['EMA_60'] < df['EMA_60'].shift(1)) & (df['EMA_60'] < df['EMA_60'].shift(2)) & (
                df['EMA_60'] < df['EMA_60'].shift(3)), 'ema60_up'] = 0

    def calculate_session_indicator(self, gateway_name, bar: Bar = None) -> pd.DataFrame:
        security = bar.security
        # Collect bar data (only keep latest 120 records)
        self.ohlcv[gateway_name][security].append(bar)
        if len(self.ohlcv[gateway_name][security]) > 120:
            self.ohlcv[gateway_name][security].pop(0)

        open_ts = [b.open for b in
                   self.ohlcv[gateway_name][security]]
        high_ts = [b.high for b in
                   self.ohlcv[gateway_name][security]]
        low_ts = [b.low for b in
                  self.ohlcv[gateway_name][security]]
        close_ts = [b.close for b in
                    self.ohlcv[gateway_name][security]]

        df = pd.DataFrame({
            "open": open_ts,
            "high": high_ts,
            "low": low_ts,
            "close": close_ts
        })
        if len(df) < 60:
            return df

        tech_strategy = ta.Strategy(
            name="Momo and Volatility",
            description="SMA 50,200, BBANDS, RSI, MACD and Volume SMA 20",
            ta=[
                {"kind": "ema", "length": 10},
                {"kind": "ema", "length": 20},
                {"kind": "ema", "length": 60},
                # {"kind": "rsi"},
                {"kind": "kdj", "col_names": ("KDJ_K", "KDJ_D", "KDJ_J")},
                {"kind": "kdj", "signal": 6, "col_names": ("KD_MACD_K", "KD_MACD_D", "KD_MACD_J")},
                {"kind": "macd", "asmode": False, "col_names": ("MACD_DIF", "MACD", "MACD_DEA")},
                # {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOLUME"},
            ]
        )
        freeze_support()
        df.ta.strategy(tech_strategy)
        df['MACD'] *= 2  # MACD需要乘以2
        # 当macd DIF>DEA交叉信号
        df.loc[(df['MACD'] > 0) & (df['MACD'].shift(1) < 0), 'macd_fork_signal'] = 1
        df.loc[(df['MACD'] < 0) & (df['MACD'].shift(1) > 0), 'macd_fork_signal'] = 0

        # 当macd红柱发散信号
        df.loc[(df['MACD'] > 0) & (df['MACD'].shift(1) < df['MACD']), 'macd_diffuse_signal'] = 1
        df.loc[(df['MACD'] < 0) & (df['MACD'].shift(1) > df['MACD']), 'macd_diffuse_signal'] = 0

        # 当macd DIF>0.2或DIF<-0.2 且发散发出买卖信号
        df.loc[(df['MACD_DIF'] > 0.2) & (df['MACD_DIF'].shift(1) < df['MACD_DIF']) & (
                df['MACD_DIF'].shift(-1) > df['MACD_DIF']), 'macd_dif_signal'] = 1
        df.loc[(df['MACD_DIF'] < -0.2) & (df['MACD_DIF'].shift(1) > df['MACD_DIF']) & (
                df['MACD_DIF'].shift(-1) < df['MACD_DIF']), 'macd_dif_signal'] = 0

        # 当kd-macd DIF>0.2或DIF<-0.2 且发散发出买卖信号
        df.loc[(df['KD_MACD_K'] < 50) & (df['KD_MACD_K'].shift(1) < df['KD_MACD_K']), 'kdmacd_k_signal'] = 1
        df.loc[(df['KD_MACD_K'] < -0.2) & (df['KD_MACD_K'].shift(1) > df['KD_MACD_K']), 'kdmacd_k_signal'] = 0

        # 均线交叉信号
        df.loc[(df['EMA_10'] > df['EMA_20']) & (df['EMA_10'].shift(1) < df['EMA_20'].shift(1)), 'ema_fork_signal'] = 1
        df.loc[(df['EMA_10'] < df['EMA_20']) & (df['EMA_10'].shift(1) > df['EMA_20'].shift(1)), 'ema_fork_signal'] = 0
        # 均线比较信号
        df.loc[(df['EMA_10'] > df['EMA_20']), 'ema_signal'] = 1
        df.loc[(df['EMA_10'] < df['EMA_20']), 'ema_signal'] = 0

        # 20日趋势
        df.loc[(df['EMA_20'] > df['EMA_20'].shift(1)) & (df['EMA_20'].shift(1) > df['EMA_20'].shift(2)), 'ema20_up'] = 1
        df.loc[(df['EMA_20'] < df['EMA_20'].shift(1)) & (df['EMA_20'].shift(1) < df['EMA_20'].shift(2)), 'ema20_up'] = 0

        # 60趋势
        df.loc[(df['EMA_60'] > df['EMA_60'].shift(1)) & (df['EMA_60'] > df['EMA_60'].shift(2)) & (
                df['EMA_60'] > df['EMA_60'].shift(3)), 'ema60_up'] = 1
        df.loc[(df['EMA_60'] < df['EMA_60'].shift(1)) & (df['EMA_60'] < df['EMA_60'].shift(2)) & (
                df['EMA_60'] < df['EMA_60'].shift(3)), 'ema60_up'] = 0
        return df

    # 仓位管理
    def position_manager(self):
        """
        仓位管理：
        1.初始总资金分为10份，每份10%
        2.选股策略，筛选10只股票，进行竞选（谁的信号先发生，先触发哪只，直到资金利用完全）
        3.单只股票，入场20%，加仓10%（最多加仓一次）
        4.当持有仓位股票卖出时，以最新的总额比例变更仓位
        4.出场策略：信号触发
        5.止损策略：支撑位，价格
        """
        pass

    def dispatch_buy(self, ctx: TradeSignalContext = None):
        """
        入场
        1.10日和20日均线金叉
        2.且macd_dif>0
        3.且macd红柱线发散
        4.收阳线
        """
        if ctx is None:
            return

        gateway_name = ctx.gateway_name
        security = ctx.security
        bar = ctx.bar
        if gateway_name is None or security is None or bar is None:
            return

        ohlc = ctx.daily_indicator

        signal = None
        # 买点
        # v1
        # if ohlc['ema_signal'] == 1 and ohlc['macd_diffuse_signal'] == 1 and ohlc[
        #     'MACD_DIF'] > 0 and ohlc['ema60_up'] == 1 and \
        #         self.cut_lost_position[security.code].cut_price is None:
        #     signal = "BUY"

        # v2
        if ctx.daily_indicator['MACD_DIF'] < -1 or ctx.daily_indicator['ema20_up'] != 1 or ctx.daily_indicator[
            'close'] < ctx.daily_indicator['EMA_60']:
            return

        # 共振
        if ctx.session_indicator['ema_fork_signal'] == 1 and self.cut_lost_position[security.code].cut_price is None:
            signal = "BUY"

        ctx.signal = signal
        return signal

    def dispatch_sell(self, ctx: TradeSignalContext = None):
        """
        止损位：
        1.macd<-0.5
        2.价格低于买入价5%
        """
        gateway_name = ctx.gateway_name
        security = ctx.security
        bar = ctx.bar
        if gateway_name is None or security is None or bar is None:
            return

        signal = ctx.signal

        # 卖点
        if ctx.session_indicator['ema_fork_signal'] == 0:
            ctx.signal = "SELL"
            self.cut_lost_position[security.code] = CutLostPosition()  # 重置止损位
            return

        # if new_ohlc['MACD'] > 0 and new_ohlc['MACD_DIF'] > 0.5 and self.cut_lost_position[
        #     security.code] is None:
        #     signal = "BUY"
        # elif new_ohlc['MACD_DIF'] < -0.5:
        #     signal = "SELL"
        #     self.cut_lost_position[security.code] = None  # 重置止损位

        long_position = ctx.long_position
        # 止损
        if long_position:
            # 更新持仓最高价
            if self.cut_lost_position[security.code].high_price is None or self.cut_lost_position[
                security.code].high_price < bar.close:
                self.cut_lost_position[security.code].high_price = bar.close

            # 趋势线止损
            # if new_ohlc['ema120_up'] == 0:
            #     signal = "SELL"
            #     self.cut_lost_position[security.code].datetime = bar.datetime
            #     self.cut_lost_position[security.code].cut_price = bar.close

            # 价格止损
            stop_price_pct = (bar.close - long_position.holding_price) / long_position.holding_price
            # 持仓期间的最高价与现价涨跌幅
            high_price_pct = (bar.close - self.cut_lost_position[security.code].high_price) / \
                             self.cut_lost_position[security.code].high_price

            # 持仓总亏损止损

            # 持仓收益最高位
            high_position_value = long_position.quantity * self.cut_lost_position[security.code].high_price
            high_position_pct = (long_position.quantity * bar.close - high_position_value) / high_position_value
            # 当比买入价低于5% 或 比持仓期间最高价低于10%时
            if stop_price_pct <= -0.1 or high_price_pct <= -0.15:
                signal = "SELL"
                self.cut_lost_position[security.code].datetime = bar.datetime
                self.cut_lost_position[security.code].cut_price = bar.close
        ctx.signal = signal
        return signal

    async def on_bar(self, cur_data: Dict[str, Dict[Security, Bar]]):

        logger.info("-" * 30 + "Enter on_bar" + "-" * 30)
        logger.info(cur_data)

        for gateway_name in self.engine.gateways:
            if gateway_name not in cur_data:
                continue

            # check balance
            balance = self.engine.get_balance(gateway_name=gateway_name)
            logger.info(f"{balance}")
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
                    return
                # 处理实时指标
                session_indicator_df = self.calculate_session_indicator(gateway_name, bar)
                session_indicator = session_indicator_df.iloc[-1]
                if {'MACD', 'EMA_20'}.issubset(session_indicator_df.columns) is False:
                    return

                code = security.code.split(".")[1]
                pre_date = calendar.previous_session(bar.datetime.strftime("%Y-%m-%d"), True)

                daily_indicator = self._dKline_df.loc[
                    (pre_date.strftime("%Y-%m-%d 00:00:00"), code)].squeeze()

                # 仓位
                long_position = self.engine.get_position(
                    security=security, direction=Direction.LONG, gateway_name=gateway_name)
                short_position = self.engine.get_position(
                    security=security, direction=Direction.SHORT, gateway_name=gateway_name)

                signal = None
                context = TradeSignalContext(
                    long_position=long_position,
                    sort_position=short_position,
                    gateway_name=gateway_name,
                    security=security,
                    bar=bar,
                    daily_indicator=daily_indicator,
                    session_indicator=session_indicator,
                    signal=signal
                )

                self.dispatch_buy(context)  # buy
                self.dispatch_sell(context)  # sell

                signal = context.signal
                order_instruct = dict()
                if long_position and signal == "BUY":
                    # 开仓、加仓
                    continue
                elif long_position and signal == "SELL":
                    # 减仓、止损、清仓
                    order_instruct = dict(
                        security=security,
                        price=bar.close,
                        quantity=long_position.quantity,
                        direction=Direction.SHORT,
                        offset=Offset.CLOSE,
                        order_type=OrderType.MARKET,
                        gateway_name=gateway_name,
                    )
                elif signal == "BUY":
                    # 入场开仓
                    quantity = math.floor(balance.cash / bar.close) * 0.4
                    order_instruct = dict(
                        security=security,
                        price=bar.close,
                        quantity=quantity,  # 购买数量
                        direction=Direction.LONG,
                        offset=Offset.OPEN,
                        order_type=OrderType.MARKET,
                        gateway_name=gateway_name,
                    )
                else:
                    continue

                # 更新操作
                self.update_action(gateway_name, action=dict(
                    gw=gateway_name,
                    sec=security.code,
                    side=order_instruct.get("direction").value,
                    offset=order_instruct.get("offset").value,
                ))
                self.on_order(gateway_name, order_instruct)

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
        # get activated plugins
        plugins = self.engine.get_plugins()
        if "dingtalk" in plugins:
            dingtalk_bot = plugins["dingtalk"].bot
            dingtalk_bot.send_text(f"{datetime.now()} Order ({order_id}) has been sent: {order}")

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
