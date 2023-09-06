from datetime import datetime
from typing import Dict, List

import pandas as pd

from futu import (
    SortDir,
    FinancialQuarter,
    KLType,
    RelativePosition,
    StockField,
    SortField,
    SimpleFilter,
    FinancialFilter,
    CustomIndicatorFilter,
)

from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.data import Bar
import app.gateways as gateways
from app.domain.security import Stock
from app.plugins.dingtalk import bot as chatbot


def common_filter():
    simple_filter = SimpleFilter()
    simple_filter.filter_min = 2
    simple_filter.filter_max = 1000
    simple_filter.stock_field = StockField.CUR_PRICE
    simple_filter.is_no_filter = False
    # simple_filter.sort = SortDir.ASCEND

    return [simple_filter]


def buy_filter():
    ma1_filter = CustomIndicatorFilter()
    ma1_filter.ktype = KLType.K_DAY
    ma1_filter.stock_field1 = StockField.MA5
    ma1_filter.stock_field2 = StockField.MA10
    ma1_filter.relative_position = RelativePosition.CROSS_UP
    ma1_filter.is_no_filter = False

    ma2_filter = CustomIndicatorFilter()
    ma2_filter.ktype = KLType.K_DAY
    ma2_filter.stock_field1 = StockField.MA10
    ma2_filter.stock_field2 = StockField.MA20
    ma2_filter.relative_position = RelativePosition.CROSS_UP
    ma2_filter.is_no_filter = False

    ma3_filter = CustomIndicatorFilter()
    ma3_filter.ktype = KLType.K_DAY
    ma3_filter.stock_field1 = StockField.MA20
    ma3_filter.stock_field2 = StockField.MA30
    ma3_filter.relative_position = RelativePosition.CROSS_UP
    ma3_filter.is_no_filter = False

    ma4_filter = CustomIndicatorFilter()
    ma4_filter.ktype = KLType.K_DAY
    ma4_filter.stock_field1 = StockField.MA30
    ma4_filter.stock_field2 = StockField.MA60
    ma4_filter.relative_position = RelativePosition.CROSS_UP
    ma4_filter.is_no_filter = False

    ma5_filter = CustomIndicatorFilter()
    ma5_filter.ktype = KLType.K_DAY
    ma5_filter.stock_field1 = StockField.MA60
    ma5_filter.stock_field2 = StockField.MA120
    ma5_filter.relative_position = RelativePosition.CROSS_UP
    ma5_filter.is_no_filter = False
    return [ma1_filter, ma2_filter, ma3_filter, ma4_filter, ma5_filter]


def sell_filter():
    ma1_filter = CustomIndicatorFilter()
    ma1_filter.ktype = KLType.K_DAY
    ma1_filter.stock_field1 = StockField.MA5
    ma1_filter.stock_field2 = StockField.MA10
    ma1_filter.relative_position = RelativePosition.CROSS_DOWN
    ma1_filter.is_no_filter = False

    ma2_filter = CustomIndicatorFilter()
    ma2_filter.ktype = KLType.K_DAY
    ma2_filter.stock_field1 = StockField.MA10
    ma2_filter.stock_field2 = StockField.MA20
    ma2_filter.relative_position = RelativePosition.CROSS_DOWN
    ma2_filter.is_no_filter = False

    ma3_filter = CustomIndicatorFilter()
    ma3_filter.ktype = KLType.K_DAY
    ma3_filter.stock_field1 = StockField.MA20
    ma3_filter.stock_field2 = StockField.MA30
    ma3_filter.relative_position = RelativePosition.CROSS_DOWN
    ma3_filter.is_no_filter = False

    ma4_filter = CustomIndicatorFilter()
    ma4_filter.ktype = KLType.K_DAY
    ma4_filter.stock_field1 = StockField.MA30
    ma4_filter.stock_field2 = StockField.MA60
    ma4_filter.relative_position = RelativePosition.CROSS_DOWN
    ma4_filter.is_no_filter = False

    ma5_filter = CustomIndicatorFilter()
    ma5_filter.ktype = KLType.K_DAY
    ma5_filter.stock_field1 = StockField.MA60
    ma5_filter.stock_field2 = StockField.MA120
    ma5_filter.relative_position = RelativePosition.CROSS_DOWN
    ma5_filter.is_no_filter = False

    return [ma1_filter, ma2_filter, ma3_filter, ma4_filter, ma5_filter]


def fetch_stocks_filter():
    """
    策略思想：
    选股池：
    1.长期处于均线下降趋势
    2.处于价格底部，比如低于52周低价
    3.MACD处于底部

    买卖信号：
    1.期待反转
    2.技术指标
    """
    trade_market = TradeMarket.HK
    fees = gateways.BaseFees

    gateway_name = "Futu"
    gateway = gateways.FutuQuoteGateway(trade_market)

    buy_filter_list = []
    buy_filter_list.extend(common_filter())
    buy_filter_list.extend(buy_filter())
    buy_stocks = gateway.fetch_stock_filter(filter_list=buy_filter_list)

    sell_filter_list = []
    sell_filter_list.extend(common_filter())
    sell_filter_list.extend(sell_filter())
    sell_stocks = gateway.fetch_stock_filter(filter_list=sell_filter_list)
    send_message(buy_stocks, sell_stocks)
    print("send_message success.")


def send_message(buy_stocks=[], sell_stocks=[]):
    if len(buy_stocks) == 0 and len(sell_stocks) == 0:
        return
    content = ''
    content += 'buy signal:'
    for row in buy_stocks:
        content += row["stock_code"] + ":" + row["cur_price"]

    content += 'sell signal:'
    for row in sell_stocks:
        content += row["stock_code"] + ":" + row["cur_price"]
    chatbot.send_markdown("filter hk stocks", content)


if __name__ == '__main__':
    fetch_stocks_filter()
    exit()
