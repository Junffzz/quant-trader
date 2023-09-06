import schedule

from app.domain.stores import StockMarket
from app.strategies import GoodPriceStrategy
from app.infra.email.smtp import NotifyEmail
import app.facade as facade


class GoodPriceStrategyJob:
    def __init__(self, run_threaded):
        self.strategy = None
        self.market_object = StockMarket()
        self.run_threaded = run_threaded
        self.jobs = [
            schedule.every().monday.at("13:30").do(self.run_threaded, self.handle_good_price_task),
            schedule.every().tuesday.at("13:30").do(self.run_threaded, self.handle_good_price_task),
            schedule.every().wednesday.at("13:30").do(self.run_threaded, self.handle_good_price_task),
            schedule.every().thursday.at("13:30").do(self.run_threaded, self.handle_good_price_task),
            schedule.every().friday.at("13:30").do(self.run_threaded, self.handle_good_price_task),
        ]
        self.handle_good_price_task()

    def start(self):
        for job in self.jobs:
            # 添加标签
            job.tag('strategies')

    def stop(self):
        for job in self.jobs:
            schedule.cancel_job(job)

    def handle_good_price_task(self):
        # A股
        self.execute_subtask_for_A()

    # A股子任务
    def execute_subtask_for_A(self):
        ten_year_bonds_yield = round(float(facade.get_cn_bonds_yield_for10_from_chinamoney()), 2) / 100
        # 好价格实例
        strategy_ins = GoodPriceStrategy(ten_year_bonds_yield)

        stock_codes = self.market_object.get_codelist()
        good_all_result = self.codes_strategy_iterator(stock_codes, strategy_ins)
        # 发送邮件
        email = NotifyEmail()
        html = email.build_good_price_html(ten_year_bonds_yield, good_all_result)
        email.send_email_html("Financing <zjf2616@163.com>", "已检测A股好价格", html, ["981248356@qq.com"])
        print("good_price_strategy run subtask_for_A successful.")
        return good_all_result

    # 美股子任务
    def execute_subtask_for_US(self):
        ten_year_bonds_yield = round(float(facade.get_cn_bonds_yield_for10_from_chinamoney()), 2) / 100
        # 好价格实例
        strategy_ins = GoodPriceStrategy(ten_year_bonds_yield)

        stock_codes = self.market_object.get_codelist()
        good_all_result = self.codes_strategy_iterator(stock_codes, strategy_ins)

        print("good_price_strategy run subtask_for_US successful.")
        return good_all_result

    def codes_strategy_iterator(self, stock_codes: tuple, strategy_ins) -> list:
        result = []
        for i in range(0, len(stock_codes), 100):
            codes = stock_codes[i:i + 100]
            stocks_realtime_data = self.market_object.get_stock_realtime(codes)
            # 推导式
            good_pe = 15.0
            sub_result = [strategy_ins.single_good_price(good_pe, indicator) for index, indicator in
                          stocks_realtime_data.iterrows()]
            result.extend(sub_result)
        return result


