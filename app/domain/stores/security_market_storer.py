#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from enum import Enum
from datetime import datetime

import pandas as pd

import app.facade as facade
import app.constants.stock as stock_const
import app.constants.common as com_const
from app.domain.data import _get_data
from app.domain.security import Stock, Security
from trader_config import DATA_PATH, DATA_MODEL, TIME_STEP, DATA_FFILL

assert set(DATA_PATH.keys()) == set(DATA_MODEL.keys()), (
    "`DATA_PATH` and `DATA_MODEL` keys are not aligned! Please check "
    "trader_config.py"
)


class SecurityMarketStorer:
    def __init__(self, local: bool = False):
        self._local = local

    # 股票代码
    def get_codelist(self, market: Enum = com_const.MarketEnum.A):
        if market == com_const.MarketEnum.HK:
            stock_json = stock_const.HK_SHARE_STOCKS_JSON
        elif market == com_const.MarketEnum.US:
            stock_json = stock_const.US_SHARE_STOCKS_JSON
        else:
            stock_json = stock_const.A_SHARE_STOCKS_JSON

        json_str = json.dumps(stock_json)
        df = pd.DataFrame(json.loads(json_str))
        # filter data
        if market == com_const.MarketEnum.A:
            df = df.drop(df[df['name'].str.contains('B') | df['name'].str.contains('ST')].index)
        return tuple(df['symbol'].sort_values())

    def get_kline_data(self, securities: [Stock], start: datetime, end: datetime = None, freq='d',
                       fqt=1) -> pd.DataFrame:
        """
        获取股票K线数据，A股、港股、美股
        """
        fields = ["time_key", "code", "open", "high", "low", "close", "volume"]
        result = pd.DataFrame()
        if self._local:
            for security in securities:
                dtypes = dict(
                    kline=fields)
                for dfield in DATA_PATH.keys():
                    data = _get_data(
                        security=security,
                        start=start,
                        end=end,
                        dfield=dfield,
                        dtype=dtypes[dfield])

                    result = pd.concat([result, data], ignore_index=True)
            return result

        code_list = [security.code.split(".")[1] for security in securities]
        data = facade.get_data(code_list, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), freq, fqt)
        data.reset_index(inplace=True)
        data['time_key'] = data['date']
        data.drop(columns=['date'], inplace=True)
        for security in securities:
            data.loc[data['code'] == security.code.split(".")[1], 'code'] = security.code
        # data['time_key'] = data['time_key'].apply(lambda x: x.to_pydatetime().strftime("%Y-%m-%d 00:00:00"))
        result = pd.concat([result, data], ignore_index=True)
        result = result[fields]
        return result

    def get_market_realtime(self, market='沪深A'):
        '''
        市场行情数据
        获取沪深市场最新行情总体情况（涨跌幅、换手率等信息）
         market表示行情名称或列表，默认沪深A股
        '沪深京A':沪深京A股市场行情; '沪深A':沪深A股市场行情;'沪A':沪市A股市场行情
        '深A':深市A股市场行情;北A :北证A股市场行情;'可转债':沪深可转债市场行情;
        '期货':期货市场行情;'创业板':创业板市场行情;'美股':美股市场行情;
        '港股':港股市场行情;'中概股':中国概念股市场行情;'新股':沪深新股市场行情;
        '科创板':科创板市场行情;'沪股通' 沪股通市场行情;'深股通':深股通市场行情;
        '行业板块':行业板块市场行情;'概念板块':概念板块市场行情;
        '沪深指数':沪深系列指数市场行情;'上证指数':上证系列指数市场行情
        '深证指数':深证系列指数市场行情;'ETF' ETF基金市场行情;'LOF' LOF 基金市场行情
        '''
        return facade.market_realtime(market)

    def get_stock_realtime(self, code_list) -> pd.DataFrame:
        """
        获取股票、期货、债券的最新行情指标
        code_list:输入单个或多个证券的list
        """
        df = facade.stock_realtime(code_list)
        return df
