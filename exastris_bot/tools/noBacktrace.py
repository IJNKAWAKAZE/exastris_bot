import datetime

from telegram import Update, Message
from telegram.ext import CallbackContext



def no_backtrace(func):
    now = datetime.datetime.now()
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):

        if update.message is not None and now > update.message.date:
            return lambda: None  # this just doing nothing
        return await func(update, context, *args, **kwargs)

    return wrapper
