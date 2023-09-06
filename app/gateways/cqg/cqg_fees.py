# -*- coding: utf-8 -*-

from app.domain.deal import Deal
from app.gateways.base_gateway import BaseFees


class CQGFees(BaseFees):
    """
    CQG fee model
    """

    def __init__(self, *deals: Deal):
        # Platform fees (to the platform)
        commissions = 0
        platform_fees = 0
        # Agency fees (to other parties such as exchange, tax authorities)
        system_fees = 0
        settlement_fees = 0
        stamp_fees = 0
        trade_fees = 0
        transaction_fees = 0

        for deal in deals:
            # price = deal.filled_avg_price
            quantity = deal.filled_quantity
            commissions += 1.92 * quantity  # 1.92 per contract

        # Total fees
        total_fees = (
            commissions
            + platform_fees
            + system_fees
            + settlement_fees
            + stamp_fees
            + trade_fees
            + transaction_fees
        )

        self.commissions = commissions
        self.platform_fees = platform_fees
        self.system_fees = system_fees
        self.settlement_fees = settlement_fees
        self.stamp_fees = stamp_fees
        self.trade_fees = trade_fees
        self.transaction_fees = transaction_fees
        self.total_fees = total_fees
