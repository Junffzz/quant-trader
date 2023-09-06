import json
import time
from datetime import datetime,timedelta,timezone


from app.markets.data import SubscribeQuote
from typing import List, Any

import redis
import exchange_calendars as xcals

from app.facade.trade import realtime_data
from app.config.configure import config
from app.utils import logger

quote_publish_channel = 'quant_trader_quotes_channel'


class QuotesService:
    def __init__(self):
        self.quotes: List[SubscribeQuote] = []

        host = config.redis.get("host", "localhost")
        port = config.redis.get("port", "6379")
        password = config.redis.get("password", "")
        db = config.redis.get("db", 1)
        pool = redis.ConnectionPool(host=host, port=port, password=password, db=db)
        self.rClient = redis.Redis(connection_pool=pool, db=db)

        self.calendars = {}
        self._init_calendar()

    def _init_calendar(self):
        self.calendars['us_calendar'] = xcals.get_calendar("XNYS")

    def subscribe(self, quote: SubscribeQuote = None):
        self.quotes.append(quote)

    def start(self):
        while True:
            code_list = self._load_quote_codes()
            if len(code_list) == 0:
                continue

            codes = []
            for co in code_list:
                if co.split(".")[0] == 'US' and self._is_now_trading_time('US') is False:
                    continue
                codes.append(co.split(".")[1])

            if len(codes) == 0:
                continue

            df = realtime_data("", codes)
            df['close'] = df['current']
            for code in code_list:
                df.loc[df['code'] == code.split(".")[1], 'code'] = code
            ret = self.rClient.publish(quote_publish_channel, df.to_json())
            logger.info("redis publish", ret)
            time.sleep(10)

    def _load_quote_codes(self) -> List:
        """
        从redis中加载行情配置
        """
        # securities = [
        #     Stock(code="US.NVDA", lot_size=1, security_name="英伟达", exchange=Exchange.NASDAQ),
        #     Stock(code="US.PDD", lot_size=1, security_name="拼多多", exchange=Exchange.NASDAQ),
        #     Stock(code="US.TSLA", lot_size=1, security_name="特斯拉", exchange=Exchange.NASDAQ),
        # ]

        rest = self.rClient.hgetall('quant_trader_quotes_config')
        for k, item in rest.items():
            quote = SubscribeQuote.from_json(item)
            self.quotes.append(quote)

        # self.quotes.append(quote)
        codes = []
        for quote in self.quotes:
            codes.extend([security.code for security in quote.securities])
        return list(set(codes))

    def _is_now_trading_time(self, type_name='US'):
        utc_now = datetime.now(timezone.utc)
        if type_name == 'US':
            us_now = utc_now
            return self.calendars['us_calendar'].is_open_on_minute(us_now.strftime("%Y-%m-%d %H:%M"))

        return False
