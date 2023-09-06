from typing import List, Dict, Any
from datetime import datetime

from app.domain.data import Bar
from app.domain.security import Security
from app.domain.balance import AccountBalance
from app.domain.position import Position
from app.domain.portfolio import Portfolio

from app.domain.engine import Engine


class BaseStrategy:
    """Base class for strategy

        To write a strategy, override init_strategy and on_bar methods
        """

    def __init__(
            self,
            securities: Dict[str, List[Security]],  # gateway:List(Security)
            strategy_account: str,
            strategy_version: str,
            engine: Engine,
            # If not in strategy trading sessions, skip strategy.on_bar(cur_data)
            strategy_trading_sessions: List[List[datetime]] = None,
            init_strategy_account_balance: Dict[str, AccountBalance] = None,
            init_strategy_position: Dict[str, Position] = None
    ):
        self.securities = securities
        self.engine = engine
        self.strategy_account = strategy_account
        self.strategy_version = strategy_version
        self.strategy_trading_sessions = strategy_trading_sessions
        if init_strategy_account_balance is None:
            init_strategy_account_balance = {gw: AccountBalance(cash=0.0) for gw in securities}
        if init_strategy_position is None:
            init_strategy_position = {gw: Position() for gw in securities}
        self.portfolios = {}
        self.init_strategy_portfolio(
            init_strategy_account_balance=init_strategy_account_balance,
            init_strategy_position=init_strategy_position
        )
        # Record the action at each time step
        self._actions = {gateway_name: "" for gateway_name in engine.gateways}
        # Record bar data at each time step
        self._data = {
            gateway_name: {security: None for security in securities.get(gateway_name, [])}
            for gateway_name in engine.gateways
        }

    def init_strategy_portfolio(
            self,
            init_strategy_account_balance: Dict[str, AccountBalance],
            init_strategy_position: Dict[str, Position]
    ):
        """Portfolio information for a specific strategy"""
        for gateway_name in self.securities:
            gateway = self.engine.gateways[gateway_name]
            account_balance = init_strategy_account_balance[gateway_name]
            position = init_strategy_position[gateway_name]
            portfolio = Portfolio(
                account_balance=account_balance,
                position=position,
                market=gateway
            )
            self.portfolios[gateway_name] = portfolio

    def init_strategy(self, *args, **kwargs):
        raise NotImplementedError(
            "init_strategy has not been implemented yet.")

    def update_bar(self, gateway_name: str, security: Security, data: Bar):
        self._data[gateway_name][security] = data

    async def on_bar(self, cur_data: Dict[str, Dict[Security, Bar]]):
        raise NotImplementedError("on_bar has not been implemented yet.")

    def on_tick(self):
        raise NotImplementedError("on_tick has not been implemented yet.")

    def get_datetime(self, gateway_name: str) -> datetime:
        return self.engine.gateways[gateway_name].market_datetime

    def get_portfolio_value(self, gateway_name: str) -> float:
        return self.engine.portfolios[gateway_name].value

    def get_strategy_portfolio_value(self, gateway_name: str) -> float:
        return self.portfolios[gateway_name].value

    def get_account_balance(self, gateway_name: str) -> AccountBalance:
        return self.engine.portfolios[gateway_name].account_balance

    def get_strategy_account_balance(self, gateway_name: str) -> AccountBalance:
        return self.portfolios[gateway_name].account_balance

    def get_position(self, gateway_name: str) -> Position:
        return self.engine.portfolios[gateway_name].position

    def get_strategy_position(self, gateway_name: str) -> Position:
        return self.portfolios[gateway_name].position

    def get_action(self, gateway_name: str) -> str:
        return self._actions[gateway_name]

    def get_open(self, gateway_name: str) -> List[float]:
        opens = []
        for g in self.engine.gateways:
            if g == gateway_name:
                for security in self.securities[gateway_name]:
                    if self._data[gateway_name][security] is None:
                        continue
                    opens.append(self._data[gateway_name][security].open)
        return opens

    def get_high(self, gateway_name: str) -> List[float]:
        highs = []
        for g in self.engine.gateways:
            if g == gateway_name:
                for security in self.securities[gateway_name]:
                    if self._data[gateway_name][security] is None:
                        continue
                    highs.append(self._data[gateway_name][security].high)
        return highs

    def get_low(self, gateway_name: str) -> List[float]:
        lows = []
        for g in self.engine.gateways:
            if g == gateway_name:
                for security in self.securities[gateway_name]:
                    if self._data[gateway_name][security] is None:
                        continue
                    lows.append(self._data[gateway_name][security].low)
        return lows

    def get_close(self, gateway_name: str) -> List[float]:
        closes = []
        for g in self.engine.gateways:
            if g == gateway_name:
                for security in self.securities[gateway_name]:
                    if self._data[gateway_name][security] is None:
                        continue
                    closes.append(self._data[gateway_name][security].close)
        return closes

    def get_volume(self, gateway_name: str) -> List[float]:
        volumes = []
        for g in self.engine.gateways:
            if g == gateway_name:
                for security in self.securities[gateway_name]:
                    if self._data[gateway_name][security] is None:
                        continue
                    volumes.append(self._data[gateway_name][security].volume)
        return volumes

    def reset_action(self, gateway_name: str):
        self._actions[gateway_name] = ""

    def update_action(self, gateway_name: str, action: Dict[str, Any]):
        self._actions[gateway_name] += str(action)
        self._actions[gateway_name] += "|"
