# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd


def append_kdj(df):
    '''calculate kdj'''
    # 9天的最低价
    lowest = df['low'].rolling(9).min()
    lowest.fillna(value=df['low'].expanding().min(), inplace=True)

    # 9天的最高价
    highest = df['high'].rolling(9).max()
    highest.fillna(value=df['high'].expanding().max(), inplace=True)

    # 计算RSV
    rsv = (df.close - lowest) / (highest - lowest) * 100
    # 前面9天是nan,填充为100.0
    rsv.fillna(value=100.0, inplace=True)

    # 分别计算k,d,j 注意，这里adjust要用False
    df['kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
    df['kdj_d'] = df['kdj_k'].ewm(com=2, adjust=False).mean()
    df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']


def position_stop_high_price(src_df: pd.DataFrame, stop_price_pct: float = -0.05):
    """
    基于持仓历史最高价止损：
    1.当价格低于5%卖出
    params:
    src_df: pd.DataFrame
    stop_price_pct: 止损价跌幅
    """
    df = src_df.copy()
    # 买入仓位
    df.loc[(df['position'] > df['position'].shift(1)) & (df['position'].shift(1) == 0), 'position_max_price'] = df.close
    # 价格止损
    df['position_max_price'] = df[df['position'] == 1].close.max()
    df['position_change_price'].fillna(method='ffill', inplace=True)
    df['position_change_pct'] = (df.close.values - df.position_change_price.values) / df['position_change_price'].values
    # 价格低于买入价5%
    df.loc[(df['position'] == 1) & (df['position_change_pct'] < stop_price_pct), 'position'] = 0
    src_df['position'] = df['position']
    return src_df


def position_stop_buy_price(src_df: pd.DataFrame, stop_price_pct: float = -0.05):
    """
    基于持仓买入价止损：
    1.当价格低于5%卖出
    params:
    src_df: pd.DataFrame
    stop_price_pct: 止损价跌幅
    """
    df = src_df.copy()
    # 仓位买入时，设置买入价
    df.loc[(df['position'] > df['position'].shift(1)) & (df['position'].shift(1) == 0), 'position_buy_price'] = df.close
    df['position_buy_price'].fillna(method='ffill', inplace=True)
    df.loc[df['position'] == 0, 'position_buy_price'] = np.NaN
    df['position_buy_pct'] = (df.close.values - df.position_buy_price.values) / df['position_buy_price'].values
    # 价格低于买入价5%
    df.loc[(df['position'] == 1) & (df['position_buy_pct'] <= stop_price_pct) & (
            df['position_buy_pct'].shift(1) > stop_price_pct), 'stop_price_position'] = True
    df.loc[df['position'] == 0, 'stop_price_position'] = 0
    df['stop_price_position'].fillna(method='ffill', inplace=True)

    df.loc[(df['stop_price_position'] == True), 'position'] = 0
    src_df['position'] = df['position']
    return src_df


def calcTR(high, low, close):
    '''Calculate True Range'''
    return np.max(np.abs([high - low, close - low, low - close]))


def ATR(df: pd.DataFrame = None, period: int = 21):
    """
    海龟交易法平均波幅
    function to calculate True Range and Average True Range
    """
    df['H-L'] = abs(df['high'] - df['low'])
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))  # df['Close'].shift(1) 前一天的开盘价
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].rolling(period).mean()
    # 无数据的先删掉
    df.drop(['H-L', 'H-PC', 'L-PC', 'TR'], axis=1, inplace=True)
