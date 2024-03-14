import logging
from abc import ABCMeta, abstractmethod
from typing import TypeVar
from enum import IntEnum
from telegram import Update, Bot

from exastris_bot.base.logging_adapter import prefixMaker

T = TypeVar('T')


class HandlerType(IntEnum):
    PRIVATE_COMMAND = 1
    COMMAND = 2
    CALLBACK = 3
    MEMBER_CHANGE = 4
    CUSTOM = 5


class BaseHandler(metaclass=ABCMeta):
    config_object: T | None = None
    config_name: str | None = None
    logger: logging.LoggerAdapter = None
    block: bool = True
    handler: HandlerType = HandlerType.CUSTOM

    def __init_subclass__(cls, **kwargs):
        if cls.config_object is not None and cls.config_name is None:
            raise ValueError('You must override the config_name in order to load your config object')
        if cls.config_object is None and cls.config_name is not None:
            cls.config_object = None
            raise Warning("Overriding config_name alone take no effect")
        cls.logger = prefixMaker(f" {cls.__name__} ", logging.getLogger(cls.__name__))

    @classmethod
    @abstractmethod
    async def run(cls, update: Update, bot: Bot):
        pass

    @classmethod
    @abstractmethod
    def recognise(cls,update:Update)->bool:
        pass


if __name__ == '__main__':
    class test(BaseHandler):
        config_object = True
        config_name = 'YHHH'

        @classmethod
        def run(cls, update: Update, bot: Bot):
            cls.logger.error(f"Config Name: {cls.config_name}")


    test.run(None, None)
