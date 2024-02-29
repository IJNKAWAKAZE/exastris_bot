import datetime
import logging

from telegram.ext import ApplicationBuilder, Application,MessageHandler
from typing import NoReturn
from logging import info,warn,error,fatal
from exastris_bot.handlers import init_handlers,Handlers,job_queue
class ExBot():
    BOT_START_TIME: datetime.datetime

    def __init__(self, config: dict):
        bot_token = config['bot_token']
        self.application: Application = (ApplicationBuilder()
                                         .token(bot_token)
                                         .arbitrary_callback_data(True)
                                         .job_queue(job_queue)
                                         .build()
                                         )
        for init_functions in init_handlers:
            init_functions(config)
        self.application.add_handlers(Handlers)


    def run(self) -> NoReturn:
        self.BOT_START_TIME = datetime.datetime.now()
        logging.info("Bot started At: %s", self.BOT_START_TIME)

        self.application.run_polling()
