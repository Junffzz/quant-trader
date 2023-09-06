from abc import ABC
from time import sleep
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass

import pandas as pd
import pandas_ta as ta
import exchange_calendars as xcals

from app.domain.balance import AccountBalance
from app.domain.position import Position, PositionData
from app.constants import Direction, Offset, OrderTimeInForce, OrderType, TradeMode, OrderStatus
from app.domain.data import Bar
from app.domain.engine import Engine
from app.domain.security import Stock, Security
from app.utils import logger
from app.strategies.base_strategy import BaseStrategy
from app.utils.tasks import SingleTask, LoopRunTask

from multiprocessing import Process, freeze_support


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
    position: Position = None
    # long_position: PositionData = None
    # sort_position: PositionData = None
    gateway_name: str = None
    # security: Security = None
    bar: Bar = None
    pre_indicator: pd.Series = None  # 日维度指标
    session_indicator: pd.Series = None  # 当前交易日


class StockUSStrategy(BaseStrategy, ABC):
    """
    策略说明
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

    证券仓位管理：
    1.每个证券均等分（小资金，全量切换证券）
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
        self.id_prefix = "stock_us_strategy_"
        # 海龟参数
        self.turtle_ctxs: Dict[str, TurtleContext] = {}
        self.max_position = 3  # 最大持仓数

    def init_strategy(self,
                      start: datetime = None,
                      end: datetime = None,
                      ):
        self.ohlcv = {}
        for security in self.securities[self.gateway_name]:
            self.ohlcv[security] = []
            self.turtle_ctxs[security.code]: TurtleContext = TurtleContext()

        if self.is_backtest is False:
            today = datetime.today()
            start = today - timedelta(120)  # 120日之前
            end = today

        SingleTask.run(self.daily_indicator_callback, start=start, end=end)
        # 注册定时任务
        if self.is_backtest is False:
            LoopRunTask.register(self.daily_indicator_callback, 60 * 20, start=start, end=end)

    async def daily_indicator_callback(self, *args, **kwargs):
        """
        加载k线策略
        """
        from app.domain.stores.security_market_storer import SecurityMarketStorer
        storer = SecurityMarketStorer(local=False)

        gateway_name = self.gateway_name
        securities = self.securities[gateway_name]
        if self.is_backtest:
            data = self.engine.gateways[gateway_name].get_kline_data(securities)
        else:
            today = datetime.today()
            start = today - timedelta(120)  # 120日之前
            end = today
            data = storer.get_kline_data(securities, start=start, end=end)

        for security in securities:
            df = data.loc[data['code'] == security.code].sort_values('time_key')
            self.dispatch_kline_indicator(df)
            self._dKline_df = pd.concat([self._dKline_df, df], ignore_index=True)

        # 重建索引
        self._dKline_df.set_index(['code', 'time_key'], inplace=True)
        self._dKline_df = self._dKline_df.sort_index()
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
            # df = pd.concat([df, bar_ohlc], ignore_index=True)
            df = df.tail(60)
            df.set_index(['code', 'time_key'], inplace=True)
        else:
            idx = pd.IndexSlice
            df = df.loc[idx[:bar.datetime.strftime("%Y-%m-%d 00:00:00")]]
            df['code'] = code
            df.reset_index(inplace=True)
            df.set_index(['code', 'time_key'], inplace=True)

        atr_period = self.turtle_ctxs[security.code].atr_period
        if len(df) <= atr_period:
            return data

        df.ta.atr(length=atr_period, mamode='sma', col_names="ATR", append=True)
        data = df.loc[(code, bar.datetime.strftime("%Y-%m-%d 00:00:00"))]
        return data

    def _try_buy(self, ctx: TradeStrategyContext = None):
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
        # 买点
        # v1
        # if ohlc['ema_signal'] == 1 and ohlc['macd_diffuse_signal'] == 1 and ohlc[
        #     'MACD_DIF'] > 0 and ohlc['ema60_up'] == 1 and \
        #         self.cut_lost_position[security.code].cut_price is None:
        #     quantity = math.floor(balance.cash / bar.close)
        #     if quantity > 0:
        #         order_instruct = dict(
        #             security=security,
        #             price=cur_price,
        #             quantity=quantity,  # 购买数量
        #             direction=Direction.LONG,
        #             offset=Offset.OPEN,
        #             order_type=OrderType.MARKET,
        #             gateway_name=ctx.gateway_name,
        #         )
        # return order_instruct

        # v2
        if ohlc['MACD_DIF'] < -1 or ohlc['ema20_up'] != 1 or ohlc['close'] < ohlc['EMA_60']:
            return

        # 共振
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

    def _try_sell(self, ctx: TradeStrategyContext = None):
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

        # 卖点
        if ohlc['macd_dif_signal'] == 0 or ohlc['ema_fork_signal'] == 0:
            quantity = long_position.quantity
            direction = Direction.SHORT
            offset = Offset.CLOSE
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

        # if new_ohlc['MACD'] > 0 and new_ohlc['MACD_DIF'] > 0.5 and self.cut_lost_position[
        #     security.code] is None:
        #     signal = "BUY"
        # elif new_ohlc['MACD_DIF'] < -0.5:
        #     signal = "SELL"
        #     self.cut_lost_position[security.code] = None  # 重置止损位

        # 止损
        quantity = 0.0
        direction = None
        offset = None
        # 止损策略: 如果是多仓且行情最新价在上一次建仓（或者加仓）的基础上又下跌了2N，就卖出全部头寸止损
        if self._real_price(cur_price, bar.low) <= turtle_ctx.last_buy_price - 2 * ctx.session_indicator['ATR']:
            quantity = long_position.quantity
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

    def get_order_quantity(self, price: float = None) -> int:
        if price is None or price <= 0:
            return 0
        from app.strategies.position_manage_strategy import SecurityPositionStrategy
        gateway_name = self.gateway_name
        count = self.max_position  # len(self.securities[gateway_name])
        power_cash = self.portfolios[gateway_name].value
        balance = self.get_strategy_account_balance(gateway_name)

        return SecurityPositionStrategy(count, power_cash, balance.cash).get_order_quantity(price)

    async def on_bar(self, cur_data: Dict[str, Dict[Security, Bar]]):

        logger.info("-" * 30 + "Enter on_bar" + "-" * 30)
        logger.info(cur_data)
        gateway_name = self.gateway_name
        if gateway_name not in cur_data:
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
        for security in cur_data[gateway_name]:
            if security not in self.securities[gateway_name]:
                continue

            bar = cur_data[gateway_name][security]
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

            daily_indicator = self._dKline_df.loc[
                (code, pre_date.strftime("%Y-%m-%d 00:00:00"))].squeeze()

            context = TradeStrategyContext(
                position=the_position,
                # long_position=long_position,
                # sort_position=short_position,
                gateway_name=gateway_name,
                bar=bar,
                pre_indicator=daily_indicator,
                session_indicator=session_indicator
            )

            # 头寸规模单位
            atr_volume = session_indicator['ATR'] * security.lot_size  # 一个市场中代表着每份合约有1ATR变动幅度的美元金额
            capital_control_ratio = 0.01
            NLot = int(balance.cash * capital_control_ratio / atr_volume)

            self.turtle_ctxs[code].unit = NLot

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

    def on_order(self, gateway_name: str = None, order_instruct: dict = None):
        order_instruct["time_in_force"] = OrderTimeInForce.DAY
        order_instruct["remark"] = self.id_prefix + "onorder"
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
