from .base_gateway import *
from .backtest import BacktestFees, BacktestGateway

try:
    from .futu import FutuGateway, FutuQuoteGateway, FutuFuturesGateway
except ImportError as e:
    print(f"Warning: {e.__class__}: {e.msg}")

try:
    from .ib import IbGateway
except ImportError as e:
    print(f"Warning: {e.__class__}: {e.msg}")

try:
    from .cqg import CqgGateway
except ImportError as e:
    print(f"Warning: {e.__class__}: {e.msg}")
