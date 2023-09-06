import numpy as np
import pandas as pd

import app.constant as constant
import app.facade as facade
import app.domain as domain
import app.strategies as strategies
from app.domain.stores import StockMarket

stock_service = StockMarket()

tudata = facade.TushareData(token=constant.TUSHARE_TOKEN,
                            my_path='sql_data/',
                            db_name='stock_data.db')


def main():
    """
    策略思想：
    1.最多持仓5只股票（可配置），价格在50元以下，小市值。
    2.选股策略：rps+资金流向+每日指标（符合）（每日选股检测）
    3.选股基础上，结合技术指标，均线、macd、kdj
    4.当账户剩余资金足够买入选股权重靠前的标的，买入持有。
    5.等待持仓符合卖出时，卖出
    6.卖出后剩余资金重复步骤3.
    7.买入和卖出，加入参数：手续费、滑点等。
    8.打分机制：得分越高的，资金越倾向
    """
    # 获取沪深全市场A股代码
    codes = stock_service.get_codelist()

    start_date = 20200101
    end_date = 20220801

    # 股票交易日历
    trade_cals_arr = tudata.get_cals().astype(np.int32)
    trade_cals = trade_cals_arr[np.where((trade_cals_arr >= start_date) & (trade_cals_arr <= end_date))].astype(
        np.str).tolist()

    for trade_date in trade_cals:
        data = filter_stock_pool(do_date=trade_date)
        # todo:资金流打分
        stock_score_grade(data)
        mk_strategy(data)
        print("策略：MM趋势+RPS+资金流选股池+每日指标。日期：", trade_date, " 选股结果：\n", data)


def mk_strategy(df, lookback=20, buy_threshold=-1.5, sell_threshold=1.5, cost=0.0):
    '''输入参数：
    df为数据表: 包含open,close,low,high,vol，标的收益率rets，指数收益率数据hs300
    lookback为均值回归策略参数，设置统计区间长度，默认20天
    '''

    # 计算均值回归策略的score值
    ret_lb = df.rets.rolling(lookback).mean()
    std_lb = df.rets.rolling(lookback).std()
    df['score'] = (df.rets - ret_lb) / std_lb
    df.fillna(0, inplace=True)
    # 设计买卖信号，为尽量贴近实际，加入涨跌停不能买卖的限制
    # 当score值小于-1.5且第二天开盘没有涨停发出买入信号设置为1
    df.loc[(df.score < buy_threshold) & (df['open'] < df['close'].shift(1) * 1.097), 'signal'] = 1
    # 当score值大于1.5且第二天开盘没有跌停发出卖入信号设置为0
    df.loc[(df.score > sell_threshold) & (df['open'] > df['close'].shift(1) * 0.903), 'signal'] = 0
    df['position'] = df['signal'].shift(1)
    df['position'].fillna(method='ffill', inplace=True)  # 用前面的值来填充
    df['position'].fillna(0, inplace=True)
    # 根据交易信号和仓位计算策略的每日收益率
    df.loc[df.index[0], 'capital_ret'] = 0
    # 今天开盘新买入的position在今天的涨幅(扣除手续费)
    df.loc[df['position'] > df['position'].shift(1), 'capital_ret'] = \
        (df['close'] / df['open'] - 1) * (1 - cost)
    # 卖出同理
    df.loc[df['position'] < df['position'].shift(1), 'capital_ret'] = \
        (df['open'] / df['close'].shift(1) - 1) * (1 - cost)
    # 当仓位不变时,当天的capital是当天的change * position
    df.loc[df['position'] == df['position'].shift(1), 'capital_ret'] = \
        df['rets'] * df['position']
    # 计算策略累计收益率
    df['capital_line'] = (df.capital_ret + 1.0).cumprod()
    return df


def stock_score_grade(df: pd.DataFrame):
    '''
    股票打分：
    选股之后给股票打分
    '''
    df['score'] = 0.0
    # 价格低的权重
    df.loc[df['close'] < 50, 'score'] = df['score'] + 0.5

    return df


def filter_stock_pool(do_date=None):
    if do_date is None:
        return

    # 每日指标数据
    trade_daily = tudata.sql_date_data(date=do_date)
    if trade_daily.empty is True:
        return
    daily_result = strategy.filter_daily_trade(trade_daily)
    if daily_result.empty is True:
        return

    # rps
    code_list = list(daily_result['symbol'])
    dl = tudata.sql_adj_data_v2(code_list=code_list, date=do_date, n=600)

    cols = ['close', 'open', 'high', 'low', 'volume']
    data_rps = dl.set_index(['trade_date', 'ts_code'])[cols]
    data_rps = data_rps.unstack()
    prices = data_rps['close'].dropna(axis=1)
    rps = strategy.RPS(prices)
    df_rps = rps.date_rps()

    # MM趋势
    mm_trend = prices.apply(strategy.MM_trend).T
    mm_result = mm_trend.query('meet_criterion==1')
    # mm趋势+120日rps>90
    mm_rps_result = pd.concat([mm_result, df_rps.query('rps_120>90')], join='inner', axis=1)

    code_list = mm_rps_result.index
    df = dl[dl['ts_code'].isin(code_list)]
    return df


if __name__ == '__main__':
    # main()

    cals = tudata.get_cals()
    bar_storer = domain.BarStorer(tudata, data_path="../data/", file_name="cn_stock.hdf5")
    strategy = strategies.CustomStrategy(cals, bar_storer)
    strategy.filter_stock(do_date='20230215')
