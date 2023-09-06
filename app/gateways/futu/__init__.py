# -*- coding: utf-8 -*-


try:
    from .futu_gateway import FutuGateway
except ImportError as e:
    print(f"{e.__class__}: {e.msg}")

try:
    from .futu_quote_gateway import FutuQuoteGateway
except ImportError as e:
    print(f"{e.__class__}: {e.msg}")

try:
    from .futu_futures_gateway import FutuFuturesGateway
except ImportError as e:
    print(f"{e.__class__}: {e.msg}")

try:
    from .futu_fees import FutuFeesSEHK, FutuFeesHKFE
except ImportError as e:
    print(f"{e.__class__}: {e.msg}")