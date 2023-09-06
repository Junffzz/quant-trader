import sys
import os

sys.path.append(os.path.dirname(sys.path[0]) + "/../")

from datetime import datetime
from typing import Dict, List

import pandas as pd

from app.constants import TradeMode, TradeMarket, Exchange
from app.domain.security import Stock
from app.facade.trade import get_data


def main():
    trade_mode = TradeMode.BACKTEST
    trade_market = TradeMarket.US

    start = datetime(2020, 1, 1, 9, 30, 0, 0)
    today = datetime.today()
    end = datetime(today.year, today.month, today.day, 23, 59, 0)

    stock_list = [
        # Stock(code="US.PDD", lot_size=1, security_name="拼多多", exchange=Exchange.NASDAQ),
        # Stock(code="US.XPEV", lot_size=1, security_name="小鹏汽车", exchange=Exchange.NASDAQ),
        # Stock(code="US.TAL", lot_size=1, security_name="好未来", exchange=Exchange.NASDAQ),
        Stock(code="US.BILI", lot_size=1, security_name="哔哩哔哩", exchange=Exchange.NASDAQ),
        Stock(code="US.NIO", lot_size=1, security_name="蔚来", exchange=Exchange.NASDAQ),
        Stock(code="US.TSLA", lot_size=1, security_name="特斯拉", exchange=Exchange.NASDAQ),
        Stock(code="US.MOMO", lot_size=1, security_name="挚文集团", exchange=Exchange.NASDAQ),
        Stock(code="US.BIDU", lot_size=1, security_name="百度", exchange=Exchange.NASDAQ),
        Stock(code="US.CCL", lot_size=1, security_name="嘉年华邮轮", exchange=Exchange.NASDAQ),
    ]

    freq = "1Day"
    for stock in stock_list:
        data_df = get_data(stock.code.split(".")[1], start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
        data_df['time_key'] = data_df.index
        data_df['time_key'] = data_df['time_key'].apply(lambda x: x.to_pydatetime().strftime("%Y-%m-%d 00:00:00"))
        trade_days = [x.to_pydatetime().strftime("%Y-%m-%d") for _, x in enumerate(data_df.index.tolist())]
        data_df = data_df[['code', 'time_key', 'open', 'high', 'low', 'close', 'volume', 'turnover', 'turnover_rate']]
        save_csv(data_df, trade_days, freq, path="../..")


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
    # data_df.set_index(["time_key"], drop=False, inplace=True)
    for trd_date in trade_days:
        df = data_df[(data_df.time_key >= trd_date) & (data_df.time_key <= trd_date + " 23:59:59")]
        if df.empty is True:
            continue
        result_path_filename = result_path + f"{trd_date}.csv"
        df.to_csv(result_path_filename, index=False)
        print(result_path_filename)
    # elif freq == "1Day":
    #     result_path_filename += f"day.csv"
    #     data_df.to_csv(result_path_filename, index=False)

    return


if __name__ == "__main__":
    main()
