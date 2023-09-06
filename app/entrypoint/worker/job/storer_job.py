import schedule

import app.domain as domain
import app.facade as facade
import app.utils as utils


class StorerJob:
    def __init__(self, run_threaded):
        self.strategy = None
        self.run_threaded = run_threaded
        self.jobs = [
            schedule.every().monday.at("18:30").do(self.run_threaded, self.handle_task),
            schedule.every().tuesday.at("18:30").do(self.run_threaded, self.handle_task),
            schedule.every().wednesday.at("18:30").do(self.run_threaded, self.handle_task),
            schedule.every().thursday.at("18:30").do(self.run_threaded, self.handle_task),
            schedule.every().friday.at("18:30").do(self.run_threaded, self.handle_task),
        ]

    def start(self):
        for job in self.jobs:
            # 添加标签
            job.tag('store_job')

    def stop(self):
        for job in self.jobs:
            schedule.cancel_job(job)

    def handle_task(self):
        self.stock_store()

    def stock_store(self):
        end_date = utils.get_today_date()
        bar_storer = domain.BarStorer(data_path="../../data/", file_name="cn_stock.hdf5")
        bar_storer.update_daily_data(end=end_date)
