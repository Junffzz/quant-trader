# -*- coding:utf-8 -*-

import sys
import os
import asyncio

sys.path.append(os.path.dirname(sys.path[0]))
from typing import Dict, List
from datetime import datetime, timedelta

from app import application
from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.security import Futures, Security
from app.domain.engine import Engine
from app.strategies import BaseStrategy
from app.domain.position import Position
from app.domain.balance import AccountBalance
from app.domain.data import Bar
from app.facade.trade import realtime_data
from app.utils import logger

import app.gateways as gateways
from app.domain.event_engine import BarEventEngineRecorder, BarEventEngine

from app.strategies import BaseStrategy


def realtime_futures(securities=None) -> {str: Bar}:
    if securities is None:
        return
    code_list = None
    if isinstance(securities, list) and isinstance(securities[0], Security):
        code_list = [security.code.split(".")[1] for security in securities]
    elif isinstance(securities, Security):
        code_list = securities.code.split(".")[1]

    if code_list is None:
        return

    df = realtime_data("", code_list)
    df['close'] = df['current']

    bars = {}
    for security in securities:
        code = security.code.split(".")[1]
        data = df.loc[df['code'] == code].squeeze()
        bar_time = datetime.strptime(
            data["date"], "%Y-%m-%d %H:%M:%S")
        bars[security.code] = Bar(
            datetime=bar_time,
            security=security,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"])
    return bars


def analysis_performance(plugins, gateway_name: str = "", futures: [Futures] = None, result_path: str = None):
    if "analysis" in plugins:
        plot_pnl = plugins["analysis"].plot_pnl
        plot_pnl(result_path=result_path, freq="daily", auto_open=True)

        instruments = {
            "security": {
                # ["FUT.GC", "FUT.SI", "FUT.CO"], ["HK.MHImain", "HK.HHImain"]
                gateway_name: [row.code for row in futures],
            },
            "lot": {
                gateway_name: [row.lot_size for row in futures],  # [100, 5000, 1000], [10, 50]
            },
            "commission": {
                gateway_name: [1.92 for row in futures],  # [1.92, 1.92, 1.92]  [10.1, 10.1]
            },
            "slippage": {
                gateway_name: [0.0 for row in futures],  # [0.0, 0.0, 0.0], [0.0, 0.0]
            }
        }
        plot_pnl_with_category = plugins["analysis"].plot_pnl_with_category
        plot_pnl_with_category(
            instruments=instruments,
            result_path=result_path,
            category="action",
            start=datetime(2020, 1, 1, 9, 30, 0),
            end=datetime(2023, 3, 17, 23, 0, 0)
        )


class EntranceService:
    def __init__(self,
                 gateway_name: str = "Backtest",
                 trade_mode: TradeMode = TradeMode.BACKTEST,
                 strategies: List[Futures] = None,
                 strategy_func=None,
                 **kwargs
                 ):
        """
        gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
        """
        self._trade_mode = trade_mode
        self.strategies = strategies

        self.gateway = self._init_gateway(gateway_name, **kwargs)

        # Engine
        self.engine = Engine(gateways={gateway_name: self.gateway})

        strategy: BaseStrategy = strategy_func(strategies, gateway_name, self.engine, **kwargs)
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
        logger.info("Program shutdown normally.")

    async def _shutdown_backtest_callback(self, *args, **kwargs):
        recorder: BarEventEngineRecorder = kwargs.get("recorder")
        if self._trade_mode == TradeMode.BACKTEST:
            result_path = recorder.save_csv()

            # get activated plugins
            plugins = self.engine.get_plugins()
            if self._trade_mode == TradeMode.BACKTEST:
                analysis_performance(plugins, 'Backtest', self.strategies, result_path)

        return

    def _init_gateway(self, gateway_name: str = 'Backtest', **kwargs) -> gateways.BaseGateway:
        UseGateway = gateways.BaseGateway
        fees = gateways.BacktestFees

        trade_market = TradeMarket.NONE
        if 'trade_market' in kwargs:
            trade_market = kwargs.get("trade_market")

        today = datetime.now()
        start_time = today - timedelta(120)
        if 'start_time' in kwargs:
            start_time: datetime = kwargs.get("start_time")
        end_time = datetime.now()
        if 'end_time' in kwargs:
            end_time: datetime = kwargs.get("end_time")

        if self._trade_mode == TradeMode.BACKTEST:
            gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
            UseGateway = gateways.BacktestGateway
        elif self._trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
            gateway_name = "FutuFutures"
            UseGateway = gateways.FutuFuturesGateway  # CqgGateway

        trading_sessions = {str: list}
        for s in self.strategies:
            trading_sessions[s.code] = []
            trading_sessions[s.code].append([datetime(1970, 1, 1, 10, 30, 0, 0), datetime(1970, 1, 1, 9, 30, 0, 0)])

        gateway = UseGateway(
            securities=self.strategies,
            trade_market=trade_market,
            gateway_name=gateway_name,
            fees=fees,
            start=start_time,
            end=end_time,
            trading_sessions=trading_sessions,
            num_of_1min_bar=180
        )
        cus_quote_funcs = gateways.QuoteHookFuncs()
        if self._trade_mode != TradeMode.BACKTEST:
            cus_quote_funcs.get_recent_data_func = realtime_futures

        gateway.custom_quote_hook(funcs=cus_quote_funcs)
        gateway.SHORT_INTEREST_RATE = 0.0
        gateway.trade_mode = self._trade_mode
        if gateway.trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
            assert datetime.now() < gateway.end, (
                "Gateway end time must be later than current datetime!")
        return gateway


def new_turtle_strategy(securities: List[Futures] = None, gateway_name: str = 'Backtest',
                        engine: Engine = None, **kwargs) -> BaseStrategy:
    # Initialize strategy
    strategy_account = "future_turtle_strategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 100000
    init_account_balance = AccountBalance(cash=init_capital)

    from app.strategies.future_turtle_strategy import FutureTurtleStrategy
    strategy = FutureTurtleStrategy(
        securities={gateway_name: securities},
        strategy_account=strategy_account,
        strategy_version=strategy_version,
        init_strategy_account_balance={gateway_name: init_account_balance},
        init_strategy_position={gateway_name: init_position},
        engine=engine,
        # strategy_trading_sessions=[[datetime(1970, 1, 1, 17, 30, 0, 0),
        #                             datetime(1970, 1, 1, 8, 30, 0, 0)]]
    )
    strategy.init_strategy()
    # 更新引擎策略
    engine.update_strategy(strategy_account, strategy_version)

    return strategy


def new_high_frequency_strategy(securities: List[Futures] = None, gateway_name: str = 'Backtest',
                                engine: Engine = None, **kwargs) -> BaseStrategy:
    # Initialize strategy
    strategy_account = "future_high_frequency_strategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 100000
    init_account_balance = AccountBalance(cash=init_capital)

    from app.strategies.stock_us_high_frequency_strategy import StockUSHighFrequencyStrategy
    strategy = StockUSHighFrequencyStrategy(
        securities={gateway_name: securities},
        strategy_account=strategy_account,
        strategy_version=strategy_version,
        init_strategy_account_balance={gateway_name: init_account_balance},
        init_strategy_position={gateway_name: init_position},
        engine=engine,
        # strategy_trading_sessions=[[datetime(1970, 1, 1, 17, 30, 0, 0),
        #                             datetime(1970, 1, 1, 8, 30, 0, 0)]]
    )
    strategy.init_strategy()
    # 更新引擎策略
    engine.update_strategy(strategy_account, strategy_version)

    return strategy


def new_stock2_strategy(securities: List[Futures] = None, gateway_name: str = 'Backtest',
                        engine: Engine = None, **kwargs) -> BaseStrategy:
    # Initialize strategy
    strategy_account = "future_strategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 100000
    init_account_balance = AccountBalance(cash=init_capital)

    from app.strategies.stock_us_strategy import StockUSStrategy
    strategy = StockUSStrategy(
        securities={gateway_name: securities},
        strategy_account=strategy_account,
        strategy_version=strategy_version,
        init_strategy_account_balance={gateway_name: init_account_balance},
        init_strategy_position={gateway_name: init_position},
        engine=engine,
        # strategy_trading_sessions=[[datetime(1970, 1, 1, 17, 30, 0, 0),
        #                             datetime(1970, 1, 1, 8, 30, 0, 0)]]
    )
    strategy.init_strategy()
    # 更新引擎策略
    engine.update_strategy(strategy_account, strategy_version)

    return strategy


def initialize():
    securities = [
        Futures(code="FUT.HG23N", lot_size=1, security_name="COMEX铜2307", exchange=Exchange.COMEX),
    ]

    gateway_name = "Backtest"
    trade_mode = TradeMode.BACKTEST

    today = datetime.today()
    start_time = today - timedelta(120)
    end_time = datetime.now()
    if trade_mode == TradeMode.BACKTEST:
        start_time = datetime(2020, 1, 1, 21, 30, 0, 0)
        end_time = datetime(2023, 5, 14, 5, 0, 0, 0)
    elif trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
        start_time = today - timedelta(120)
        end_time = datetime(today.year, today.month, today.day, 23, 0, 0)

    service = EntranceService(strategies=securities,
                              gateway_name=gateway_name,
                              trade_mode=trade_mode,
                              trade_market=TradeMarket.US,
                              start_time=start_time,
                              end_time=end_time,
                              strategy_func=new_turtle_strategy,
                              )
    service.start()

    if trade_mode == TradeMode.BACKTEST:
        service.stop()


if __name__ == "__main__":
    config_file = sys.argv[1]
    application.start(config_file, initialize)
