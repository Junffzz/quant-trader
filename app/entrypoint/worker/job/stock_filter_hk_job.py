import schedule

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
import app.gateways as gateways
from app.entrypoint.worker.job.job_base import JobBase
from app.plugins.dingtalk import bot as chatbot


class StockFilterHKJob(JobBase):
    def __init__(self, run_threaded):
        super().__init__()
        self.strategy = None
        self.run_threaded = run_threaded
        self.jobs = [
            schedule.every().monday.at("17:30").do(self.run_threaded, self.handle_task),
            schedule.every().tuesday.at("17:30").do(self.run_threaded, self.handle_task),
            schedule.every().wednesday.at("17:30").do(self.run_threaded, self.handle_task),
            schedule.every().thursday.at("17:30").do(self.run_threaded, self.handle_task),
            schedule.every().friday.at("17:30").do(self.run_threaded, self.handle_task),
        ]

    def start(self):
        for job in self.jobs:
            # 添加标签
            job.tag('StockFilterHKJob')

    def stop(self):
        for job in self.jobs:
            schedule.cancel_job(job)

    def handle_task(self):
        self.fetch_stocks_filter()

    def fetch_stocks_filter(self):
        """
        策略思想：
        选股池：
        1.长期处于均线下降趋势
        2.处于价格底部，比如低于52周低价
        3.MACD处于底部

        买卖信号：
        1.期待反转
        2.技术指标
        """
        trade_market = TradeMarket.HK

        gateway_name = "Futu"
        gateway = gateways.FutuQuoteGateway(trade_market)

        buy_filter_list = []
        buy_filter_list.extend(self.common_filter())
        buy_filter_list.extend(self.buy_filter())
        buy_stocks = gateway.fetch_stock_filter(filter_list=buy_filter_list)

        sell_filter_list = []
        sell_filter_list.extend(self.common_filter())
        sell_filter_list.extend(self.sell_filter())
        sell_stocks = gateway.fetch_stock_filter(filter_list=sell_filter_list)
        self.send_message(buy_stocks, sell_stocks)
        print("send_message success.")

    @staticmethod
    def send_message(buy_stocks=[], sell_stocks=[]):
        if len(buy_stocks) == 0 and len(sell_stocks) == 0:
            return
        content = ''
        content += 'buy signal:'
        for row in buy_stocks:
            content += row["stock_code"] + ":" + row["cur_price"]

        content += 'sell signal:'
        for row in sell_stocks:
            content += row["stock_code"] + ":" + row["cur_price"]
        chatbot.send_markdown("filter hk stocks", content)

    @staticmethod
    def common_filter():
        simple_filter = SimpleFilter()
        simple_filter.filter_min = 2
        simple_filter.filter_max = 1000
        simple_filter.stock_field = StockField.CUR_PRICE
        simple_filter.is_no_filter = False
        # simple_filter.sort = SortDir.ASCEND

        return [simple_filter]

    @staticmethod
    def buy_filter():
        ma1_filter = CustomIndicatorFilter()
        ma1_filter.ktype = KLType.K_DAY
        ma1_filter.stock_field1 = StockField.MA5
        ma1_filter.stock_field2 = StockField.MA10
        ma1_filter.relative_position = RelativePosition.CROSS_UP
        ma1_filter.is_no_filter = False

        ma2_filter = CustomIndicatorFilter()
        ma2_filter.ktype = KLType.K_DAY
        ma2_filter.stock_field1 = StockField.MA10
        ma2_filter.stock_field2 = StockField.MA20
        ma2_filter.relative_position = RelativePosition.CROSS_UP
        ma2_filter.is_no_filter = False

        ma3_filter = CustomIndicatorFilter()
        ma3_filter.ktype = KLType.K_DAY
        ma3_filter.stock_field1 = StockField.MA20
        ma3_filter.stock_field2 = StockField.MA30
        ma3_filter.relative_position = RelativePosition.CROSS_UP
        ma3_filter.is_no_filter = False

        ma4_filter = CustomIndicatorFilter()
        ma4_filter.ktype = KLType.K_DAY
        ma4_filter.stock_field1 = StockField.MA30
        ma4_filter.stock_field2 = StockField.MA60
        ma4_filter.relative_position = RelativePosition.CROSS_UP
        ma4_filter.is_no_filter = False

        ma5_filter = CustomIndicatorFilter()
        ma5_filter.ktype = KLType.K_DAY
        ma5_filter.stock_field1 = StockField.MA60
        ma5_filter.stock_field2 = StockField.MA120
        ma5_filter.relative_position = RelativePosition.CROSS_UP
        ma5_filter.is_no_filter = False
        return [ma1_filter, ma2_filter, ma3_filter, ma4_filter, ma5_filter]

    @staticmethod
    def sell_filter():
        ma1_filter = CustomIndicatorFilter()
        ma1_filter.ktype = KLType.K_DAY
        ma1_filter.stock_field1 = StockField.MA5
        ma1_filter.stock_field2 = StockField.MA10
        ma1_filter.relative_position = RelativePosition.CROSS_DOWN
        ma1_filter.is_no_filter = False

        ma2_filter = CustomIndicatorFilter()
        ma2_filter.ktype = KLType.K_DAY
        ma2_filter.stock_field1 = StockField.MA10
        ma2_filter.stock_field2 = StockField.MA20
        ma2_filter.relative_position = RelativePosition.CROSS_DOWN
        ma2_filter.is_no_filter = False

        ma3_filter = CustomIndicatorFilter()
        ma3_filter.ktype = KLType.K_DAY
        ma3_filter.stock_field1 = StockField.MA20
        ma3_filter.stock_field2 = StockField.MA30
        ma3_filter.relative_position = RelativePosition.CROSS_DOWN
        ma3_filter.is_no_filter = False

        ma4_filter = CustomIndicatorFilter()
        ma4_filter.ktype = KLType.K_DAY
        ma4_filter.stock_field1 = StockField.MA30
        ma4_filter.stock_field2 = StockField.MA60
        ma4_filter.relative_position = RelativePosition.CROSS_DOWN
        ma4_filter.is_no_filter = False

        ma5_filter = CustomIndicatorFilter()
        ma5_filter.ktype = KLType.K_DAY
        ma5_filter.stock_field1 = StockField.MA60
        ma5_filter.stock_field2 = StockField.MA120
        ma5_filter.relative_position = RelativePosition.CROSS_DOWN
        ma5_filter.is_no_filter = False

        return [ma1_filter, ma2_filter, ma3_filter, ma4_filter, ma5_filter]
