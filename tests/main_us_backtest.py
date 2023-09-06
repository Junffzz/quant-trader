# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(sys.path[0]))

from datetime import datetime

from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.event_engine import BarEventEngineRecorder, BarEventEngine
from app.domain.engine import Engine
from app.domain.balance import AccountBalance
from app.domain.position import Position
from app.domain.security import Stock
import app.gateways as gateways

from app.strategies import StockUSStrategy


def analysis_performance(gateway_name: str = "", stocks: [Stock] = None, result_path: str = None):
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
            start=datetime(2020, 1, 1, 9, 30, 0),
            end=datetime(2023, 3, 17, 23, 0, 0)
        )


if __name__ == "__main__":
    trade_mode = TradeMode.BACKTEST
    # trade_mode = TradeMode.SIMULATE
    trade_market = TradeMarket.US
    fees = gateways.BacktestFees
    UseGateway = gateways.BaseGateway
    gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
    UseGateway = gateways.BacktestGateway
    start = datetime(2020, 1, 1, 0, 0, 0, 0)
    # start = datetime(2022, 1, 1, 0, 0, 0, 0)
    end = datetime(2023, 3, 17, 16, 0, 0, 0)

    stock_list = [
        # Stock(code="PDD", lot_size=1, security_name="拼多多", exchange=Exchange.NASDAQ),
        # Stock(code="XPEV", lot_size=1, security_name="小鹏汽车", exchange=Exchange.NASDAQ),
        # Stock(code="NIO", lot_size=1, security_name="蔚来", exchange=Exchange.NASDAQ),
        # Stock(code="TAL", lot_size=1, security_name="好未来", exchange=Exchange.NASDAQ),
        Stock(code="BILI", lot_size=1, security_name="哔哩哔哩", exchange=Exchange.NASDAQ),
        # Stock(code="TSLA", lot_size=1, security_name="特斯拉", exchange=Exchange.NASDAQ),
        # Stock(code="MOMO", lot_size=1, security_name="挚文集团", exchange=Exchange.NASDAQ),
        # Stock(code="BIDU", lot_size=1, security_name="百度", exchange=Exchange.NASDAQ),
        # Stock(code="CCL", lot_size=1, security_name="嘉年华邮轮", exchange=Exchange.NASDAQ),
    ]

    trading_sessions = {str: list}
    for s in stock_list:
        trading_sessions[s.code] = []
        trading_sessions[s.code].append([datetime(1970, 1, 1, 17, 30, 0, 0), datetime(1970, 1, 1, 10, 0, 0, 0)])

    gateway = UseGateway(
        securities=stock_list,
        trade_market=trade_market,
        gateway_name=gateway_name,
        fees=fees,
        start=start,
        end=end,
        trading_sessions=trading_sessions,
        num_of_1min_bar=180
    )

    gateway.SHORT_INTEREST_RATE = 0.0
    gateway.trade_mode = trade_mode
    if gateway.trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
        assert datetime.now() < gateway.end, (
            "Gateway end time must be later than current datetime!")

    # Engine
    engine = Engine(gateways={gateway_name: gateway})

    # get activated plugins
    plugins = engine.get_plugins()

    # Initialize strategy
    strategy_account = "StockUSStrategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 10000
    init_account_balance = AccountBalance(cash=init_capital)

    strategy = StockUSStrategy(
        securities={gateway_name: stock_list},
        strategy_account=strategy_account,
        strategy_version=strategy_version,
        init_strategy_account_balance={gateway_name: init_account_balance},
        init_strategy_position={gateway_name: init_position},
        engine=engine,
        # strategy_trading_sessions=[[datetime(1970, 1, 1, 9, 30, 0, 0),
        #                             datetime(1970, 1, 1, 19, 0, 0, 0)]]
    )
    strategy.init_strategy(start=start, end=end)

    # 更新引擎策略
    # todo: 引擎中后期要支持多个策略
    engine.update_strategy(strategy.strategy_account, strategy.strategy_version)

    # Event recorder
    recorder = BarEventEngineRecorder(datetime=[],
                                      action=[],
                                      open=[],
                                      high=[],
                                      low=[],
                                      close=[],
                                      volume=[])
    event_engine = BarEventEngine(
        strategies={"stock_us": strategy},
        recorders={"stock_us": recorder},
        engine=engine
    )

    event_engine.run()

    result_path = recorder.save_csv()

    # if "dingtalk" in plugins:
    #     dingtalk_bot = plugins["dingtalk"].bot
    #     dingtalk_bot.send_text(f"{datetime.now()} {dingtalk_bot.__doc__}")
    #

    analysis_performance(gateway_name, stock_list, result_path)

    engine.log.info("Program shutdown normally.")
