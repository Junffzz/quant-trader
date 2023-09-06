import pandas as pd

import talib


def macd_indicator(df: pd.DataFrame):
    # macd
    df['DIFF'], df['DEA'], df['MACD'] = talib.MACD(df['close'].values)
    df['MACD'] *= 2  # 国内MACD需要乘以2
    df.fillna(0, inplace=True)


def kdj_indicator(df: pd.DataFrame):
    # kdj
    df['slowk'], df['slowd'] = talib.STOCH(df['high'].values,
                                           df['low'].values,
                                           df['close'].values,
                                           fastk_period=9,
                                           slowk_period=3,
                                           slowk_matype=0,
                                           slowd_period=3,
                                           slowd_matype=0)
    # 求出J值，J = (3*K)-(2*D)
    df['slowj'] = list(map(lambda x, y: 3 * x - 2 * y, df['slowk'], df['slowd']))
    df.index = range(len(df))
