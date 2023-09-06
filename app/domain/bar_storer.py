import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import parse
from tqdm import tqdm
import multitasking
import signal

import app.constants as constants
import app.facade as facade
import app.utils as utils

# import warnings
#
# warnings.filterwarnings('ignore')

# kill all tasks on ctrl-c
#signal.signal(signal.SIGINT, multitasking.killall)


class BarStorer:
    def __init__(self,tudata: facade.TushareData, data_path='../../data', file_name=''):
        self._cols = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'adj_factor', 'vol', 'main_net_inflow','turnover_rate_f', 'volume_ratio', 'pe_ttm', 'pb', 'ps_ttm', 'dv_ttm',
                      'free_share', 'total_mv', 'circ_mv']
        self._data_path = data_path
        self._file_name = file_name
        self.hdfStore = pd.HDFStore(self._data_path + self._file_name, 'a')
        self.tudata = tudata
        self._code_list = []
        self._cals = self.tudata.get_cals()
        self._store_daily_key = "daily"

    def get_code_list(self):
        data = self.tudata.get_stock_basic()
        return data['ts_code']

    # 获取数据库最新日期
    def get_store_latest_date(self):
        try:
            data = self.hdfStore.select_column(key="000001.SZ", column="trade_date", start=-1)
            date = data.iloc[0]
        except:
            date = '20040101'
        return date

    # 下载某日期期间所有个股行情数据+指标+基础信息，保存到sql数据库
    def store_daily_data(self, dates):
        tu_pbar = tqdm(total=len(dates), desc='tushare Processing')
        df = pd.DataFrame()
        for d in dates:
            data = self.trade_daily_store_data(d)
            df = df.append(data)
            tu_pbar.update()
        tu_pbar.close()
        if df.empty is True:
            return
        df.sort_values(by=['ts_code', 'trade_date'], ascending=[True, False], inplace=True)

        # 存储
        self.hdfStore.append(key=self._store_daily_key, value=df, format='table', data_columns=True)
        return

        # code_list = self.get_code_list()
        #
        # store_pbar = tqdm(total=len(code_list), desc='store Processing')
        # for code in code_list:
        #     ts_code = code
        #     data = df[df.ts_code == ts_code]
        #     self.do_store(ts_code, data, store_pbar)
        #
        # multitasking.wait_for_tasks()
        # store_pbar.close()

    # @multitasking.task
    def do_store(self, ts_code, data: pd.DataFrame, pbar):
        if data.empty is True:
            pbar.update()
            return
        try:
            hdf = self.hdfStore
            if hdf.get_node(ts_code) is None:
                hdf.put(key=ts_code, value=data, format='table', data_columns=self._cols)

                stock_basic = pd.Series(
                    data[['symbol', 'ts_code', 'name', 'area', 'industry', 'stores', 'list_date']].iloc[0])
                # 存储属性
                code_storer = hdf.get_storer(ts_code)
                code_storer.attrs['attr_code'] = ts_code
                code_storer.attrs['attr_symbol'] = stock_basic['symbol']
                code_storer.attrs['attr_name'] = stock_basic['name']
                code_storer.attrs['attr_area'] = stock_basic['area']
                code_storer.attrs['attr_code'] = stock_basic['industry']
                code_storer.attrs['attr_market'] = stock_basic['stores']
                code_storer.attrs['attr_listed_date'] = stock_basic['list_date']
            else:
                hdf.append(key=ts_code, value=data, format='table', data_columns=True)
            pbar.update()
        except Exception as e:
            print("ts_code=", ts_code)
            print(e)

    # @multitasking.task
    def trade_daily_store_data(self, date) -> pd.DataFrame:
        try:
            df = self.tudata.trade_daily_store_data(date)
            cols = ['主力净流入']
            new_cols = ['main_net_inflow']
            df = df.rename(columns=dict(zip(cols, new_cols)))
            return df
        except Exception as e:
            print(date)
            print(e)

    def get_trade_daily_data(self, date) -> pd.DataFrame:
        data = self.hdfStore.select(key=self._store_daily_key, where=[f"trade_date=='{date}'"])
        return data

    # 从存储中获取近期（如600日，至少保证交易日不少于250日）所有个股复权价格和成交量等数据
    def get_adj_data(self, code_list: list = None, deadline_date=None, n=600, adj='hfq') -> pd.DataFrame:
        # 获取距离当前n日数据
        end_time = datetime.now()
        if deadline_date is not None:
            end_time = datetime.strptime(deadline_date, "%Y%m%d")

        cals = self._cals
        n2 = np.where(cals <= deadline_date)[0][-1] + 1
        dates = cals[-n:n2]
        if len(dates) == 0:
            return
        start_date = dates[0]
        end_date = dates[-1]
        where = f"trade_date > '{start_date}' & trade_date < '{end_date}'"
        if code_list is not None:
            codes = tuple(code_list)
            where = where + f' & ts_code in {codes}'
        data = self.hdfStore.select(key=self._store_daily_key, where=[where])
        if isinstance(data, pd.DataFrame) is False:
            return

        data = data.sort_values(['ts_code', 'trade_date'])
        data = data.drop_duplicates()
        # 前复权
        cols = ['close', 'open', 'high', 'low']
        if adj == 'qfq':
            for c in cols:
                data['adj' + c] = data.groupby('ts_code').apply(
                    lambda x: x[c] * x.adj_factor / x.adj_factor.iloc[-1]).values
        if adj == 'hfq':
            for c in cols:
                data['adj' + c] = data.groupby('ts_code').apply(
                    lambda x: x[c] * x.adj_factor / x.adj_factor.iloc[0]).values
        # 设置索引
        adj_cols = ['adj' + c for c in cols]
        old_cols = adj_cols + ['vol']
        # 将复权名称转为一般名称['close','open','high','low']
        new_cols = cols + ['volume']
        data.drop(labels=new_cols, axis=1, inplace=True, errors='ignore')  # 先删除同名列
        data = data.rename(columns=dict(zip(old_cols, new_cols)))

        data = data.drop_duplicates()
        return data

    def get_trade_dates(self, start, end):
        if start is None:
            start = self.get_store_latest_date()
        if end is None:
            end = utils.get_today_date()

        dates = utils.get_trade_date(self._cals, start, end)
        return dates

    # 更新数据库数据
    def update_daily_data(self, start=None, end=None):
        dates = self.get_trade_dates(start, end)
        self.store_daily_data(dates)
        sql_date = self.get_store_latest_date()
        print(f"hdf5数据库已更新至{sql_date}日数据")

    def start(self, start='20100101', end='20230101'):
        code_groups = utils.arr_chunk_groups(self._code_list, 100)
        for codes in code_groups:
            data = facade.get_data(code_list=codes, start=start, end=end, fqt=2)

            stock_realtime_df = self.stock_s.get_stock_realtime(codes)
            codes_dict = stock_realtime_df.set_index(['code']).to_dict('index')

            for code in codes:
                symbol = code
                code_data = data[data.code == code][self._cols]
                self.hdfStore.put(key=symbol, value=code_data, format='table', data_columns=True)
                if self.hdfStore.get_node(symbol) is None:
                    continue

                self.hdfStore.get_storer(symbol).attrs['attr_code'] = code
                self.hdfStore.get_storer(symbol).attrs['attr_name'] = codes_dict[code]['name']
                self.hdfStore.get_storer(symbol).attrs['attr_listed_date'] = codes_dict[code]['listed_date']

        self.hdfStore.close()

    def stop(self):
        self.hdfStore.close()
