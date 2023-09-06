class GoodPriceStrategy(object):
    def __init__(self, bonds_yield: float):
        self._default_good_pe = 15.0  # 好价格市盈率
        self._ten_year_bonds_yield = bonds_yield  # 十年期国债收益，中国/美国

    def cal_good_price(self, price: float, ttm_pe: float, good_price_pe: float, ttm_dividend: float):
        """
        计算好价格
        市盈率法和股息法，哪个价格小选哪个
        """
        if good_price_pe is None or good_price_pe <= 0:
            good_price_pe = self._default_good_pe

        pe_good_price = self._pe_good_price(price, ttm_pe, good_price_pe)
        dividend_good_price = self._dividend_good_price(ttm_dividend)

        good_price = pe_good_price
        if good_price > dividend_good_price > 0:
            good_price = dividend_good_price
        return good_price

    def _pe_good_price(self, price: float, ttm_pe: float, good_price_pe: float):
        """好价格：市盈率法
        price: 股价
        ttmPE：TTM市盈率
        goodPricePE：好价格对应的市盈率
        """
        if good_price_pe is None or good_price_pe <= 0:
            good_price_pe = self._default_good_pe

        if price <= 0 or good_price_pe <= 0:
            return float(0)

        return (price / ttm_pe) * good_price_pe

    def _dividend_good_price(self, ttm_dividend: float):
        """
        好价格：股息法
        ttmDividend: TTM股息
        bondsYield：十年期国债收益率
        """
        return ttm_dividend / self._ten_year_bonds_yield

    def single_good_price(self, good_pe: float, indicator: dict) -> dict:
        current_price = indicator['current']
        result = {
            "code": indicator['code'],
            "name": indicator['name'],
            "current_price": current_price,
            "ttm_pe": indicator['ttm_pe'],
        }
        good_pe_items = []
        result["ttm_dividend"] = dividend = round(
            float(current_price) * (float(indicator['ttm_dividend_ratio']) / 100), 3)
        good_price = self.cal_good_price(price=current_price, ttm_pe=indicator['ttm_pe'],
                                         good_price_pe=good_pe,
                                         ttm_dividend=dividend)
        if good_price <= 0 or current_price > good_price:
            return {}
        good_pe_items.append({"good_pe": 15, "good_price": round(good_price, 2),
                              "premium_ratio": round(((good_price - current_price) / good_price) * 100, 2)})
        result["good_pe_items"] = good_pe_items
        return result
