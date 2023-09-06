import app.facade as facade
from app.domain.stores import StockMarket

stock_service = StockMarket()


def filter_rps():
    # RPS输入数据不能有缺失值,时间长度至少要大于250日
    # 获取全市场价格数据耗时较长（1分钟左右）

    cols = ['close', 'open', 'high', 'low']
    # 获取沪深全市场A股代码
    codes = stock_service.get_codelist()
    codes = codes[:1000]
    # 获取沪深全市场A股2020年以来行情数据后复权价格
    data = facade.get_data(code_list=codes, start='20200101', fqt=2)
    # 转成面板数据
    data = data.drop_duplicates()
    data = data.set_index(['code'], append=True)[cols]
    data = data.unstack()
    data.head(10)

    # 获取价格
    prices = data['close'].dropna(axis=1)
    rps = strategies.RPS(prices)
    df_rps = rps.date_rps()

    # 使用RPS大于90以上选股，可以将股票池从几千只缩小成几百只
    # 再结合公司基本面进一步选股
    len(df_rps[df_rps.rps_120 > 90])
    # 查看一只股票的plot图
    rps.plot_stock_rps('600026')

    # 根据5或20日筛选短期强势股
    df_rps.sort_values('rps_20', ascending=False)[:10]

    # MM趋势选股池
    mm_trend = prices.apply(strategies.MM_trend).T
    mm_result = mm_trend.query('meet_criterion==1')
    print("mm_result = ", mm_result)


if __name__ == '__main__':
    filter_rps()
