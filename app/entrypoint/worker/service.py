import threading
import time
import schedule
from threading import Thread

import app.entrypoint.worker.job as job
from app.service.hk_stock_service import HKStockService


class WorkerService:
    def __init__(self):
        # self.good_price_strategy_job = job.GoodPriceStrategyJob(self.run_threaded)
        self._jobs = [
            job.StockFilterHKJob(self.run_threaded),
        ]
        # job Thread
        self._threads = [
            Thread(target=self._job_thread),
            Thread(target=self._service_thread),
        ]

    def start(self):
        for j in self._jobs:
            j.start()

        # threads start
        for thread in self._threads:
            thread.start()

    def wait(self):
        # wait thread
        for thread in self._threads:
            thread.join()

    def stop(self):
        for j in self._jobs:
            j.stop()

    @staticmethod
    def _service_thread():
        hk_stock_service = HKStockService()
        hk_stock_service.handle()

    @staticmethod
    def _job_thread():
        while 1:
            schedule.run_pending()
            time.sleep(1)

    @staticmethod
    def run_threaded(job_func):
        job_thread = threading.Thread(target=job_func)
        job_thread.start()
