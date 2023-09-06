# -*- coding: utf-8 -*-

##########################################################################
#
#                          Demo strategy
##########################################################################
from datetime import datetime

from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.event_engine import BarEventEngineRecorder, BarEventEngine
from app.domain.engine import Engine
from app.domain.balance import AccountBalance
from app.domain.position import Position
from app.domain.security import Stock, Futures
import app.gateways as gateways

from app.strategies import DemoStrategy

if __name__ == "__main__":

    # trade_mode = TradeMode.BACKTEST
    trade_mode = TradeMode.SIMULATE
    trade_market = TradeMarket.US
    fees = gateways.BacktestFees
    UseGateway = gateways.BaseGateway
    start = datetime.now()
    end = datetime.now()
    if trade_mode == TradeMode.BACKTEST:
        gateway_name = "Backtest"  # "Futufutures", "Backtest", "Cqg", "Ib"
        UseGateway = gateways.BacktestGateway
        start = datetime(2021, 3, 15, 9, 30, 0, 0)
        end = datetime(2021, 3, 17, 16, 0, 0, 0)
    elif trade_mode in (TradeMode.SIMULATE, TradeMode.LIVETRADE):
        gateway_name = "Futu"
        UseGateway = gateways.FutuGateway  # CqgGateway
        start = datetime(2023, 2, 20, 9, 30, 0, 0)
        today = datetime.today()
        end = datetime(today.year, today.month, today.day, 23, 0, 0)

    stock_list = [
        # Futures(code="FUT.GC", lot_size=100, security_name="GCQ2",
        #         exchange=Exchange.NYMEX, expiry_date="20220828"),
        # Futures(code="FUT.SI", lot_size=5000, security_name="SIN2",
        #         exchange=Exchange.NYMEX, expiry_date="20220727"),

        # Stock(code="HK.09868", lot_size=100, security_name="小鹏汽车-W", exchange=Exchange.SEHK),
        # Stock(code="HK.03800", lot_size=100, security_name="协鑫科技", exchange=Exchange.SEHK),
        # Stock(code="HK.02150", lot_size=100, security_name="奈雪的茶", exchange=Exchange.SEHK),

        Stock(code="US.XPEV", lot_size=100, security_name="小鹏汽车", exchange=Exchange.NASDAQ),
        Stock(code="US.TSLA", lot_size=100, security_name="特斯拉", exchange=Exchange.NASDAQ),
        Stock(code="US.TAL", lot_size=100, security_name="好未来", exchange=Exchange.NASDAQ),
        Stock(code="US.PDD", lot_size=100, security_name="拼多多", exchange=Exchange.NASDAQ),
        Stock(code="US.QTT", lot_size=100, security_name="趣头条", exchange=Exchange.NASDAQ),
        Stock(code="US.BILI", lot_size=100, security_name="哔哩哔哩", exchange=Exchange.NASDAQ),
    ]

    trading_sessions = {str: list}
    for s in stock_list:
        trading_sessions[s.code] = []
        trading_sessions[s.code].append([datetime(1970, 1, 1, 17, 30, 0, 0), datetime(1970, 1, 1, 8, 30, 0, 0)])

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
    #     result_path="results/2023-02-25 06-31-22.643593/result.csv"
    #     plot_pnl = plugins["analysis"].plot_pnl
    #     plot_pnl(result_path=result_path, freq="daily")
    #     exit()

    # Initialize strategy
    strategy_account = "DemoStrategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 100000
    init_account_balance = AccountBalance(cash=init_capital)

    strategy = DemoStrategy(
        securities={gateway_name: stock_list},
        strategy_account=strategy_account,
        strategy_version=strategy_version,
        init_strategy_account_balance={gateway_name: init_account_balance},
        init_strategy_position={gateway_name: init_position},
        engine=engine,
        strategy_trading_sessions=[[datetime(1970, 1, 1, 17, 30, 0, 0),
                                    datetime(1970, 1, 1, 8, 30, 0, 0)]]
    )
    strategy.init_strategy()

    # Event recorder
    recorder = BarEventEngineRecorder(datetime=[],
                                      open=[],
                                      high=[],
                                      low=[],
                                      close=[],
                                      volume=[])
    event_engine = BarEventEngine(
        strategies={"demo": strategy},
        recorders={"demo": recorder},
        engine=engine
    )

    if "telegram" in plugins:
        telegram_bot = plugins["telegram"].bot
        telegram_bot.send_message(f"{datetime.now()} {telegram_bot.__doc__}")
    event_engine.run()

    result_path = recorder.save_csv()

    if "analysis" in plugins:
        plot_pnl = plugins["analysis"].plot_pnl
        plot_pnl(result_path=result_path, freq="daily")
    engine.log.info("Program shutdown normally.")
