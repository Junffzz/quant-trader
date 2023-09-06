# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import asyncio

from typing import Dict, List
from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.event_engine import BarEventEngineRecorder, BarEventEngine
from app.domain.engine import Engine
from app.domain.balance import AccountBalance
from app.domain.position import Position
from app.facade.trade import realtime_data
from app.domain.security import Stock, Security
from app.domain.data import Bar
import app.gateways as gateways
from app.utils import logger
from app.utils.tasks import SingleTask

from app.strategies import BaseStrategy
from app.strategies.stock_us_high_frequency_strategy import StockUSHighFrequencyStrategy
from app.strategies.stock_us_turtle_strategy import StockUSTurtleStrategy


def get_gateways(securities: List[Security] = None, trading_sessions: Dict[str, List] = None) -> Dict[
    str, gateways.BaseGateway]:
    fees = gateways.BacktestFees
    today = datetime.today()
    cus_quote_funcs = gateways.QuoteHookFuncs()

    ret = dict()
    ret['Backtest'] = gateways.BacktestGateway(
        securities=securities,
        trade_market=TradeMarket.US,
        gateway_name='Backtest',
        fees=fees,
        start=datetime(2020, 1, 1, 9, 30, 0, 0),
        end=datetime(today.year, today.month, today.day, 16, 0, 0),
        trading_sessions=trading_sessions,
        num_of_1min_bar=180
    )
    ret['Backtest'].SHORT_INTEREST_RATE = 0.0
    ret['Backtest'].trade_mode = TradeMode.BACKTEST

    cus_quote_funcs.get_recent_data = realtime_stock
    # ret['Futu'] = gateways.FutuGateway(
    #     securities=securities,
    #     trade_market=TradeMarket.US,
    #     gateway_name='Futu',
    #     fees=fees,
    #     start=today - timedelta(120),
    #     end=datetime(today.year, today.month, today.day, 23, 0, 0),
    #     trading_sessions=trading_sessions,
    #     num_of_1min_bar=180
    # )
    # ret['Futu'].custom_quote_hook(funcs=cus_quote_funcs)
    # ret['Futu'].SHORT_INTEREST_RATE = 0.0
    # ret['Futu'].trade_mode = TradeMode.SIMULATE

    # if gateway.trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
    #     assert datetime.now() < gateway.end, (
    #         "Gateway end time must be later than current datetime!")
    return ret


def realtime_stock(securities=None) -> {str: Bar}:
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


def analysis_performance(plugins, gateway_name: str = "", securities: [Security] = None, result_path: str = None):
    if "analysis" in plugins:
        plot_pnl = plugins["analysis"].plot_pnl
        plot_pnl(result_path=result_path, freq="daily", auto_open=True)

        instruments = {
            "security": {
                # ["FUT.GC", "FUT.SI", "FUT.CO"], ["HK.MHImain", "HK.HHImain"]
                gateway_name: [row.code for row in securities],
            },
            "lot": {
                gateway_name: [row.lot_size for row in securities],  # [100, 5000, 1000], [10, 50]
            },
            "commission": {
                gateway_name: [1.92 for row in securities],  # [1.92, 1.92, 1.92]  [10.1, 10.1]
            },
            "slippage": {
                gateway_name: [0.0 for row in securities],  # [0.0, 0.0, 0.0], [0.0, 0.0]
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


class USEntranceService:
    def __init__(self,
                 trade_mode: TradeMode = TradeMode.BACKTEST,
                 strategies: List[BaseStrategy] = None,
                 engine: Engine = None,
                 ):
        """
        gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
        """
        self._trade_mode = trade_mode

        # Engine
        self.engine = engine

        # Event recorder
        recorder = BarEventEngineRecorder(datetime=[],
                                          action=[],
                                          open=[],
                                          high=[],
                                          low=[],
                                          close=[],
                                          volume=[])

        map_strategies = {}
        recorders = {}
        for t in strategies:
            map_strategies[t.strategy_account + t.strategy_version] = t
            recorders[t.strategy_account + t.strategy_version] = recorder

        event_engine = BarEventEngine(
            strategies=map_strategies,
            recorders=recorders,
            engine=self.engine
        )
        event_engine.run()

        # for t in strategies:
        #     if self._trade_mode == TradeMode.BACKTEST:
        #         SingleTask.run(self._shutdown_backtest_callback, securities=t.securities['Backtest'], recorder=recorder)
        # if self._trade_mode == TradeMode.BACKTEST:
        #     asyncio.get_event_loop().stop()
        logger.info("Program shutdown normally.")

    async def _shutdown_backtest_callback(self, *args, **kwargs):
        gateway_name = kwargs.get("gateway_name")
        securities = kwargs.get("securities")
        recorder: BarEventEngineRecorder = kwargs.get("recorder")
        result_path = recorder.save_csv()

        # get activated plugins
        plugins = self.engine.get_plugins()
        analysis_performance(plugins, gateway_name, securities, result_path)
        return
