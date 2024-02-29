import logging

from telegram import Update
from telegram.ext import CallbackContext


def log_on_trigger(level):
    def decorator(func):
        logging.fatal(f"register to log on trigger {func.__name__}")

        async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
            logging.log(level,
                        f"Handle {func.__name__} is triggered")
            return await func(update, context, *args, **kwargs)

        return wrapper

    return decorator
