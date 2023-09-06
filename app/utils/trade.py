from datetime import datetime, timedelta
from datetime import time as Time
from datetime import date as Date

import pandas as pd
from dateutil.parser import parse
from typing import List

import numpy as np

import warnings

def convert_tscode(code: str):
    return code + '.SH' if code.startswith('6') else code + '.SZ'


# 获取最新交易日
def latest_trade_date(self):
    d0 = datetime.now()
    if d0.hour > 16:
        d = d0.strftime('%Y%m%d')
    else:
        d = (d0 - timedelta(1)).strftime('%Y%m%d')
    while d not in self.cals:
        d1 = parse(d)
        d = (d1 - timedelta(1)).strftime('%Y%m%d')
    return d


# 获取今天日期
def get_today_date():
    now = datetime.now().strftime('%Y%m%d')
    return now


def get_trading_day(
        dt: datetime,
        daily_open_time: Time,
        daily_close_time: Time
) -> Date:
    """Get futures trading day according to daily_open_time and daily_close_time
    given."""
    if daily_open_time <= daily_close_time:
        return dt.date()
    elif daily_close_time < daily_open_time and dt.time() > daily_close_time:
        return (dt + timedelta(days=1)).date()
    elif daily_close_time < daily_open_time and dt.time() <= daily_close_time:
        return dt.date()
    else:
        warnings.warn(
            f"{dt} is NOT within {daily_open_time} and {daily_close_time}")
        return None

# 获取两个日期之间的交易日
def get_trade_date(cals:np.array, start, end):
    cals = np.sort(cals)
    n1 = np.where(cals > start)[0][0]
    n2 = np.where(cals <= end)[0][-1] + 1
    dates = cals[n1:n2]
    return dates

def get_trading_dates_by_df(kline_df:pd.DataFrame, start:datetime=None, end:datetime=None):
    """
    依据k线数据获取交易日历
    """
    d = kline_df.index.tolist()
    return d
