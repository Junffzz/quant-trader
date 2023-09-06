from dataclasses import dataclass
from typing import List, Any

from dataclasses_json import dataclass_json
from app.domain.security import Stock, Security


@dataclass_json
@dataclass
class SubscribeQuote:
    """Quote"""
    strategy_name: str
    securities: List[Security]
