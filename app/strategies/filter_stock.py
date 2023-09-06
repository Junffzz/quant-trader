import pandas as pd


def filter_daily_trade(trade_daily: pd.DataFrame) -> pd.DataFrame:
    """
    每日指标选股逻辑：
    - 换手率大于5%。换手率是每天交易的股数占流通股数量的比例，一般处于2%-5%区间见，说明其中没有大资金，低于1%成交低迷。换句话说股票换手率高一般意味着其流通性好，交易活跃，属于热门股；换手率越低，则表明股票交易不活跃，属于冷门股。
    - 量比大于1。量比是股市开市后平均每分钟的成交量与过去5个交易日平均每分钟成交量之比。量比的数值越大，表明了该股当日流入的资金越多，市场活跃度越高；反之，量比值越小，说明了资金的流入越少，市场活跃度越低。
    - 流通市值大于100亿元。目前各行业进入头部垄断市场，小市值企业很难逆袭，选择流通市值100亿以上个股
    - 市盈率大于0。剔除市盈率小于0即公司亏损个股，尽管A股很多涨幅很大的炒作股都是亏损企业，但容易踩雷。
    """

    # 单日主力资金净流入
    c1 = trade_daily['主力净流入'] > 0
    # 量比
    c2 = trade_daily['量比'] > 1
    # 市盈率
    c3 = (0 < trade_daily['市盈率']) & (trade_daily['市盈率'] < 80)
    # 流通市值大于100亿元
    c4 = trade_daily['流通市值'] / 10000 > 100
    # 换手率
    c5 = trade_daily['换手率'] > 5
    # 还可以结合市净率、股息率等指标进一步选股
    c = c1 & c2 & c3 & c4 & c5
    # 以主力净流入排名，查看前十
    result = trade_daily[c]
    daily_cols = ['trade_date', 'symbol', '主力净流入', '换手率', '量比', '市盈率', '市净率', '市销率', '股息率','流通市值']
    daily_result = result.set_index('ts_code')[daily_cols]
    return daily_result

def filter_daily_indicator(trade_daily: pd.DataFrame) -> pd.DataFrame:
    """
    每日指标选股逻辑：
    - 换手率大于5%。换手率是每天交易的股数占流通股数量的比例，一般处于2%-5%区间见，说明其中没有大资金，低于1%成交低迷。换句话说股票换手率高一般意味着其流通性好，交易活跃，属于热门股；换手率越低，则表明股票交易不活跃，属于冷门股。
    - 量比大于1。量比是股市开市后平均每分钟的成交量与过去5个交易日平均每分钟成交量之比。量比的数值越大，表明了该股当日流入的资金越多，市场活跃度越高；反之，量比值越小，说明了资金的流入越少，市场活跃度越低。
    - 流通市值大于100亿元。目前各行业进入头部垄断市场，小市值企业很难逆袭，选择流通市值100亿以上个股
    - 市盈率大于0。剔除市盈率小于0即公司亏损个股，尽管A股很多涨幅很大的炒作股都是亏损企业，但容易踩雷。
    """

    # 单日主力资金净流入
    c1 = trade_daily['main_net_inflow'] > 0
    # 量比
    c2 = trade_daily['volume_ratio'] > 1
    # 市盈率
    c3 = (0 < trade_daily['pe_ttm']) & (trade_daily['pe_ttm'] < 80)
    # 流通市值大于100亿元
    c4 = trade_daily['circ_mv'] / 10000 > 100
    # 换手率
    c5 = trade_daily['turnover_rate_f'] > 5
    # 还可以结合市净率、股息率等指标进一步选股
    c = c1 & c2 & c3 & c4 & c5
    # 以主力净流入排名，查看前十
    result = trade_daily[c]
    daily_result = result.set_index('ts_code')
    return daily_result