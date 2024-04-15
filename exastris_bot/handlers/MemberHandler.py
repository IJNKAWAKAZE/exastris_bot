import logging
import random
from typing import Optional

from telegram import ChatPermissions
from telegram import Update
from telegram import User
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, filters

from exastris_bot.tools import log_on_trigger, select_value_by_inline_keyboard, universal_callback_handler, \
    no_backtrace

DEBUG = False


class MemberHandlerConfig:
    WelcomeMessage_CN: str
    WelcomeMessage_ALL: str
    WelcomeMessage_MarkDown: bool
    AuthMessage_CN: str
    AuthMessage_ALL: str
    AuthButtons: list[str]
    AuthFailTimeOut: int
    AuthNumberOfButton: int
    AuthAuthTimeOut: int
    AuthButtonsPerRow: int

    @staticmethod
    def init_config(config: dict) -> None:
        logging.error("Config initing")
        if config is None or "MemberHandler" not in config:
            raise ValueError("Config must contain 'MemberHandler'")
        global DEBUG
        DEBUG = config["debug"]
        config = config["MemberHandler"]
        MemberHandlerConfig.WelcomeMessage_CN = config["Welcome"]["text_CN"]
        MemberHandlerConfig.WelcomeMessage_ALL = config["Welcome"]["text_ALL"]
        MemberHandlerConfig.WelcomeMessage_Markdown = config["Welcome"]["is_markdown"]
        MemberHandlerConfig.AuthMessage_CN = config["Auth"]["text_CN"]
        MemberHandlerConfig.AuthMessage_ALL = config["Auth"]["text_ALL"]
        MemberHandlerConfig.AuthButtons = config["Auth"]["all_buttons"]
        MemberHandlerConfig.AuthNumberOfButton = config["Auth"]["number_of_button"]
        MemberHandlerConfig.AuthFailTimeOut = config["Auth"]["fail_timeout"]
        MemberHandlerConfig.AuthAuthTimeOut = config["Auth"]["auth_timeout"]
        MemberHandlerConfig.AuthButtonsPerRow = config["Auth"]["number_of_button_per_row"]

    @staticmethod
    def random_select_button() -> Optional[tuple[list[str], int]]:
        if MemberHandlerConfig.AuthButtons is None or len(
                MemberHandlerConfig.AuthButtons) < MemberHandlerConfig.AuthNumberOfButton:
            logging.error("random_select_button has called before init_config or wrong config file have provided")
            return None
        questions: list[str] = random.sample(MemberHandlerConfig.AuthButtons, MemberHandlerConfig.AuthNumberOfButton)
        answers: int = random.randint(0, len(questions) - 1)
        return questions, answers


@no_backtrace
@log_on_trigger(logging.DEBUG)
async def new_member_handler(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    for member in message.new_chat_members:
        logging.info(f"New member triggered: {member.full_name}")
        if member.is_bot:
            return
        else:
            await context.bot.restrict_chat_member(message.chat_id, member.id,
                                                   ChatPermissions.no_permissions())
            question, answer = MemberHandlerConfig.random_select_button()
            keyboard = [[]]
            for i, x in enumerate(question):
                keyboard[-1].append((x, i))
                if len(keyboard[-1]) >= MemberHandlerConfig.AuthButtonsPerRow:
                    keyboard.append([])
            keyboard.append([
                ("ADMIN KILL", -1),
                ("ADMIN PASS", -2)
            ])
            msg = (MemberHandlerConfig.AuthMessage_CN
                   if member.language_code is not None and "zh" not in member.language_code else
                   MemberHandlerConfig.AuthMessage_ALL).format(username=member.full_name,
                                                               correct_button=question[answer])
            await select_value_by_inline_keyboard(context.bot, update, msg, selection=keyboard,
                                                  answer=question[answer],
                                                  timeout=MemberHandlerConfig.AuthAuthTimeOut,
                                                  fail_timeout=MemberHandlerConfig.AuthFailTimeOut)


@no_backtrace
@log_on_trigger(logging.DEBUG)
async def left_chat_member_handler(update: Update, context: CallbackContext):
    message = update.effective_message
    await message.delete()


async def welcome_handler(chat_id: int, context: CallbackContext, member: User) -> None:
    welcome_message = MemberHandlerConfig.WelcomeMessage_CN
    if member.language_code is not None and "zh" in member.language_code:
        pass
    else:
        welcome_message = MemberHandlerConfig.WelcomeMessage_ALL
    await context.bot.send_message(chat_id=chat_id,
                                   text=welcome_message.format(username=member.full_name),
                                   parse_mode=ParseMode.MARKDOWN_V2)


NewMemberHandler = MessageHandler(filters=filters.StatusUpdate.NEW_CHAT_MEMBERS, callback=new_member_handler)
LeftMemberHandler = MessageHandler(filters=filters.StatusUpdate.LEFT_CHAT_MEMBER, callback=left_chat_member_handler)
MemberJoinCallBack = CallbackQueryHandler(universal_callback_handler, pattern=r"^MJ", block=False)
