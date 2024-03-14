import datetime
import logging

from telegram.ext import Updater
from typing import NoReturn
from logging import info,warn,error,fatal
class ExBot():
    BOT_START_TIME: datetime.datetime

    def __init__(self, config: dict):
        bot_token = config['bot_token']


    def run(self) -> NoReturn:
        self.BOT_START_TIME = datetime.datetime.now()
        logging.info("Bot started At: %s", self.BOT_START_TIME)

        self.application.run_polling()
