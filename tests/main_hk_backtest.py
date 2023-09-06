# -*- coding: utf-8 -*-

##########################################################################
#
#                          Demo strategy
##########################################################################
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

from app.strategies import StockHKStrategy

if __name__ == "__main__":

    trade_mode = TradeMode.BACKTEST
    # trade_mode = TradeMode.SIMULATE
    trade_market = TradeMarket.HK
    fees = gateways.BacktestFees
    UseGateway = gateways.BaseGateway
    gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
    UseGateway = gateways.BacktestGateway
    start = datetime(2015, 10, 2, 9, 30, 0, 0)
    end = datetime(2023, 3, 20, 16, 0, 0, 0)

    stock_list = [
        Stock(code="HK.01157", lot_size=100, security_name="中联重科", exchange=Exchange.SEHK),
        Stock(code="HK.09868", lot_size=100, security_name="小鹏汽车-W", exchange=Exchange.SEHK),
        Stock(code="HK.03800", lot_size=1000, security_name="协鑫科技", exchange=Exchange.SEHK),
        Stock(code="HK.02420", lot_size=500, security_name="子不语", exchange=Exchange.SEHK),
        Stock(code="HK.00873", lot_size=1000, security_name="世茂服务", exchange=Exchange.SEHK),
        Stock(code="HK.09939", lot_size=500, security_name="开拓药业-B", exchange=Exchange.SEHK),
        Stock(code="HK.09696", lot_size=200, security_name="天齐锂业", exchange=Exchange.SEHK),
    ]

    trading_sessions = {str: list}
    for s in stock_list:
        trading_sessions[s.code] = []
        trading_sessions[s.code].append([datetime(1970, 1, 1, 9, 30, 0, 0), datetime(1970, 1, 1, 17, 0, 0, 0)])

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

    # if "analysis" in plugins:
    #     result_path = "results/2023-03-04 21-19-14.003415/result_stockhk.csv"
    #     plot_pnl = plugins["analysis"].plot_pnl
    #     plot_pnl(result_path=result_path, freq="daily")
    #     if "dingtalk" in plugins:
    #         dingtalk_bot = plugins["dingtalk"].bot
    #         dingtalk_bot.send_text(f"{datetime.now()} {dingtalk_bot.__doc__}")
    #     exit()

    # Initialize strategy
    strategy_account = "StockHKStrategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 100000
    init_account_balance = AccountBalance(cash=init_capital)

    strategy = StockHKStrategy(
        securities={gateway_name: stock_list},
        strategy_account=strategy_account,
        strategy_version=strategy_version,
        init_strategy_account_balance={gateway_name: init_account_balance},
        init_strategy_position={gateway_name: init_position},
        engine=engine,
        strategy_trading_sessions=[[datetime(1970, 1, 1, 9, 30, 0, 0),
                                    datetime(1970, 1, 1, 19, 0, 0, 0)]]
    )
    strategy.init_strategy()

    # 更新引擎策略
    # todo: 引擎中后期要支持多个策略
    engine.update_strategy(strategy.strategy_account, strategy.strategy_version)

    # Event recorder
    recorder = BarEventEngineRecorder(datetime=[],
                                      open=[],
                                      high=[],
                                      low=[],
                                      close=[],
                                      volume=[])
    event_engine = BarEventEngine(
        strategies={"stockhk": strategy},
        recorders={"stockhk": recorder},
        engine=engine
    )

    event_engine.run()

    if "dingtalk" in plugins:
        dingtalk_bot = plugins["dingtalk"].bot
        dingtalk_bot.send_text(f"{datetime.now()} {dingtalk_bot.__doc__}")

    result_path = recorder.save_csv()

    if "analysis" in plugins:
        plot_pnl = plugins["analysis"].plot_pnl
        plot_pnl(result_path=result_path, freq="daily", auto_open=False)
    engine.log.info("Program shutdown normally.")
