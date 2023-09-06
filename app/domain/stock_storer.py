import app.facade as facade
import app.utils as utils
import app.domain.repository as repo


class StockStorer:
    def __init__(self, tudata: facade.TushareData):
        self.tudata = tudata
        self.stock_repo = repo.StockRepo()

    def get_stock_list(self):
        stock_list = self.stock_repo.get_stock_basic('china')
        return stock_list

    def update_stock_basic(self):
        dd = self.tudata.get_stock_basic()

        fields = ['name', 'ts_code', 'region_tag', 'fullname', 'enname', 'symbol', 'exchange', 'industry',
                  'listed_date', 'delisted_date', 'list_status', 'classify', 'is_hs', 'curr_type', 'stores',
                  'area']
        data_list = []  # 新建一个空列表用来存储元组数据
        for index, row in dd.iterrows():
            name = row['name']
            ts_code = row['ts_code']
            region_tag = 'china'
            fullname = row['fullname']
            enname = row['enname']
            symbol = row['symbol']
            exchange = row['exchange']
            industry = row['industry']
            listed_date = row['list_date']
            delisted_date = row['delist_date']
            list_status = row['list_status']
            classify = ''
            is_hs = row['is_hs']
            curr_type = row['curr_type']
            market = row['stores']
            area = row['area']

            tup = (name, ts_code, region_tag, fullname, enname, symbol, exchange, industry, listed_date, delisted_date,
                   list_status, classify, is_hs, curr_type, market, area)  # 构造元组
            data_list.append(tup)  # [(),(),()...]

        self.stock_repo.adds(data_list)

    def stop(self):
        pass
