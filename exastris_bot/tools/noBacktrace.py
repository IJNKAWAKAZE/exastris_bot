import datetime

from telegram import Update
from telegram.ext import CallbackContext


def no_backtrace(func):
    now = datetime.datetime.now().timestamp()

    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_message is not None and now > update.effective_message.date.timestamp():
            return lambda: None  # this just doing nothing
        return await func(update, context, *args, **kwargs)

    return wrapper
