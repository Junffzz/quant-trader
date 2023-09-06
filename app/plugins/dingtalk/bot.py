# -*- coding: utf-8 -*-
from datetime import datetime

from dingtalkchatbot.chatbot import DingtalkChatbot, ActionCard, CardItem

from trader_config import DINGTALK_TOKEN
from trader_config import DINGTALK_SECRET


class DingtalkBot:
    """
    <QuantTrader DingtalkBot> Available commands:"
    1. /stop
    2. /balance
    3. /positions
    4. /orders
    5. /deals
    6. /cancel_order
    7. /cancel_orders
    8. /send_order
    9. /close_positions
    10. /help
    """

    def __init__(self, token: str):
        # Handle responses (make updater.bot subclass, so that we can add
        # attributes to it)
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=' + DINGTALK_TOKEN
        secret = None
        if DINGTALK_SECRET != "" and DINGTALK_SECRET is not None:
            secret = DINGTALK_SECRET
        self.chatbot = DingtalkChatbot(webhook, secret=secret)

    def send_text(self, msg: str, at_mobiles=[]):
        self.chatbot.send_text(msg, at_mobiles=at_mobiles)

    def send_markdown(self, title: str = "", text: str = ''):
        self.chatbot.send_markdown(title, text)


bot = DingtalkBot(token=DINGTALK_TOKEN)

if __name__ == "__main__":
    if "bot" not in locals():
        bot = DingtalkBot(token=DINGTALK_TOKEN)

    bot.send_text(msg="Yes I am here!")
    print("Closed.")
