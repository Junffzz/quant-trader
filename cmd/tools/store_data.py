import pandas as pd

import app.facade as facade
import app.domain as domain
from app.domain.stores.security_market_storer import SecurityMarketStorer
import app.constants as constants
import app.utils as utils
import warnings

warnings.filterwarnings('ignore')

# tudata = facade.TushareData(token=constants.TUSHARE_TOKEN,my_path='../../sql_data/',db_name='stock_data.db')


class StockDataStore:
    def __init__(self, data_path='../../data', file_name=''):
        self.stock_s = SecurityMarketStorer()
        self._cols = ['open', 'high', 'low', 'close', 'volume', 'turnover', 'turnover_rate']
        self._data_path = data_path
        self._file_name = file_name

    def init_load_stock(self, start='20100101', end='20230101'):
        hdf = pd.HDFStore(self._data_path + self._file_name, 'w')

        code_list = self.stock_s.get_codelist()
        code_groups = utils.arr_chunk_groups(code_list, 100)
        for codes in code_groups:
            data = facade.get_data(code_list=codes, start=start, end=end, fqt=2)

            stock_realtime_df = self.stock_s.get_stock_realtime(codes)
            codes_dict = stock_realtime_df.set_index(['code']).to_dict('index')

            for code in codes:
                symbol = code
                code_data = data[data.code == code][self._cols]
                hdf.put(key=symbol, value=code_data, format='table', data_columns=True)
                if hdf.get_node(symbol) is None:
                    continue

                hdf.get_storer(symbol).attrs['attr_code'] = code
                hdf.get_storer(symbol).attrs['attr_name'] = codes_dict[code]['name']
                hdf.get_storer(symbol).attrs['attr_listed_date'] = codes_dict[code]['listed_date']

        hdf.close()

    def append_stock_data(self, start='20100101', end='20230101'):
        hdf = pd.HDFStore(self._data_path + self._file_name, 'a')

        codes = self.stock_s.get_codelist()
        codes = codes[:50]
        data = facade.get_data(code_list=codes, start=start, end=end, fqt=2)

        for code in codes:
            symbol = code
            code_data = data[data.code == code][self._cols]
            hdf.append(key=symbol, value=code_data, format='table', data_columns=True)

        hdf.close()


# 存储股票基本信息
def store_stock_basic():
    # stock_storer = SecurityMarketStorer()

    # 中国
    data=facade.get_data("RM309",start='20230101')
    print(data)

    # 美国
    data = facade.get_data("HG23K", start='20230101')
    print(data)


def store_stock_kline_data():
    bar_storer = domain.BarStorer(tudata, data_path="../../data/", file_name="cn_stock.hdf5")
    bar_storer.update_daily_data(start='20200101')
    ret = bar_storer.get_trade_daily_data(date='20230215')
    print("ret 20230215 data = ", ret)
    bar_storer.stop()


if __name__ == '__main__':
    # store = StockDataStore(data_path='/Users/ZhaoJunfeng/workspace/python/quant-trader/', file_name='cn_stock.hdf5')
    # store.init_load_stock(start='20100101', end='20230101')
    # add_stock_data()

    # data=facade.hist_money(603031)
    # data.head(10)

    store_stock_basic()

    # store_stock_kline_data()
