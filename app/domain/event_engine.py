# -*- coding: utf-8 -*-
import json
import os
from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd

import redis
import aioredis

from app.domain.data import Bar
from app.constants import TradeMode
from app.domain.engine import Engine
from app.strategies.base_strategy import BaseStrategy
from app.utils.utility import timeit
from app.utils import logger
from app.utils.tasks import SingleTask, LoopRunTask
from trader_config import TIME_STEP
from app.config.configure import config


class BarEventEngineRecorder:
    """记录bar事件过程的变量"""

    def __init__(self, **kwargs):
        self.recorded_methods = {"datetime": "append", "portfolio_value": "append",
                                 "strategy_portfolio_value": "append"}
        self.recorder_name = None
        self.datetime = []
        self.portfolio_value = []
        self.strategy_portfolio_value = []
        for k, v in kwargs.items():
            if v is None:
                self.recorded_methods[str(k)] = "override"
            elif isinstance(v, list) and len(v) == 0:
                self.recorded_methods[str(k)] = "append"
            else:
                raise ValueError(f"BarEventEngineRecorder 的输入参数{k}的类型为{type(v)}, 只有[]或None是合法的输入")
            setattr(self, k, v)

    def get_recorded_fields(self):
        return list(self.recorded_methods.keys())

    def write_record(self, field, value):
        record = getattr(self, field, None)
        if self.recorded_methods[field] == "append":
            record.append(value)
        elif self.recorded_methods[field] == "override":
            setattr(self, field, value)

    def set_recorder_name(self, name: str):
        self.recorder_name = name

    def save_csv(self, path=None):
        """保存所有记录变量至csv"""
        vars = [attr for attr in dir(self) if not callable(getattr(self, attr)) and not attr.startswith("__")]
        assert "datetime" in vars, "`datetime` is not in the recorder!"
        assert "portfolio_value" in vars, "`portfolio_value` is not in the recorder!"
        assert "strategy_portfolio_value" in vars, "`strategy_portfolio_value` is not in the recorder!"
        save_dir = config.recorder.get('path')
        if path is None:
            path = save_dir + "/results"
        if not os.path.exists(path):
            os.mkdir(path)
        now = datetime.now()
        now = now.strftime('%Y-%m-%d %H-%M-%S.%f')
        os.mkdir(f"{path}/{now}")

        dt = getattr(self, "datetime")
        pv = getattr(self, "portfolio_value")
        df = pd.DataFrame([dt, pv], index=["datetime", "portfolio_value"]).T
        for var in vars:
            if var in ("datetime", "portfolio_value", "recorded_methods", "recorder_name"):
                continue
            v = getattr(self, var)
            if self.recorded_methods[var] == "append":
                df[var] = v
            elif self.recorded_methods[var] == "override":
                df[var] = None

                if isinstance(v, list) and len(v) > 0 and isinstance(v[0][0], datetime) and isinstance(v[0][1], str):
                    for i in range(len(v)):
                        date_time = v[i][0]
                        idx = df[df["datetime"] == date_time].index[0]
                        if df.loc[idx, var] is None:
                            df.loc[idx, var] = v[i][1]
                        elif isinstance(df.loc[idx, var], str):
                            df.loc[idx, var] = df.loc[idx, var] + "; " + v[i][1]
                else:
                    df.iloc[len(dt) - 1, df.columns.get_loc(var)] = str(v)
        save_name = "result"
        if self.recorder_name is not None and self.recorder_name != "":
            save_name += "_" + self.recorder_name
        result_path = f"{path}/{now}/{save_name}.csv"
        df.to_csv(result_path, index=False)
        return result_path


class BarEventEngine:
    """
    Bar事件框架
    """

    def __init__(self,
                 strategies: Dict[str, BaseStrategy],
                 recorders: Dict[str, BarEventEngineRecorder],
                 start: datetime = None,
                 end: datetime = None,
                 engine: Engine = None,
                 ):

        self.rClient = None
        self._load_redis()

        self.strategies = strategies
        self.recorders = recorders
        self.engine = engine
        self.trade_modes = {}  # 存储不同gateway的交易模式
        starts = {}
        ends = {}
        for gateway_name in self.engine.gateways:
            # mode用于判断是回测模式还是实盘模式
            self.trade_modes[gateway_name] = self.engine.gateways[gateway_name].trade_mode
            # 确定模式之后，尝试同步券商的资金和持仓信息（回测模式下不会有任何变化）
            self.engine.sync_broker_balance(gateway_name=gateway_name)
            self.engine.sync_broker_position(gateway_name=gateway_name)
            # 输出初始账户资金和持仓
            logger.info(self.engine.get_balance(gateway_name=gateway_name))
            logger.info(self.engine.get_all_positions(gateway_name=gateway_name))
            # 确定起始和截止时间
            starts[gateway_name] = self.engine.gateways[gateway_name].start
            ends[gateway_name] = self.engine.gateways[gateway_name].end
        starts = [starts[gn] for gn in starts if isinstance(starts[gn], datetime)]
        ends = [ends[gn] for gn in ends if isinstance(ends[gn], datetime)]
        self.start = min(starts) if start is None else start
        self.end = max(ends) if end is None else end

        self._backtest_all_data = pd.DataFrame()
        self._load_backtest_securities_data()

    def _load_redis(self):
        host = config.redis.get("host", "localhost")
        port = config.redis.get("port", "6379")
        password = config.redis.get("password", "")
        db = config.redis.get("db", 1)
        pool = redis.ConnectionPool(host=host, port=port, password=password, db=db)
        self.rClient = redis.Redis(connection_pool=pool)

    def _load_backtest_securities_data(self):
        is_backtest = False
        gateways = self.engine.gateways
        for gateway in gateways.values():
            if gateway.trade_mode == TradeMode.BACKTEST:
                is_backtest = True
                break
        if is_backtest is False:
            return

        from app.domain.stores.security_market_storer import SecurityMarketStorer
        storer = SecurityMarketStorer(local=False)
        securities = []
        for strategy in self.strategies.values():
            for secList in strategy.securities.values():
                securities.extend(secList)
        self._backtest_all_data = storer.get_kline_data(securities, start=self.start, end=self.end)

    @timeit
    def run(self):
        engine = self.engine
        engine.start()
        # todo: 一个engine只绑定一个策略
        gateways = self.engine.gateways
        for strategy_name in self.strategies.keys():
            recorder = self.recorders[strategy_name]
            recorder.set_recorder_name(strategy_name)

            for gateway_name in gateways:
                gateway = gateways[gateway_name]
                if gateway.trade_mode == TradeMode.BACKTEST:
                    SingleTask.run(self.strategy_backtest_callback, strategy_name=strategy_name, recorder=recorder,
                                   gateway=gateway)
                    continue
                SingleTask.run(self.strategy_real_callback, strategy_name=strategy_name, recorder=recorder,
                               gateway=gateway)

    def stop(self):
        self.engine.stop()
        logger.info("到达预期结束时间，策略停止（其他工作任务线程将会在1分钟内停止）")

    async def strategy_backtest_callback(self, *args, **kwargs):
        gateway = kwargs.get("gateway")
        cur_datetime = datetime.now() if self.start is None else self.start
        while cur_datetime <= self.end:
            cur_datetime += timedelta(milliseconds=TIME_STEP)
            cur_datetime = datetime.combine(cur_datetime.date(), datetime.min.time())

            df = self._backtest_all_data.loc[
                self._backtest_all_data['time_key'] == cur_datetime.strftime('%Y-%m-%d %H:%M:%S')]
            df = df.rename(columns={'time_key': 'datetime'})
            gateway.market_datetime = cur_datetime
            kwargs['data'] = df
            await self.on_strategy_callback(*args, **kwargs)

    async def strategy_real_callback(self, *args, **kwargs):
        host = config.redis.get("host", "localhost")
        port = config.redis.get("port", "6379")
        password = config.redis.get("password", "")
        db = config.redis.get("db", 1)
        client = await aioredis.create_redis(f"redis://{host}:{port}", password=password, db=int(db))
        channels = await client.subscribe('quant_trader_quotes_channel')  # 订阅频道
        assert isinstance(channels[0], aioredis.Channel)

        channel = channels[0]
        while await channel.wait_message():
            message = await channel.get_json()
            message = json.dumps(message)
            df = pd.read_json(message)
            kwargs['data'] = df
            await self.on_strategy_callback(*args, **kwargs)

    async def on_strategy_callback(self, *args, **kwargs):
        strategy_name = kwargs.get("strategy_name")
        recorder: BarEventEngineRecorder = kwargs.get("recorder")
        gateway = kwargs.get("gateway")
        gateway_name = gateway.gateway_name
        df: pd.DataFrame = kwargs.get("data")

        # engine = self.engine
        # gateways = engine.gateways
        strategy = self.strategies[strategy_name]
        securities = strategy.securities

        trade_mode = self.trade_modes[gateway_name]

        # 获取每只股票的最新bar数据(按 gateway_name 进行划分)
        cur_data = {}
        cur_gateway_data = {}
        for security in securities[gateway_name]:
            data = df.loc[df['code'] == security.code].squeeze()
            if data.empty:
                continue
            # bar_time = datetime.strptime(
            #     data["datetime"], "%Y-%m-%d %H:%M:%S")
            bar = Bar(
                datetime=data["datetime"],
                security=security,
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                volume=data["volume"])

            if bar is None:
                continue

            cur_gateway_data[security] = bar
            strategy.update_bar(gateway_name, security, bar)

        cur_data[gateway_name] = cur_gateway_data
        # 运行策略
        try:
            await strategy.on_bar(cur_data)
        except:
            logger.exception("strategy.on_bar fail.", cur_data=cur_data, caller=self)

        gw_value = {field: [] for field in recorder.get_recorded_fields()}

        for field in recorder.get_recorded_fields():
            value = getattr(strategy, f"get_{field}")(gateway_name)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            gw_value[field].append(value)

        for field in recorder.get_recorded_fields():
            recorder.write_record(field, gw_value[field])

        # 重置操作
        strategy.reset_action(gateway_name)
        # # 通过控件来中断程序运行：
        # if False:
        #     for gateway_name in gateways:
        #         gateway = gateways[gateway_name]
        #         gateway.close()
        #     engine.stop()
        #     logger.info("程序被人手终止")
        #     return

        # 更新事件循环时间戳
        if trade_mode == TradeMode.BACKTEST:
            return
        elif trade_mode in (TradeMode.LIVETRADE, TradeMode.SIMULATE):
            return
