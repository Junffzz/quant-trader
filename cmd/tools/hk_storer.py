import sys
import os

sys.path.append(os.path.dirname(sys.path[0]) + "/../")

from datetime import datetime
from typing import Dict, List

import pandas as pd

from futu import (
    SortDir,
    FinancialQuarter,
    KLType,
    RelativePosition,
    StockField,
    SortField,
    SimpleFilter,
    FinancialFilter,
    CustomIndicatorFilter,
)

from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.data import Bar
import app.gateways as gateways
from app.domain.security import Stock


def main():
    trade_mode = TradeMode.BACKTEST
    trade_mode = TradeMode.SIMULATE
    trade_market = TradeMarket.HK
    fees = gateways.BaseFees

    gateway_name = "Futu"
    UseGateway = gateways.FutuGateway  # CqgGateway
    start = datetime(2015, 10, 1, 9, 30, 0, 0)
    today = datetime.today()
    end = datetime(today.year, today.month, today.day, 23, 59, 0)

    stock_list = [
        Stock(code="HK.01157", lot_size=100, security_name="中联重科", exchange=Exchange.SEHK),
        Stock(code="HK.09868", lot_size=100, security_name="小鹏汽车-W", exchange=Exchange.SEHK),
        Stock(code="HK.03800", lot_size=1000, security_name="协鑫科技", exchange=Exchange.SEHK),
        Stock(code="HK.02420", lot_size=500, security_name="子不语", exchange=Exchange.SEHK),
        Stock(code="HK.00873", lot_size=1000, security_name="世茂服务", exchange=Exchange.SEHK),
        Stock(code="HK.09939", lot_size=500, security_name="开拓药业-B", exchange=Exchange.SEHK),
        Stock(code="HK.09696", lot_size=200, security_name="天齐锂业", exchange=Exchange.SEHK),
    ]

    trading_sessions = {str: list}
    for s in stock_list:
        trading_sessions[s.code] = []
        trading_sessions[s.code].append([datetime(1970, 1, 1, 9, 30, 0, 0), datetime(1970, 1, 1, 19, 0, 0, 0)])

    gateway = UseGateway(
        securities=stock_list,
        trade_market=trade_market,
        gateway_name=gateway_name,
        fees=fees,
        start=start,
        end=end,
        trading_sessions=trading_sessions,
        num_of_1min_bar=180
    )

    gateway.SHORT_INTEREST_RATE = 0.0
    gateway.trade_mode = trade_mode

    freq = "1Day"
    for stock in stock_list:
        data_df = gateway.get_historical_kline_df(
            security=stock,
            freq=freq,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d")
        )
        trade_days = gateway.get_trading_days()
        save_csv(data_df, trade_days, freq, path="/home/zhaojunfeng/workspace/python/quant-trader")


def save_csv(data_df: pd.DataFrame, trade_days: List, freq: str, path=None):
    k_freq_path = "K_unknown"
    if freq == "1Min":
        k_freq_path = "K_1M"
    elif freq == "1Day":
        k_freq_path = "K_1D"
    code = data_df.iloc[0].code
    result_path = f"{path}/data/k_line/{k_freq_path}/{code}/"
    if not os.path.exists(result_path):
        os.makedirs(result_path)

    # if freq == "1Min":
    data_df.set_index(["time_key"], drop=False, inplace=True)
    for trd_date in trade_days:
        df = data_df[(data_df.index >= trd_date["time"]) & (data_df.index <= trd_date["time"] + " 23:59:59")]
        if df.empty is True:
            continue
        result_path_filename = result_path + f"{trd_date['time']}.csv"
        df.to_csv(result_path_filename, index=False)
        print(result_path_filename)
    # elif freq == "1Day":
    #     result_path_filename += f"day.csv"
    #     data_df.to_csv(result_path_filename, index=False)

    return


if __name__ == "__main__":
    main()
