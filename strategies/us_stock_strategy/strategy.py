# -*- coding: utf-8 -*-
import json
from typing import Dict, List

from app.domain.position import Position
from app.domain.balance import AccountBalance
from app.constants import Exchange, TradeMode
from app.domain.engine import Engine
from app.domain.security import Stock, Security
from app.strategies import BaseStrategy

from app.infra.db.redis_driver import get_redis_conn


def register_strategy_securities(strategy_name='', trade_mode: TradeMode = TradeMode.BACKTEST):
    if strategy_name == '':
        return

    securities = [
        Stock(code="US.NVDA", lot_size=1, security_name="英伟达", exchange=Exchange.NASDAQ),
        # Stock(code="US.PDD", lot_size=1, security_name="拼多多", exchange=Exchange.NASDAQ),
        # Stock(code="US.TSLA", lot_size=1, security_name="特斯拉", exchange=Exchange.NASDAQ),
        # Stock(code="US.MSFT", lot_size=1, security_name="微软", exchange=Exchange.NASDAQ),
        # Stock(code="US.TSM", lot_size=1, security_name="台积电", exchange=Exchange.NASDAQ),
        # Stock(code="US.APLT", lot_size=1, security_name="Applied Therapeutics", exchange=Exchange.NASDAQ),
        # Stock(code="US.XPEV", lot_size=1, security_name="小鹏汽车", exchange=Exchange.NASDAQ),
        # Stock(code="US.NIO", lot_size=1, security_name="蔚来", exchange=Exchange.NASDAQ),
        # Stock(code="US.TAL", lot_size=1, security_name="好未来", exchange=Exchange.NASDAQ),
        # Stock(code="US.AAPL", lot_size=1, security_name="苹果", exchange=Exchange.NASDAQ),
        # Stock(code="US.BILI", lot_size=1, security_name="哔哩哔哩", exchange=Exchange.NASDAQ),
        # Stock(code="US.MOMO", lot_size=1, security_name="挚文集团", exchange=Exchange.NASDAQ),
        # Stock(code="US.BIDU", lot_size=1, security_name="百度", exchange=Exchange.NASDAQ),
        # Stock(code="US.CCL", lot_size=1, security_name="嘉年华邮轮", exchange=Exchange.NASDAQ),
    ]

    if trade_mode == TradeMode.BACKTEST:
        return securities

    securities = [s.to_json() for s in securities]
    strategy_securities_dict = dict(
        strategy_name=strategy_name,
        securities=[json.loads(s) for s in securities]
    )
    strategy_securities = json.dumps(strategy_securities_dict)

    redis_client = get_redis_conn()
    redis_client.hset('quant_trader_quotes_config', strategy_name, strategy_securities)

    rest = redis_client.hget('quant_trader_quotes_config', strategy_name)
    rest = json.loads(rest)
    securities = [Stock.from_dict(s) for s in rest['securities']]
    return securities


def register_strategy_etf_securities(strategy_name: str = "", trade_mode: TradeMode = TradeMode.BACKTEST):
    if strategy_name == "":
        return

    securities = [
        Stock(code="SZ.159929", lot_size=1, security_name="医药ETF", exchange=Exchange.SZSE),
        # Stock(code="US.BIDU", lot_size=1, security_name="百度", exchange=Exchange.NASDAQ),
        # Stock(code="US.CCL", lot_size=1, security_name="嘉年华邮轮", exchange=Exchange.NASDAQ),
    ]

    if trade_mode == TradeMode.BACKTEST:
        return securities

    securities = [s.to_json() for s in securities]
    strategy_securities_dict = dict(
        strategy_name=strategy_name,
        securities=[json.loads(s) for s in securities]
    )
    strategy_securities = json.dumps(strategy_securities_dict)

    redis_client = get_redis_conn()
    redis_client.hset('quant_trader_quotes_config', strategy_name, strategy_securities)

    rest = redis_client.hget('quant_trader_quotes_config', strategy_name)
    rest = json.loads(rest)
    securities = [Stock.from_dict(s) for s in rest['securities']]
    return securities


def new_turtle_strategy(securities: List[Stock] = None, gateway_name: str = 'Backtest',
                        engine: Engine = None, **kwargs) -> BaseStrategy:
    # Initialize strategy
    strategy_account = "turtle_strategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 100000
    init_account_balance = AccountBalance(cash=init_capital)

    from app.strategies.stock_us_turtle_strategy import StockUSTurtleStrategy
    strategy = StockUSTurtleStrategy(
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


def new_high_frequency_strategy(securities: List[Stock] = None, gateway_name: str = 'Backtest',
                                engine: Engine = None, **kwargs) -> BaseStrategy:
    # Initialize strategy
    strategy_account = "high_frequency_strategy"
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


def new_stock2_strategy(securities: List[Stock] = None, gateway_name: str = 'Backtest',
                        engine: Engine = None, **kwargs) -> BaseStrategy:
    # Initialize strategy
    strategy_account = "stock2_strategy"
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


def new_grid_trading_strategy(securities: List[Stock] = None, gateway_name: str = 'Backtest',
                              engine: Engine = None, **kwargs) -> BaseStrategy:
    # Initialize strategy
    strategy_account = "grid_trading_strategy"
    strategy_version = "1.0"
    init_position = Position()
    init_capital = 100000
    init_account_balance = AccountBalance(cash=init_capital)

    from app.strategies.grid_trading_strategy import GridTradingStrategy
    strategy = GridTradingStrategy(
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
