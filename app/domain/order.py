from datetime import datetime
from dataclasses import dataclass

from app.domain.security import Stock
from app.constants import Exchange, OrderType, OrderTimeInForce, OrderStatus, Direction, Offset


@dataclass
class OrderBook:
    """Orderbook"""
    security: Stock
    exchange: Exchange
    datetime: datetime

    bid_price_1: float = 0
    bid_price_2: float = 0
    bid_price_3: float = 0
    bid_price_4: float = 0
    bid_price_5: float = 0
    bid_price_6: float = 0
    bid_price_7: float = 0
    bid_price_8: float = 0
    bid_price_9: float = 0
    bid_price_10: float = 0

    ask_price_1: float = 0
    ask_price_2: float = 0
    ask_price_3: float = 0
    ask_price_4: float = 0
    ask_price_5: float = 0
    ask_price_6: float = 0
    ask_price_7: float = 0
    ask_price_8: float = 0
    ask_price_9: float = 0
    ask_price_10: float = 0

    bid_volume_1: float = 0
    bid_volume_2: float = 0
    bid_volume_3: float = 0
    bid_volume_4: float = 0
    bid_volume_5: float = 0
    bid_volume_6: float = 0
    bid_volume_7: float = 0
    bid_volume_8: float = 0
    bid_volume_9: float = 0
    bid_volume_10: float = 0

    ask_volume_1: float = 0
    ask_volume_2: float = 0
    ask_volume_3: float = 0
    ask_volume_4: float = 0
    ask_volume_5: float = 0
    ask_volume_6: float = 0
    ask_volume_7: float = 0
    ask_volume_8: float = 0
    ask_volume_9: float = 0
    ask_volume_10: float = 0

    bid_num_1: float = 0
    bid_num_2: float = 0
    bid_num_3: float = 0
    bid_num_4: float = 0
    bid_num_5: float = 0
    bid_num_6: float = 0
    bid_num_7: float = 0
    bid_num_8: float = 0
    bid_num_9: float = 0
    bid_num_10: float = 0

    ask_num_1: float = 0
    ask_num_2: float = 0
    ask_num_3: float = 0
    ask_num_4: float = 0
    ask_num_5: float = 0
    ask_num_6: float = 0
    ask_num_7: float = 0
    ask_num_8: float = 0
    ask_num_9: float = 0
    ask_num_10: float = 0


@dataclass
class Order:
    """Order"""
    security: Stock
    price: float
    quantity: float
    direction: Direction
    offset: Offset
    order_type: OrderType
    create_time: datetime
    updated_time: datetime = None
    stop_price: float = None
    filled_avg_price: float = 0
    filled_quantity: int = 0
    time_in_force: OrderTimeInForce = None
    status: OrderStatus = OrderStatus.UNKNOWN
    orderid: str = ""
    remark: str = ""


class OrderService:
    def __init__(self, engine=None):
        self.engine = engine

    def create_order(self, order: Order = None, account_id=0, strategy_name=""):
        plugins = self.engine.get_plugins()
        DB = getattr(plugins["mariadb"], "DB")
        db = DB()

        updated_time = order.updated_time
        if updated_time is None:
            updated_time = datetime.now()
        db.insert_records(
            table_name="orders",
            broker_order_id=order.orderid,
            account_id=account_id,
            strategy_name=strategy_name,
            security_name=order.security.security_name,
            security_code=order.security.code,
            direction=order.direction.name,
            offset_type=order.offset.name,
            order_type=order.order_type.name,
            price=order.price,
            quantity=order.quantity,
            update_time=updated_time,
            filled_avg_price=order.filled_avg_price,
            filled_quantity=order.filled_quantity,
            status=order.status.name,
            remark="",
        )

    def update_deal(self):
        pass


if __name__ == '__main__':
    import sys

    from app import application
    from app.plugins.mariadb import DB


    def test_order():
        db = DB()
        stock = Stock(code="HK.02420", lot_size=500, security_name="子不语", exchange=Exchange.SEHK)
        order = Order(
            security=stock,
            price=23.01,
            quantity=100,
            direction=Direction.LONG,
            offset=Offset.OPEN,
            order_type=OrderType.MARKET,
            orderid="",
            create_time=datetime.now(),
            updated_time=datetime.now(),
        )
        account_id = 12
        strategy_name = "us_strategy1.0"

        updated_time = order.updated_time
        if updated_time is None:
            updated_time = datetime.now()
        db.insert_records(
            table_name="orders",
            broker_order_id=order.orderid,
            account_id=account_id,
            strategy_name=strategy_name,
            security_name=order.security.security_name,
            security_code=order.security.code,
            direction=order.direction.name,
            offset_type=order.offset.name,
            order_type=order.order_type.name,
            price=order.price,
            quantity=order.quantity,
            update_time=updated_time,
            remark="",
        )


    config_file = sys.argv[1]
    application.start(config_file, test_order)
