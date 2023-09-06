# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dateutil.parser import parse
from tqdm import tqdm
import multitasking
import signal

import tushare as ts

from app.facade.base import sql_engine
import app.utils as utils

signal.signal(signal.SIGINT, multitasking.killall)

# 常见的全球指数代码和名称
china_indexs = {'上证综指': '000001.SH', '深证成指': '399001.SZ', '沪深300': '000300.SH',
                '创业板指': '399006.SZ', '上证50': '000016.SH', '中证500': '000905.SH',
                '中小板指': '399005.SZ', '上证180': '000010.SH',
                '上证指数': '000001.SH', 'sh': '000001.SH', 'sz': '399001.SZ', 'hs300': '000300.SH',
                'cyb': '399006.SZ', 'sz50': '000016.SH', 'sz500': '000905.SH',
                'zxb': '399005.SZ', 'sz180': '000010.SH'}

global_indexs = {'恒生': 'HSI', '道琼斯': 'DJI', '标普500': 'SPX', '纳斯达克': 'IXIC',
                 '法国CAC40': 'FCHI', '德国DAX': 'GDAXI', '日经225': 'N225', '韩国综合': 'KS11',
                 '澳大利亚标普': 'AS51', '印度孟买': 'SENSEX', '台湾加权': 'TWII',
                 '恒生指数': 'HSI', '道琼斯指数': 'DJI', '标普500指数': 'SPX', '纳斯达克指数': 'IXIC',
                 '法国CAC40指数': 'FCHI', '德国DAX指数': 'GDAXI', '日经225指数': 'N225',
                 }

index_dict = dict(**china_indexs, **global_indexs)

token = 'fd2f94e6dbb36f8b0fd4651eaf89cbc90224b4344421c17c46544e82'


def ts_pro(token):
    ts.set_token(token)
    pro = ts.pro_api(token)
    return pro


class TushareData(object):
    def __init__(self, token=token,
                 my_path='D:\\zjy\\sql_data',
                 db_name='stock_data.db',
                 table_name='daily_data'):
        '''参数token：tushare的token
        my_paaath:数据库存放目录文件夹
        db_name:数据库名称
        table_name:数据表名称
        '''
        if not os.path.exists(my_path):
            os.mkdir(my_path)
        self.pro = ts_pro(token)
        self.engine = sql_engine(my_path, db_name)
        self.pbar = None
        self.cals = self.get_cals()
        self.table_name = table_name

    # 获取股票地域行业信息
    def get_stock_basic(self) -> pd.DataFrame:
        df = self.pro.stock_basic(list_status='', fields=[
            "ts_code",
            "symbol",
            "name",
            "area",
            "industry",
            "stores",
            "list_date",
            "fullname",
            "enname",
            "cnspell",
            "exchange",
            "curr_type",
            "list_status",
            "delist_date",
            "is_hs"
        ])
        # 将上市地深圳改为广东
        df['area'] = df['area'].replace('深圳', '广东')
        return df

    # 获取股票名称代码字典
    def get_name_code_dict(self, st=False, bank=False, new=False):
        # 三年前日期
        date = str(datetime.now().year - 3) + '0101'
        df = self.get_stock_basic()
        # 是否剔除st股
        if st:
            # 排除st和*ST股
            df = df[-df.name.str.startswith(('ST'))]
            df = df[-df.name.str.startswith(('*'))]
        # 是否剔除'银行','保险','多元金融'等股票
        if bank:
            df = df[-df.industry.isin(['银行', '保险', '多元金融'])]
        # 是否剔除新股次新股
        if new:
            df = df[df.list_date < date]
        code = df.ts_code.values
        name = df.name
        return dict(zip(name, code))

    # 获取股票交易日历
    def get_cals(self):
        # 获取交易日历
        cals = self.pro.trade_cal(exchange='')
        cals = cals[cals.is_open == 1].cal_date.values
        cals = np.sort(cals)
        return cals

    # 简称或数字转为带‘SZ'或'SH’的代码
    def trans_code(self, stock):
        if len(stock) == 9:
            return stock
        # 输入的是简称或数字代码
        dd = self.get_stock_basic()
        if stock in list(dd.symbol):
            return dd[dd.symbol == stock].iloc[0, 0]
        if stock in list(dd.name):
            return dd[dd.name == stock].iloc[0, 0]

    # 根据代码获取股票名称
    def trans_name(self, stock):
        if '\u4e00' <= stock[0] <= '\u9fa5':
            return stock
        # 输入的是简称或数字代码
        dd = self.get_stock_basic()
        if stock in list(dd.symbol):
            return dd[dd.symbol == stock].iloc[0, 2]
        if stock in list(dd.ts_code):
            return dd[dd.ts_code == stock].iloc[0, 2]

    # 在线获取某个股OHLCV数据
    # 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债
    # 默认前复权，adj='None'不复权，adj='hfq'后复权
    def get_ohlc_data(self, stock, start='', end='', adj='qfq', freq='D', asset='E'):
        code = self.trans_code(stock)
        # name=self.trans_name(stock)
        df = ts.pro_bar(ts_code=code, start_date=start, end_date=end, adj=adj, freq=freq, asset=asset)
        df.index = pd.to_datetime(df.trade_date)
        df = df.sort_index()[['open', 'high', 'low', 'close', 'vol']]
        return df

    # 在线获取某个股所有日期行情数据+指标+基础信息
    def stock_daily_data(self, stock):
        code = self.trans_code(stock)

        try:
            # 每日行情数据（无复权）
            df0 = self.pro.daily(ts_code=code)[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']]
            df1 = self.pro.adj_factor(ts_code=code, trade_date='')  # 复权因子
            # 每日主力资金净流入（大单+超大单主动买入-主动卖出）
            # 定义20万以上为大单,超大单是100万
            df2 = self.pro.moneyflow(ts_code=code)
            df2['主力净流入'] = df2['buy_lg_amount'] + df2['buy_elg_amount'] - (
                    df2['sell_lg_amount'] + df2['sell_elg_amount'])
            df2 = df2[['ts_code', 'trade_date', '主力净流入']]
            # 每日涨跌停价格
            df3 = self.pro.stk_limit(ts_code=code)
            # 每日指标(其中市盈率、市销率和股息率均为动态的，即滚动季度计算)
            cols = ['ts_code', 'trade_date', 'turnover_rate_f', 'volume_ratio', 'pe_ttm', 'pb', 'ps_ttm', 'dv_ttm',
                    'free_share', 'circ_mv']
            new_cols = ['ts_code', 'trade_date', '换手率', '量比', '市盈率', '市净率', '市销率', '股息率', '自由流通股',
                        '流通市值']
            df4 = self.pro.daily_basic(ts_code=code, fields=','.join(cols))
            df4 = df4.rename(columns=dict(zip(cols, new_cols)))
            # 公司基础信息
            df5 = self.pro.stock_basic(ts_code=code)
            # 合并数据
            df = df0.merge(df1).merge(df2).merge(df3).merge(df4).merge(df5)
            return df

        except Exception as e:
            print(code)
            print(e)

    # 在线获取某交易日所有个股资金流入与每日指标
    def trade_daily_data(self, date=None):
        if date is None:
            date = self.latest_trade_date()
        df0 = self.pro.moneyflow(trade_date=date)
        df0['主力净流入'] = df0['buy_lg_amount'] + df0['buy_elg_amount'] - (
                df0['sell_lg_amount'] + df0['sell_elg_amount'])
        df0 = df0[['ts_code', 'trade_date', '主力净流入']]
        df1 = self.pro.stk_limit(trade_date=date)
        cols = ['ts_code', 'trade_date', 'turnover_rate_f', 'volume_ratio', 'pe_ttm', 'pb', 'ps_ttm', 'dv_ttm',
                'free_share', 'circ_mv']
        new_cols = ['ts_code', 'trade_date', '换手率', '量比', '市盈率', '市净率', '市销率', '股息率', '自由流通股',
                    '流通市值']
        df2 = self.pro.daily_basic(trade_date=date, fields=','.join(cols))
        df2 = df2.rename(columns=dict(zip(cols, new_cols)))
        df = df0.merge(df1).merge(df2)
        return df

    # 在线获取某交易日所有个股资金流入与每日指标
    def trade_daily_store_data(self, date=None):
        if date is None:
            date = self.latest_trade_date()
        df0 = self.pro.daily(trade_date=date)[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']]
        df1 = self.pro.adj_factor(trade_date=date)
        df2 = self.pro.moneyflow(trade_date=date)
        df2['主力净流入'] = df2['buy_lg_amount'] + df2['buy_elg_amount'] - (
                df2['sell_lg_amount'] + df2['sell_elg_amount'])
        df2 = df2[['ts_code', 'trade_date', '主力净流入']]
        df3 = self.pro.stk_limit(trade_date=date)
        cols = ['ts_code', 'trade_date', 'turnover_rate_f', 'volume_ratio', 'pe_ttm', 'pb', 'ps_ttm', 'dv_ttm',
                'free_share', 'total_mv', 'circ_mv']
        df4 = self.pro.daily_basic(trade_date=date, fields=','.join(cols))
        df = df0.merge(df1).merge(df2).merge(df3).merge(df4)
        return df

    @multitasking.task
    def run(self, date):
        try:
            df0 = self.pro.daily(trade_date=date)[['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']]
            df1 = self.pro.adj_factor(trade_date=date)
            df2 = self.pro.moneyflow(trade_date=date)
            df2['主力净流入'] = df2['buy_lg_amount'] + df2['buy_elg_amount'] - (
                    df2['sell_lg_amount'] + df2['sell_elg_amount'])
            df2 = df2[['ts_code', 'trade_date', '主力净流入']]
            df3 = self.pro.stk_limit(trade_date=date)
            cols = ['ts_code', 'trade_date', 'turnover_rate_f', 'volume_ratio', 'pe_ttm', 'pb', 'ps_ttm', 'dv_ttm',
                    'free_share', 'circ_mv']
            new_cols = ['ts_code', 'trade_date', '换手率', '量比', '市盈率', '市净率', '市销率', '股息率', '自由流通股',
                        '流通市值']
            df4 = self.pro.daily_basic(trade_date=date, fields=','.join(cols))
            df4 = df4.rename(columns=dict(zip(cols, new_cols)))
            df5 = self.pro.stock_basic(trade_date=date)
            df = df0.merge(df1).merge(df2).merge(df3).merge(df4).merge(df5)
            df.to_sql(self.table_name, self.engine, index=False, if_exists='append')
            self.pbar.update()
        except:
            pass

    # 下载某日期期间所有个股行情数据+指标+基础信息，保存到sql数据库
    def sql_daily_data(self, dates):
        self.pbar = tqdm(total=len(dates))
        for d in dates:
            self.run(d)

    # 从数据库中获取个股数据默认计算后复权
    def get_sql_stock(self, stock, adj='hfq'):
        code = self.trans_code(stock)
        sql = f"select * from {self.table_name} where ts_code='{code}'"
        df = pd.read_sql(sql, self.engine)
        df.index = pd.to_datetime(df.trade_date)
        df = (df.sort_index()).drop('trade_date', axis=1)
        df = df.rename(columns={'vol': 'volume'})

        prices = ['close', 'open', 'high', 'low']

        if adj == 'qfq':
            for p in prices:
                df['adj' + p] = df[p] * df.adj_factor / df.adj_factor.iloc[-1]

        if adj == 'hfq':
            for p in prices:
                df['adj' + p] = df[p] * df.adj_factor / df.adj_factor.iloc[0]

        cols1 = ['adj' + p for p in prices] + ['volume']
        cols2 = prices + ['volume']
        df1 = df.drop(columns=prices).rename(columns=dict(zip(cols1, cols2)))
        return df1

    def sql_all_data(self, date=None):
        if date is None:
            d = self.latest_trade_date()
            date = self.cals[np.where(self.cals < d)[0]][-300:][0]
        sql = f'select * from {self.table_name} where trade_date>{date}'
        data = pd.read_sql(sql, self.engine)
        return data

    # 数据库读取指定日期数据
    def sql_date_data(self, date=None):
        if date is None:
            d = self.latest_trade_date()
            date = self.cals[np.where(self.cals < d)[0]][-300:][0]
        sql = f'select * from {self.table_name} where trade_date={date}'
        data = pd.read_sql(sql, self.engine)
        return data

    # 从数据库中获取近期（如600日，至少保证交易日不少于250日）所有个股复权价格和成交量等数据
    def sql_adj_data(self, code_list: list = None, date=None, n=600, adj='hfq') -> pd.DataFrame:
        # 获取距离当前n日数据
        end_time = datetime.now()
        if date is not None:
            end_time = datetime.strptime(date, "%Y%m%d")

        start_date = (end_time - timedelta(n)).strftime('%Y%m%d')
        end_date = end_time.strftime('%Y%m%d')

        sql = f'select * from {self.table_name} where trade_date>{start_date} and trade_date<={end_date}'
        if code_list is not None:
            codes = tuple(code_list)
            sql = f'select * from {self.table_name} where symbol in {codes} and trade_date>{start_date} and trade_date<={end_date}'

        data = pd.read_sql(sql, self.engine)
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
        data = data.set_index(['trade_date', 'ts_code'])[old_cols]
        # 将复权名称转为一般名称['close','open','high','low']
        new_cols = cols + ['volume']
        data = data.rename(columns=dict(zip(old_cols, new_cols)))
        # 转成面板数据
        data = data.drop_duplicates()
        data = data.unstack()
        return data

    # 从数据库中获取近期（如600日，至少保证交易日不少于250日）所有个股复权价格和成交量等数据
    def sql_adj_data_v2(self, code_list: list = None, date=None, n=600, adj='hfq') -> pd.DataFrame:
        # 获取距离当前n日数据
        end_time = datetime.now()
        if date is not None:
            end_time = datetime.strptime(date, "%Y%m%d")

        start_date = (end_time - timedelta(n)).strftime('%Y%m%d')
        end_date = end_time.strftime('%Y%m%d')

        sql = f'select * from {self.table_name} where trade_date>{start_date} and trade_date<={end_date}'
        if code_list is not None:
            codes = tuple(code_list)
            sql = f'select * from {self.table_name} where symbol in {codes} and trade_date>{start_date} and trade_date<={end_date}'

        data = pd.read_sql(sql, self.engine)
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
        # 转成面板数据
        data = data.drop_duplicates()
        return data

    # 资金流
    def moneyflow_stock(self, codes, date, w_list=[3, 5, 10, 20, 60]):
        code_list = []
        for s in codes:
            s = s[:6]
            try:
                if all(self.stock_money(s, date, w_list).iloc[-1] > 0):
                    code_list.append(s)
            except:
                continue

        return code_list

    # 个股n日资金流
    def stock_money(self, code, date, ndays=[3, 5, 10, 20]):
        '''stock可以为股票简称或代码，如晓程科技或300139
           ndays为时间周期，如3日、5日、10日等
        '''
        # 获取个股资金流向数据

        maxn = max(ndays) + 100  # +100为了保证数据全
        end_time = datetime.now()
        if date is not None:
            end_time = datetime.strptime(date, "%Y%m%d")

        start_date = (end_time - timedelta(maxn)).strftime('%Y%m%d')
        end_date = end_time.strftime('%Y%m%d')

        df = self.hist_money(code, start_date, end_date)
        df.index = pd.to_datetime(df['trade_date'])
        df = df.sort_index()

        if isinstance(ndays, int):
            ndays = [ndays]
        for n in ndays:
            df[str(n) + '日累计'] = df['主力净流入'].rolling(n).sum()
        cols = ['主力净流入'] + [(str(n) + '日累计') for n in ndays]

        # 单位转为万元
        new_cols = [str(i) + '日主力净流入' for i in [1] + ndays]
        result = (df[cols] / 10000).dropna()
        result = result.rename(columns=dict(zip(cols, new_cols)))
        return result

    # 个股或债券或期货历史资金流向数据
    def hist_money(self, code, start_date, end_date):
        ts_code = utils.convert_tscode(code)
        sql = f'select * from {self.table_name} where ts_code="{ts_code}" and trade_date>{start_date} and trade_date<={end_date}'
        data = pd.read_sql(sql, self.engine)
        data = data.sort_values(['ts_code', 'trade_date'])
        data = data.drop_duplicates()
        return data

    # 获取指数数据
    def get_index_data(self, stock):
        if stock in index_dict.keys():
            code = index_dict[stock]
        else:
            code = stock

        # 判断是否为A股指数代码（数字开头）
        if code[0].isdigit():
            try:
                df = self.pro.index_daily(ts_code=code)
            except:
                print('指数代码或简称输入有误')
                return
        else:
            try:
                df = self.pro.index_global(ts_code=code)
            except:
                print('指数代码或简称输入有误')
                return
        df.index = pd.to_datetime(df.trade_date)
        df = df.rename(columns={'vol': 'volume'})
        df = (df.sort_index()).drop('trade_date', axis=1)
        return df

    # 获取全部指数价格数据
    def get_all_index_price(self):
        all_indexs = {'上证指数': '000001.SH', '深证成指': '399001.SZ', '沪深300': '000300.SH',
                      '创业板指': '399006.SZ', '上证50': '000016.SH', '中证500': '000905.SH',
                      '中小板指': '399005.SZ', '上证180': '000010.SH', '恒生指数': 'HSI',
                      '道琼斯': 'DJI', '标普500': 'SPX', '纳斯达克': 'IXIC', '法国CAC40': 'FCHI',
                      '德国DAX': 'GDAXI', '日经225': 'N225', '韩国综合': 'KS11',
                      '澳大利亚标普': 'AS51', '印度孟买': 'SENSEX', '台湾加权': 'TWII', }
        index_data = pd.DataFrame()
        for name, code in tqdm(all_indexs.items()):
            index_data[name] = self.get_index_data(code).close
        all_index_price = index_data.fillna(method='ffill').dropna()
        return all_index_price

    # 北向资金数据
    def get_north_money(self, start='20150101'):
        end = self.get_today()
        dates = self.get_trade_date(start, end)
        # tushare限制流量，每次只能获取300条记录
        df = self.pro.moneyflow_hsgt(start_date=start, end_date=end)
        # 拆分时间进行拼接，再删除重复项
        for i in range(0, len(dates) - 300, 300):
            d0 = self.pro.moneyflow_hsgt(start_date=dates[i], end_date=dates[i + 300])
            df = pd.concat([d0, df])
            # 删除重复项
            df = df.drop_duplicates()
            df.index = pd.to_datetime(df.trade_date)
            df = df.sort_index()
        return df

    # 获取两个日期之间的交易日
    def get_trade_date(self, start, end):
        n1 = np.where(self.cals > start)[0][0]
        n2 = np.where(self.cals <= end)[0][-1] + 1
        dates = self.cals[n1:n2]
        return dates

    # 获取数据库最新日期
    def get_sql_date(self):
        try:
            date = pd.read_sql(f"select max(trade_date) from {self.table_name}", self.engine)
            date = date.values[0][0]
        except:
            date = '20040101'
        return date

    # 获取今天日期
    def get_today(self):
        now = datetime.now().strftime('%Y%m%d')
        return now

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

    def update_dates(self, start, end):
        if start is None:
            start = self.get_sql_date()
        if end is None:
            end = self.get_today()
        dates = self.get_trade_date(start, end)
        return dates

    # 更新数据库数据
    def update_sql_data(self, start=None, end=None):
        dates = self.update_dates(start, end)
        self.sql_daily_data(dates)
        sql_date = self.get_sql_date()
        print(f"{self.table_name}数据库已更新至{sql_date}日数据")

    # 查询数据库信息
    def info_sql(self, table_name='daily_data'):
        sql1 = f'select count(*) from {table_name}'
        l = pd.read_sql(sql1, self.engine).values[0][0]
        print(f'统计查询的总数：{l}')
        sql2 = f'select min(trade_date) from {table_name}'
        sql3 = f'select max(trade_date) from {table_name}'
        t0 = pd.read_sql(sql2, self.engine).values[0][0]
        t1 = pd.read_sql(sql3, self.engine).values[0][0]
        print(f'数据期间：{t0}——{t1}')
        sql4 = f'select distinct ts_code from {table_name}'
        d = pd.read_sql(sql4, self.engine)
        print(f'数据库包含股票个数：{len(d)}')

    def get_ths_data(self, start='20180101'):
        end = self.get_today()
        dates = self.get_trade_date(start, end)[-300:]
        df = self.pro.ths_daily(start_date=start, end_date=end)
        # 拆分时间进行拼接，再删除重复项
        for date in tqdm(dates):
            temp = self.pro.ths_daily(trade_date=date)
            df = pd.concat([df, temp])
        return df.drop_duplicates()

    # 获取股票涨跌停板面板数据（历年个股），回测分析用
    def get_all_limit_data(self, tp='U'):
        # 16年开始有数据，设置2017年开始
        start = '20170101'
        end = self.get_today()
        dates = self.get_trade_date(start, end)
        df = self.pro.limit_list(trade_date=dates[0], limit_type=tp)
        for date in tqdm(dates[1:]):
            df_tem = self.pro.limit_list(trade_date=date, limit_type=tp)
            df = pd.concat([df, df_tem])
        # 获取细分行业数据
        industry = self.pro.stock_basic(exchange='', list_status='L',
                                        fields='ts_code,symbol,name,area,industry,list_date')
        # 排除新股
        industry = industry[industry.list_date < (parse(self.get_today()) - timedelta(60)).strftime('%Y%m%d')]
        cols1 = ['trade_date', 'ts_code', 'name', 'close', 'pct_chg', 'fc_ratio', 'fl_ratio']
        cols2 = ['ts_code', 'name', 'industry', 'list_date']
        dff = pd.merge(df[cols1], industry[cols2])
        return dff

    # 获取最近n日各行业累计涨停板情况
    def get_industry_limit(self, df, w_list=[1, 3, 5, 10], n=10):
        industry_limit = pd.DataFrame()
        # 获取最近10日各行业涨停板数据
        start = '20170101'
        end = self.get_today()
        dates = self.get_trade_date(start, end)
        d0 = w_list[-1]
        for d in dates[-d0:]:
            industry_limit[d] = df[df.trade_date == d].groupby('industry')['name'].count()
        industry_limit = industry_limit.fillna(0).sort_values(dates[-1], ascending=False).astype(int)
        result = pd.DataFrame()
        for w in w_list:
            result[str(w) + '累计'] = (industry_limit.rolling(w, axis=1).sum()).iloc[:, -1]
        result = result.sort_values(result.columns[-1], ascending=False)[:n]
        return result

    # 获取最新日期连板个股
    def get_con_up_stocks(self, delect_st_new=False):
        # delect_st_new=True即默认排除新股和st股
        # 获取最新交易数据
        d1 = self.latest_trade_date()
        dates = self.cals[np.where(self.cals < d1)[0]][-60:][::-1]
        fields = 'trade_date,ts_code,name,close,pct_chg,fl_ratio'
        up_limit = self.pro.limit_list(trade_date=d1, limit_type='U', fields=fields)
        if len(up_limit) == 0:
            d1 = dates[0]
            up_limit = self.pro.limit_list(trade_date=d1, limit_type='U', fields=fields)
            dates = dates[1:]
        if delect_st_new:
            # 分别剔除ST、*ST和新股（N开头）
            up_limit = up_limit[-(up_limit.name.str.startswith('ST') | \
                                  up_limit.name.str.startswith('*ST') | \
                                  up_limit.name.str.startswith('N'))]
        # 统计个股连板情况
        dict_up = {}
        for code in tqdm(up_limit.ts_code.values):
            up = 1
            for d in dates:
                if code in self.pro.limit_list(trade_date=d, limit_type='U').ts_code.values:
                    up += 1
                else:
                    break
            dict_up[code] = up
        # 输出dataframe
        dd = pd.DataFrame()
        dd['代码'] = dict_up.keys()
        dd['连板次数'] = dict_up.values()
        dd = dd.sort_values('代码')
        dd = dd[dd['连板次数'] > 1]
        dd['日期'] = d1
        temp = self.get_stock_basic()
        dd['名称'] = temp[temp.ts_code.isin(dd['代码'])].sort_values('ts_code').name.values
        dd = dd.sort_values('连板次数', ascending=False).reset_index(drop=True)
        return dd

    # 获取同花顺概念指数代码和简称
    def get_ths_dict(self):
        index_list = self.pro.ths_index()
        # 保留A股指数
        A_index_list = index_list.query("exchange=='A'").copy()
        A_index_list['nums'] = pd.to_numeric(A_index_list['count'])
        # 去掉缺失值
        A_index_list.dropna(inplace=True)
        # 删除代码重复项，筛掉概念成份个股数量低于12大于52（相当于取25%到75%分位数）
        # 保留type为N板块的指数
        final_index_list = (A_index_list
                            .drop_duplicates(subset=['ts_code'], keep='first')
                            .query("12<nums<52")
                            .query("type=='N'"))
        # 去掉样本股或成份股指数
        final_index_list = final_index_list[
            -final_index_list.name.apply(lambda s: s.endswith('样本股') or s.endswith('成份股'))]
        codes = list(final_index_list.ts_code)
        names = list(final_index_list.name)
        return dict(zip(codes, names))

    # 获取同花顺概念指数价格数据
    def get_ths_price(self, start='20180101'):
        data = self.get_ths_data(start)
        code_name = self.get_ths_dict()
        data = data[data.ts_code.isin(list(code_name.keys()))]
        # 删除重复缺失值、将代码使用概念中文名代替
        final_data = (data.sort_values(['ts_code', 'trade_date'])
                      .drop_duplicates()
                      .set_index(['trade_date', 'ts_code'])['close'].unstack()
                      .dropna(axis=1)
                      .rename(columns=code_name))
        return final_data

    # 获取同花顺概念指数成分股
    def get_ths_member(self, name):
        '''name可以为同花顺概念指数代码或简称'''
        if name[0].isdigit():
            code = name
        else:
            d = self.get_ths_dict()
            code = list(d.keys())[list(d.values()).index(name)]
        dd = self.pro.ths_member(ts_code=code)
        df = pd.DataFrame()
        for c, n in tqdm(dict(dd[['code', 'name']].values).items()):
            df[n] = self.get_ohlc_data(c).close[-200:]
        df = df.fillna(method='ffill')
        return df

    ##财务数据##
    # 获取某只股票或当前日期业绩预告数据
    def get_stock_forecast(self, stock=None, date=None):
        if stock is None:
            if date is not None:
                dd = self.pro.forecast(ann_date=date)
            else:
                now = self.get_today()
                dd = self.pro.forecast(ann_date=now)
        else:
            code = self.trans_code(stock)
            try:
                dd = self.pro.forecast_vip(ts_code=code)
            except:
                dd = self.pro.forecast(ts_code=code)
        dd.index = pd.to_datetime(dd.ann_date)
        # 计算平均变动幅度
        dd['chg_avg%'] = (dd['p_change_min'] + dd['p_change_max']) / 2
        cols = ['ts_code', 'end_date', 'type', 'chg_avg%', 'summary', 'change_reason']
        dd = dd.sort_index()[cols]
        return dd

    # 获取某期间所有股票的业绩预告数据（用于回测）,默认是20100101
    def get_all_forecast(self, start='2010101'):
        end = self.get_today()
        dates = self.get_trade_date(start, end)
        df = self.pro.forecast_vip(ann_date=dates[0])
        for d in tqdm(dates[1:]):
            df_temp = self.pro.forecast_vip(ann_date=d)
            df = pd.concat([df, df_temp]).reset_index(drop=True)
        df.index = pd.to_datetime(df.ann_date)
        # 计算平均变动幅度
        df['chg_avg%'] = (df['p_change_min'] + df['p_change_max']) / 2
        cols = ['ts_code', 'end_date', 'type', 'chg_avg%', 'summary', 'change_reason']
        df = df.sort_index()[cols]
        return df

    # 获取某只股票或当前日期财务指标数据，需5000积分
    def get_stock_indicator(self, stock=None, start='20180101', end='', pepb=False, fields=''):
        '''使用所有默认参数时，得到的是最新日期所有个股的财务指标数据
           stock输入个股名称或代码，获取个股财务指标数据
           pepb获取个股市盈率和市净率数据
           fields指定要获取的财务指标数据
        '''
        if stock is not None:
            code = self.trans_code(stock)
            try:
                dd = self.pro.fina_indicator_vip(ts_code=code, start_date=start, end_date=end, fields=fields)
            except:
                dd = self.pro.fina_indicator(ts_code=code, start_date=start, end_date=end, fields=fields)
            dd.set_index('end_date', inplace=True)
            dd = dd.sort_index().fillna(0)
            if pepb:
                # 获取市盈率和市净率指标（pe、pb数据）
                pbe = self.pro.daily_basic(ts_code=code, fields='trade_date,pe_ttm,pb')
                pbe.set_index('trade_date', inplace=True)
                pbe = pbe.sort_index()
                # 合并数据
                dd = pd.merge(dd, pbe, left_index=True, right_index=True, how='left')
        else:
            now = self.get_today()
            dd = self.pro.fina_indicator_vip(ann_date=now)
        dd = dd[dd.update_flag == '1']
        return dd

    # 获取某股票最新主营业务构成tp='D'代表按地区划分
    def get_mainbz(self, stock):
        def mainbz(code, tp):
            dd = self.pro.fina_mainbz(ts_code=code, type=tp)
            dd = dd.sort_values('end_date')
            date = dd.end_date.iloc[-1]
            dd = dd[dd.end_date == date][['bz_item', 'bz_sales']]
            # 单位百万元
            dd['bz_sales'] = (dd['bz_sales'] / 1000000).round(2).sort_values()
            dd = dd.rename(columns=dict(zip(dd.columns, ['类型', '收入(百万)'])))
            return dd

        code = self.trans_code(stock)
        # name=self.trans_name(stock)
        dd0 = mainbz(code, tp='P')
        dd1 = mainbz(code, tp='D')
        data_dict = {'P': dd0, 'D': dd1}
        return data_dict

    # 获取某股票某日期以来公司公告,默认是今年以来
    def get_stock_report(self, stock, date=None):
        code = self.trans_code(stock)
        df = self.pro.anns(ts_code=code)
        if date is None:
            date = str(datetime.now().year)
        # 获取最近两年公告
        df = df[df['ann_date'] > date]
        return df

    # 获取今天新浪财经新闻快讯文本数据
    def get_sina_news(self):
        date = datetime.now().strftime('%Y-%m-%d')
        df = self.pro.news(start_date=date, src='sina').content.apply(lambda s: str(s))
        return list(df)

    # 获取最新同花顺、东方财富和云财经新闻标题内容
    def get_news_title(self):
        date = datetime.now().strftime('%Y-%m-%d')
        text = []

        # 同花顺、东方财富和云财经新闻标题
        for src in ['10jqka', 'eastmoney', 'yuncaijing']:
            new = self.pro.news(start_date=date, src=src).title.apply(lambda s: str(s))
            text += list(new)
        return text

    # 全球财经指标，默认中国
    def get_macro_indicator(self, c='中国'):
        ss = self.pro.eco_cal(country=c)
        ss = ss[-(ss.value == '')]
        return ss
