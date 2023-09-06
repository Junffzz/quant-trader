import numpy as np
import pandas as pd

import app.facade as facade
from app.domain.stores import StockMarket
import app.strategies as strategies
import app.utils as utils

stock_service = StockMarket()

tudata = facade.TushareData(token='7ba597f7da0b37aa7303298c65dcb17d72ee50ccdd345563b9ded06e',
                            my_path='sql_data/',
                            db_name='stock_data.db')


def main():
    cols = ['close', 'open', 'high', 'low']
    # 获取沪深全市场A股代码
    codes = stock_service.get_codelist()
    codes = codes[:1000]

    start_date = 20200101
    end_date = 20220801

    # 股票交易日历
    trade_cals_arr = tudata.get_cals().astype(np.int32)
    trade_cals = trade_cals_arr[np.where((trade_cals_arr >= start_date) & (trade_cals_arr <= end_date))].astype(
        np.str).tolist()

    # 临时定义
    trade_cals = ['20200106', '20200122', '20200220', '20200304', '20200409', '20200423', '20200507']
    for trade_date in trade_cals:
        data = strategy_rps_mm_moneyflow_daily(do_date=trade_date)
        if data is None:
            continue
        print("策略：MM趋势+RPS+资金流选股池+每日指标。日期：", trade_date, " 选股结果：", data)



def strategy_rps_mm_moneyflow_daily(do_date=None):
    '''
    策略：MM趋势+RPS+资金流选股池+每日指标
    卖出：双均线死叉
    '''
    if do_date is None:
        return

    # 每日指标数据
    trade_daily = tudata.sql_date_data(date=do_date)
    if trade_daily.empty is True:
        return
    daily_result = strategies.filter_daily_trade(trade_daily)
    if daily_result.empty is True:
        return
    # daily_result.sort_values('主力净流入',ascending=False)[:10]

    code_list = list(daily_result['symbol'])
    prices = tudata.sql_adj_data(code_list=code_list, date=do_date, n=600)['close'].dropna(axis=1)
    rps = strategies.RPS(prices)
    df_rps = rps.date_rps()

    # MM趋势
    mm_trend = prices.apply(strategies.MM_trend).T
    mm_result = mm_trend.query('meet_criterion==1')

    # mm趋势+120日rps>90
    mm_rps_result = pd.concat([mm_result, df_rps.query('rps_120>90')], join='inner', axis=1)
    # mm_rps_result.sort_values('rps_250',ascending=False)[:10]

    # 资金流(指定日期)
    code_list = tudata.moneyflow_stock(mm_rps_result.index, date=do_date)
    if len(code_list) == 0:
        return
    code_list = [utils.convert_tscode(c) for c in code_list]
    # print(f'最近1、3、5、10、20、60日主力资金累计净流入均大于0个股数量：{len(code_list)}')

    # mm趋势+RPS+资金流选股
    # mm_rps_result.loc[(set(mm_rps_result.index)&set(code_list))]

    # mm趋势+RPS+资金流选股+每日指标
    df1 = mm_rps_result.loc[code_list][['收盘价', 'rps_120']]
    df2 = daily_result.copy()
    data = pd.concat([df1, df2], join='inner', axis=1)
    return data


if __name__ == '__main__':
    # code_list = ['000021.SZ', '002273.SZ', '002600.SZ', '601689.SH']
    # #code_list = ['601689.SH']
    # code_result1 = strategies.moneyflow_stock(code_list)
    # print("code_result1:", code_result1)
    # code_result2 = tudata.moneyflow_stock(code_list,'20200106')
    # print("code_result2:", code_result2)

    main()
