from telegram import Update, Bot
from abc import ABCMeta,abstractmethod
from exastris_bot.base import base_handler


class CommandHandler(base_handler.BaseHandler, metaclass=ABCMeta):
    @classmethod
    async def run(cls, update: Update, bot: Bot):
        args = update.message.text.split(' ')
        if len(args) == 1:
            args = None

    @classmethod
    @abstractmethod
    async def real_run(cls, update: Update, bot: Bot , command_argument :list[str] | None ):
        pass


    @classmethod
    def recognise(cls, update: Update) -> bool:
        pass

