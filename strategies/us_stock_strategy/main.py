# -*- coding:utf-8 -*-

import sys
import os
import asyncio
import signal

sys.path.append(os.path.dirname(os.path.dirname(sys.path[0])))
from typing import Dict, List
from datetime import datetime, timedelta

import app.gateways as gateways

from app import application
from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.security import Stock, Security
from app.domain.engine import Engine
from app.strategies import BaseStrategy
from app.domain.event_engine import BarEventEngineRecorder, BarEventEngine
from strategies.us_stock_strategy.strategy import register_strategy_securities, new_grid_trading_strategy, \
    new_stock2_strategy,register_strategy_etf_securities
from app.config.configure import config
from app.utils import logger


def analysis_performance(plugins, start: datetime, end: datetime, gateway_name: str = "", stocks: [Stock] = None,
                         result_path: str = None):
    if "analysis" in plugins:
        plot_pnl = plugins["analysis"].plot_pnl
        plot_pnl(result_path=result_path, freq="daily", auto_open=True)

        instruments = {
            "security": {
                # ["FUT.GC", "FUT.SI", "FUT.CO"], ["HK.MHImain", "HK.HHImain"]
                gateway_name: [row.code for row in stocks],
            },
            "lot": {
                gateway_name: [row.lot_size for row in stocks],  # [100, 5000, 1000], [10, 50]
            },
            "commission": {
                gateway_name: [1.92 for row in stocks],  # [1.92, 1.92, 1.92]  [10.1, 10.1]
            },
            "slippage": {
                gateway_name: [0.0 for row in stocks],  # [0.0, 0.0, 0.0], [0.0, 0.0]
            }
        }
        plot_pnl_with_category = plugins["analysis"].plot_pnl_with_category
        plot_pnl_with_category(
            instruments=instruments,
            result_path=result_path,
            category="action",
            start=start,
            end=end
        )


class EntranceService:
    def __init__(self,
                 gateway_name: str = "Backtest",
                 trade_mode: TradeMode = TradeMode.BACKTEST,
                 securities: List[Stock] = None,
                 strategy_func=None,
                 **kwargs
                 ):
        """
        gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
        """
        self._trade_mode = trade_mode
        self.securities = securities

        today = datetime.now()
        self.start_time = today - timedelta(120)
        if 'start_time' in kwargs:
            self.start_time: datetime = kwargs.get("start_time")
        self.end_time = datetime.now()
        if 'end_time' in kwargs:
            self.end_time: datetime = kwargs.get("end_time")

        self.gateway = self._init_gateway(gateway_name, **kwargs)

        # Engine
        self.engine = Engine(gateways={gateway_name: self.gateway})

        strategy: BaseStrategy = strategy_func(securities, gateway_name, self.engine, **kwargs)
        # Event recorder
        self.recorder = BarEventEngineRecorder(datetime=[],
                                               action=[],
                                               open=[],
                                               high=[],
                                               low=[],
                                               close=[],
                                               volume=[])

        self.event_engine = BarEventEngine(
            strategies={str(strategy.strategy_account) + str(strategy.strategy_version): strategy},
            recorders={str(strategy.strategy_account) + str(strategy.strategy_version): self.recorder},
            engine=self.engine
        )

    def start(self):
        self.event_engine.run()

        if self._trade_mode == TradeMode.BACKTEST:
            from app.utils.tasks import SingleTask
            SingleTask.run(self._shutdown_backtest_callback, recorder=self.recorder)

    def stop(self):
        asyncio.get_event_loop().stop()
        self.engine.stop()
        logger.info("Program shutdown normally.")

    async def _shutdown_backtest_callback(self, *args, **kwargs):
        recorder: BarEventEngineRecorder = kwargs.get("recorder")
        if self._trade_mode == TradeMode.BACKTEST:
            result_path = recorder.save_csv()

            # get activated plugins
            plugins = self.engine.get_plugins()
            if self._trade_mode == TradeMode.BACKTEST:
                start_time: datetime = self.start_time
                end_time: datetime = self.end_time
                analysis_performance(plugins, start_time, end_time, 'Backtest', self.securities, result_path)

        return

    def _init_gateway(self, gateway_name: str = 'Backtest', **kwargs) -> gateways.BaseGateway:
        UseGateway = gateways.BaseGateway
        fees = gateways.BacktestFees

        trade_market = TradeMarket.NONE
        if 'trade_market' in kwargs:
            trade_market = kwargs.get("trade_market")

        if self._trade_mode == TradeMode.BACKTEST:
            gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
            UseGateway = gateways.BacktestGateway
            gateway = UseGateway(
                securities=self.securities,
                trade_market=trade_market,
                gateway_name=gateway_name,
                fees=fees,
                start=self.start_time,
                end=self.end_time,
                # trading_sessions=trading_sessions,
                num_of_1min_bar=180
            )
        elif self._trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
            gateway_name = "Futu"
            UseGateway = gateways.FutuGateway  # CqgGateway
            gateway = UseGateway(
                # securities=self.securities,
                trade_market=trade_market,
                gateway_name=gateway_name,
                fees=fees,
                start=self.start_time,
                end=self.end_time,
                # trading_sessions=trading_sessions,
                num_of_1min_bar=180
            )

        # trading_sessions = {str: list}
        # for s in self.securities:
        #     trading_sessions[s.code] = []
        #     trading_sessions[s.code].append([datetime(1970, 1, 1, 10, 30, 0, 0), datetime(1970, 1, 1, 9, 30, 0, 0)])

        # gateway = UseGateway(
        #     # securities=self.securities,
        #     trade_market=trade_market,
        #     gateway_name=gateway_name,
        #     fees=fees,
        #     start=self.start_time,
        #     end=self.end_time,
        #     # trading_sessions=trading_sessions,
        #     num_of_1min_bar=180
        # )
        gateway.SHORT_INTEREST_RATE = 0.0
        gateway.trade_mode = self._trade_mode
        if gateway.trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
            assert datetime.now() < gateway.end, (
                "Gateway end time must be later than current datetime!")
        return gateway


def initialize():
    gateway_name = "Backtest"
    trade_mode = TradeMode.BACKTEST

    if config.service.get('env') == 'prod':
        gateway_name = "Futu"
        trade_mode = TradeMode.SIMULATE

    today = datetime.today()
    start_time = today - timedelta(120)
    end_time = datetime.now()
    if trade_mode == TradeMode.BACKTEST:
        start_time = datetime(2020, 1, 1, 9, 30, 0, 0)
        end_time = datetime(2023, 5, 14, 16, 0, 0, 0)
    elif trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
        start_time = today - timedelta(120)
        end_time = datetime(today.year, today.month, today.day, 23, 0, 0)

    # securities = register_strategy_securities('new_stock2_strategy',trade_mode)
    # securities = register_strategy_securities('new_grid_trading_strategy', trade_mode)
    securities = register_strategy_etf_securities('new_grid_trading_strategy', trade_mode)
    service = EntranceService(securities=securities,
                              gateway_name=gateway_name,
                              trade_mode=trade_mode,
                              trade_market=TradeMarket.US,
                              start_time=start_time,
                              end_time=end_time,
                              strategy_func=new_grid_trading_strategy,
                              # strategy_func=new_stock2_strategy,
                              )
    service.start()

    def keyboard_interrupt(s, f):
        print("main KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(s))
        service.stop()

    signal.signal(signal.SIGINT, keyboard_interrupt)
    if trade_mode == TradeMode.BACKTEST:
        service.stop()


if __name__ == "__main__":
    config_file = sys.argv[1]
    application.start(config_file, initialize)
