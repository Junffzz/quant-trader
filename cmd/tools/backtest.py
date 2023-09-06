import quantstats as qst
import numpy as np
import pandas as pd
import scipy.stats as stats
from datetime import timedelta
import scipy.spatial.distance as distance
import matplotlib.pyplot as plt
import app.strategies.backtest as backtest
import app.strategies.helpers as helpers
import app.plot as pt
import app.utils as utils

import pandas_ta as ta
from multiprocessing import Process, freeze_support

plt.set_loglevel("info")


# 封装成函数方便后面进行回测分析
def ma_momentum(code, benchmark='hs300', start='20100101', end='202303219', ma_list=None, threshold=0.8):
    df = backtest.data_feed(code, index=benchmark, start=start, end=end, fqt=2)
    ss = np.linspace(10, 100, 10) if ma_list is None else ma_list
    for i in ss:
        df[str(i) + '日均线'] = df['close'].rolling(window=int(i), center=False).mean()
    df.dropna(inplace=True)
    cols = [str(i) + '日均线' for i in ss]
    for date in df.index:
        ranking = stats.rankdata(df.loc[date, cols].values)
        df.loc[date, 'scores'] = distance.hamming(ranking, range(1, len(ss) + 1))
    # 当日均线多头排列scores=1发出买入信号设置为1
    df.loc[df['scores'] > threshold, 'signal'] = 1
    # 当日均线空头排列scores=0发出买入信号设置为0
    df.loc[df['scores'] <= threshold, 'signal'] = 0
    df['position'] = df['signal'].shift(1)
    df['position'].fillna(method='ffill', inplace=True)
    d = df[df['position'] == 1].index[0] - timedelta(days=1)
    df1 = df.loc[d:].copy()
    df1['position'][0] = 0
    # 当仓位为1时，买入持仓，当仓位为0时，空仓，计算资金净值
    df1['capital_ret'] = df1.rets.values * df1['position'].values
    # 计算策略累计收益率
    df1['capital_line'] = (df1.capital_ret + 1.0).cumprod()
    return df1


def momentum_backtest():
    # 可以通过ma_list自定义设置ma均线计算周期
    # 如ma_list=[3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
    # ma_list=None表示默认使用10-100日均线
    data = ma_momentum('中国平安', ma_list=None, threshold=0.8)
    backtest.start_backtest(data)

    qst.reports.full(data.capital_ret)


def main():
    # 获取数据
    # data_feed是qstock回测模块获取数据函数，默认基准指数为沪深300
    # fqt=2表示后复权数据，等于1表示前复权
    df = backtest.data_feed('中国平安', index='hs300', start='20200101', end='202201216', fqt=2)
    # 计算10个均线序列
    for i in np.linspace(10, 100, 10):
        df[str(i) + '日均线'] = df['close'].rolling(window=int(i), center=False).mean()
    df.dropna(inplace=True)
    # 均线可视化
    cols = ['close'] + [str(i) + '日均线' for i in np.linspace(10, 100, 10)]
    pt.line(df['2020':][cols])

    cols = [str(i) + '日均线' for i in np.linspace(10, 100, 10)]

    for date in df.index:
        # 围绕每一日的均线大小进行排序
        ranking = stats.rankdata(df.loc[date, cols].values)
        # 计算每一日均线之间的汉明距离（scipy.spatial.distance）
        df.loc[date, 'scores'] = distance.hamming(ranking, range(1, 11))

    # 价格走势与均线排列的汉明距离得分可视化
    df[['close', 'scores']].plot(figsize=(15, 7), secondary_y='scores', alpha=0.6)
    plt.show()

    # 描述性统计
    df[['close', 'scores']].describe()


# 封装成函数方便后面进行回测分析
def tech_strategy(code, benchmark='标普500', start='20100101', end='20230402'):
    df = backtest.data_feed(code, index=benchmark, start=start, end=end, fqt=1)
    macd_strategy = ta.Strategy(
        name="Momo and Volatility",
        description="SMA 50,200, BBANDS, RSI, MACD and Volume SMA 20",
        ta=[
            # {"kind": "sma", "length": 50},
            # {"kind": "sma", "length": 200},
            {"kind": "ema", "length": 10},
            {"kind": "ema", "length": 20},
            # {"kind": "kdj", "prefix": "kdj"},
            {"kind": "macd", "asmode": False, "col_names": ("MACD_DIF", "MACD", "MACD_DEA")},
            {"kind": "sma", "close": "volume", "length": 20, "prefix": "VOLUME"},
        ]
    )
    freeze_support()
    df.ta.strategy(macd_strategy)
    df['MACD'] *= 2  # MACD需要乘以2
    # 当macd DIF>DEA发出买入信号设置为1
    df.loc[(df['MACD'] > 0) & (df['MACD_DIF'] > 0.5), 'signal'] = 1
    # 当macd DIF<-0.5发出卖出信号设置为0
    df.loc[(df['MACD_DIF'] < -0.5) | (df['EMA_10']<df['EMA_20']), 'signal'] = 0

    df['position'] = df['signal'].shift(1) # 持仓位置
    df['position'].fillna(method='ffill', inplace=True)
    d = df[df['position'] == 1].index[0] - timedelta(days=1)
    df1 = df.loc[d:].copy()
    # 价格止损
    df1 = helpers.position_stop_buy_price(df1)
    df1['position'][0] = 0
    # 当仓位为1时，买入持仓，当仓位为0时，空仓，计算资金净值
    df1['capital_ret'] = df1.rets.values * df1['position'].values
    # 计算策略累计收益率
    df1['capital_line'] = (df1.capital_ret + 1.0).cumprod()
    return df1


def us_backtest():
    # 可以通过ma_list自定义设置ma均线计算周期
    # 如ma_list=[3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
    # ma_list=None表示默认使用10-100日均线
    data = tech_strategy('XPEV', start='20200101')
    result = backtest.start_backtest(data)
    print("result = \n", result)
    # qst.reports.full(data.capital_ret)


if __name__ == '__main__':
    # main()
    # momentum_backtest()

    us_backtest()
    # us_ta_strategy('PDD', start='20211207')
