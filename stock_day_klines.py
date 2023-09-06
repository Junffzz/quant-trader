# -*- coding: utf-8 -*-

import app.facade as facade

from app.domain.stores import StockMarket
import app.constants.common as com_const


def main():
    df = facade.get_data('601318', '20221104')
    df.tail()


def get_codes():
    stock_service = StockMarket()
    code_list = stock_service.get_codelist()
    print('a股：', code_list)
    code_list = stock_service.get_codelist(market=com_const.MarketEnum.HK)
    print('港股：', code_list)
    code_list = stock_service.get_codelist(market=com_const.MarketEnum.US)
    print('美股：', code_list)


def get_realtime_data():
    stock_service = StockMarket()
    df = stock_service.get_stock_realtime("BYSI")
    print(df)


if __name__ == '__main__':
    # print_hi('PyCharm')
    main()
    # get_codes()
    # get_realtime_data()