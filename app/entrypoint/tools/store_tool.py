from app.domain.stores import StockMarket


def save_to_csv():
    stock_service = StockMarket()
    stock_codelist = stock_service.get_codelist()


if __name__ == '__main__':
    save_to_csv()
