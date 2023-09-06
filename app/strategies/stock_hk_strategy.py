from abc import ABC
from time import sleep
from typing import Dict, List

import pandas as pd
from finta import TA

from app.domain.balance import AccountBalance
from app.domain.position import Position
from app.constants import Direction, Offset, OrderType, TradeMode, OrderStatus
from app.domain.data import Bar
from app.domain.engine import Engine
from app.domain.security import Stock, Security
from app.strategies.base_strategy import BaseStrategy
from app.utils import logger


class StockHKStrategy(BaseStrategy, ABC):
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
        self.portfolios = engine.portfolios
        # For simulation/live trading, set the waiting time > 0
        self.sleep_time = 0
        for gateway_name in engine.gateways:
            if engine.gateways[gateway_name].trade_mode != TradeMode.BACKTEST:
                self.sleep_time = 5

    def init_strategy(self):
        self.ohlcv = {}
        for gateway_name in self.engine.gateways:
            self.ohlcv[gateway_name] = {}
            for security in self.engine.gateways[gateway_name].securities:
                self.ohlcv[gateway_name][security] = []

    def on_bar(self, cur_data: Dict[str, Dict[Security, Bar]]):

        logger.info("-" * 30 + "Enter on_bar" + "-" * 30)
        logger.info(cur_data)

        for gateway_name in self.engine.gateways:
            if gateway_name not in cur_data:
                continue

            # check balance
            balance = self.engine.get_balance(gateway_name=gateway_name)
            self.engine.log.info(f"{balance}")
            broker_balance = self.engine.get_broker_balance(
                gateway_name=gateway_name)
            self.engine.log.info(f"{broker_balance}")

            # check position
            positions = self.engine.get_all_positions(
                gateway_name=gateway_name)
            self.engine.log.info(f"positions = {positions}")
            broker_positions = self.engine.get_all_broker_positions(
                gateway_name=gateway_name)
            self.engine.log.info(f"broker_positions = {broker_positions}")

            # send orders
            for security in cur_data[gateway_name]:
                if security not in self.securities[gateway_name]:
                    continue

                bar = cur_data[gateway_name][security]
                if bar is None:
                    continue

                # Collect bar data (only keep latest 20 records)
                self.ohlcv[gateway_name][security].append(bar)
                if len(self.ohlcv[gateway_name][security]) > 50:
                    self.ohlcv[gateway_name][security].pop(0)

                open_ts = [b.open for b in
                           self.ohlcv[gateway_name][security]]
                high_ts = [b.high for b in
                           self.ohlcv[gateway_name][security]]
                low_ts = [b.low for b in
                          self.ohlcv[gateway_name][security]]
                close_ts = [b.close for b in
                            self.ohlcv[gateway_name][security]]

                ohlc = pd.DataFrame({
                    "open": open_ts,
                    "high": high_ts,
                    "low": low_ts,
                    "close": close_ts
                })
                # macd = TA.MACD(
                #     ohlc,
                #     period_fast=12,
                #     period_slow=26,
                #     signal=9)
                #
                # if len(macd) < 2:
                #     continue
                #
                # prev_macd = macd.iloc[-2]["MACD"]
                # cur_macd = macd.iloc[-1]["MACD"]
                # cur_signal = macd.iloc[-1]["SIGNAL"]
                # signal = None
                # if prev_macd > cur_signal > cur_macd > 0:
                #     signal = "SELL"
                # elif prev_macd < cur_signal < cur_macd < 0:
                #     signal = "BUY"

                TA.STOCH(ohlc)
                TA.STOCHD(ohlc)

                rsi = TA.RSI(ohlc, period=6, column="close")
                if len(rsi) < 6:
                    continue

                cur_rsi = rsi.iloc[-1]
                signal = None
                if cur_rsi < 15:
                    signal = "BUY"
                if cur_rsi > 80:
                    signal = "SELL"

                # 持仓判断
                long_position = self.engine.get_position(
                    security=security, direction=Direction.LONG, gateway_name=gateway_name)
                short_position = self.engine.get_position(
                    security=security, direction=Direction.SHORT, gateway_name=gateway_name)

                if short_position and signal == "SELL":
                    continue
                elif long_position and signal == "BUY":
                    continue
                elif long_position and signal == "SELL":
                    order_instruct = dict(
                        security=security,
                        quantity=long_position.quantity,
                        direction=Direction.SHORT,
                        offset=Offset.CLOSE,
                        order_type=OrderType.MARKET,
                        gateway_name=gateway_name,
                    )
                elif signal == "SELL":
                    order_instruct = dict(
                        security=security,
                        quantity=1,
                        direction=Direction.SHORT,
                        offset=Offset.OPEN,
                        order_type=OrderType.MARKET,
                        gateway_name=gateway_name,
                    )
                elif short_position and signal == "BUY":
                    order_instruct = dict(
                        security=security,
                        quantity=short_position.quantity,
                        direction=Direction.LONG,
                        offset=Offset.CLOSE,
                        order_type=OrderType.MARKET,
                        gateway_name=gateway_name,
                    )
                elif signal == "BUY":
                    order_instruct = dict(
                        security=security,
                        quantity=1,
                        direction=Direction.LONG,
                        offset=Offset.OPEN,
                        order_type=OrderType.MARKET,
                        gateway_name=gateway_name,
                    )
                else:
                    continue

                order_instruct["price"] = bar.close
                logger.info(f"Submit order: \n{order_instruct}")
                # 处理订单
                orderid = self.engine.send_order(**order_instruct)
                if orderid == "":
                    logger.error("Fail to submit order ", order_instruct)
                    return

                sleep(self.sleep_time)
                order = self.engine.get_order(
                    orderid=orderid, gateway_name=gateway_name)
                logger.info(f"Order ({orderid}) has been sent: {order}")
                # 处理交易
                deals = self.engine.find_deals_with_orderid(
                    orderid, gateway_name=gateway_name)
                for deal in deals:
                    self.portfolios[gateway_name].update(deal)

                if order.status == OrderStatus.FILLED:
                    logger.info(f"Order ({orderid}) has been filled.")
                else:
                    err = self.engine.cancel_order(
                        orderid=orderid, gateway_name=gateway_name)
                    if err:
                        logger.error(
                            f"Can't cancel order ({orderid}). Error: {err}")
                    else:
                        logger.info(
                            f"Successfully cancel order ({orderid}).")

    def cut_position(self):
        # # 更新持仓最高价
        # if self.cut_lost_position[security.code].high_price is None or self.cut_lost_position[
        #     security.code].high_price < bar.close:
        #     self.cut_lost_position[security.code].high_price = bar.close
        #
        # # 趋势线止损
        # # if new_ohlc['ema120_up'] == 0:
        # #     signal = "SELL"
        # #     self.cut_lost_position[security.code].datetime = bar.datetime
        # #     self.cut_lost_position[security.code].cut_price = bar.close
        #
        # # 价格止损
        # stop_price_pct = (bar.close - long_position.holding_price) / long_position.holding_price
        # # 持仓期间的最高价与现价涨跌幅
        # high_price_pct = (bar.close - self.cut_lost_position[security.code].high_price) / \
        #                  self.cut_lost_position[security.code].high_price
        #
        # # 持仓总亏损止损
        #
        # # 持仓收益最高位
        # high_position_value = long_position.quantity * self.cut_lost_position[security.code].high_price
        # high_position_pct = (long_position.quantity * bar.close - high_position_value) / high_position_value
        # # 当比买入价低于5% 或 比持仓期间最高价低于10%时
        # if stop_price_pct <= -0.15 or high_price_pct <= -0.15:
        #     cur_price = bar.close
        #     quantity = long_position.quantity
        #     direction = Direction.SHORT
        #     offset = Offset.CLOSE
        #     order_instruct = dict(
        #         security=security,
        #         price=cur_price,
        #         quantity=quantity,  # 购买数量
        #         direction=direction,
        #         offset=offset,
        #         order_type=OrderType.MARKET,
        #         gateway_name=ctx.gateway_name,
        #     )
        #     self.cut_lost_position[security.code].datetime = bar.datetime
        #     self.cut_lost_position[security.code].cut_price = bar.close
        pass
