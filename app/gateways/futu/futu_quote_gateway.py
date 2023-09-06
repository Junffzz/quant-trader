# -*- coding: utf-8 -*-

import uuid
import re
from typing import Dict, List
from datetime import datetime
import time

import pandas as pd
from futu import (
    RET_OK,
    RET_ERROR,
    SubType,
    OrderType,
    ModifyOrderOp,
    KLType,
    AuType,
    KL_FIELD,
    TrdMarket,
    TrdEnv,
    Plate,
    OrderStatus,
    SortField,
    SimpleFilter,
    FinancialFilter,
    CustomIndicatorFilter,
    OpenQuoteContext,
    OpenSecTradeContext
)

from app.constants import TradeMarket
from app.utils import BlockingDict
from app.utils.utility import try_parsing_datetime
from app.utils.utility import get_kline_dfield_from_seconds
from trader_config import GATEWAYS, DATA_PATH, TIME_STEP
from .utility import (
    convert_trade_market_qt2futu,
    convert_direction_qt2futu,
    convert_trade_mode_qt2futu,
    convert_plate_qt2futu,
    convert_orderstatus_futu2qt,
    get_hk_futures_code,
)

FUTU = GATEWAYS.get("Futu")


class FutuQuoteGateway:
    # kline type supported
    KL_ALLOWED = ("1Day", "1Min")

    def __init__(self,
                 trade_market: TradeMarket = TradeMarket.NONE,
                 ):
        gateway_name = "Futu"
        self.trd_market = convert_trade_market_qt2futu(trade_market)
        self.broker_name = GATEWAYS[gateway_name]["broker_name"]
        self.broker_account = GATEWAYS[gateway_name]["broker_account"]
        self.quote = BlockingDict()

        self.quote_ctx = OpenQuoteContext(host=FUTU["host"], port=FUTU["port"])

    def get_trading_days(self,
                         start_date: str = None,
                         end_date: str = None,
                         code: str = None
                         ) -> List:
        """
        获取交易日历
        """
        if start_date == "" or start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")
        if end_date == "" or end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        ret, data = self.quote_ctx.request_trading_days(
            market=self.trd_market,
            start=start_date,
            end=end_date,
            code=code)
        if ret == RET_OK:
            return data
        else:
            print('error:', data)
        return []

    # 条件选股
    def fetch_stock_filter(self, filter_list: List = None, plate_code=None, count=200):
        ret_list = self._api_get_stock_filter(self.trd_market, filter_list,
                                              plate_code, count)
        result = []
        for ls in ret_list:
            result.extend(ls)
        return result

    def _api_get_stock_filter(self, market: TrdMarket, filter_list: List = None, plate_code=None, num=200):
        if filter_list is None:
            return

        n_begin = 0
        last_page = False
        ret_list = list()
        while not last_page:  # 请求后面的所有结果
            n_begin += len(ret_list)
            ret, ls = self.quote_ctx.get_stock_filter(
                market,
                filter_list=filter_list,
                plate_code=plate_code,
                begin=n_begin,
                num=num,
            )  # 请求翻页后的数据
            if ret == RET_OK:
                last_page, all_count, ret_list = ls
                yield ret_list
            else:
                print('error:', ls)
                return
            time.sleep(3)  # 加入时间间隔，避免触发限频

    # 获取板块列表
    def get_plate_list(self, plate: str = "ALL") -> pd.DataFrame:
        """
        获取子板块代码，条件选股支持的板块分别为
        港股的行业板块和概念板块。
        美股的行业板块
        沪深的行业板块，概念板块和地域板块
        """
        ft_plate = convert_plate_qt2futu(plate)
        ret, data = self.quote_ctx.get_plate_list(self.trd_market, ft_plate)
        if ret == RET_OK:
            return data
        else:
            print('get_plate_list error:', data)
        return pd.DataFrame()

    # 获取板块内股票列表
    def get_plate_stocks(self, plate_code, sort_field=SortField.CODE, ascend=True) -> pd.DataFrame:
        ret, data = self.quote_ctx.get_plate_stock(plate_code, sort_field, ascend)
        if ret == RET_OK:
            return data
        else:
            print('get_plate_stocks error:', data)
        return pd.DataFrame()
