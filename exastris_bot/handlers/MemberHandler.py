import asyncio

import logging
import random
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import ChatMember, User, Chat
from telegram.constants import ParseMode
from telegram import ChatPermissions
from telegram.ext import CallbackContext, ChatMemberHandler, CallbackQueryHandler

from exastris_bot.tools import log_on_trigger, no_backtrace, select_value_by_inline_keyboard, \
    universal_callback_handler, ClickControl, UNIVERSAL_CALLBACK_PREFIX

MEMBER_JOIN_PREFIX = "MJ"
ADMIN_PASS = -1
ADMIN_KILL = -2
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
@log_on_trigger(logging.INFO)
async def MemberUpdateCallback(update: Update, context: CallbackContext) -> None:
    massage = update.message
    if massage is None:
        return
    if massage.new_chat_members:
        for member in massage.new_chat_members:
            await new_member_handler(update, context, member, bool(update.chat_member.invite_link))
        return
    elif massage.left_chat_member:
        return await left_chat_member_handler(update, context)


@log_on_trigger(logging.DEBUG)
async def welcome_handler(chat_id: int, context: CallbackContext, member: User) -> None:
    welcome_message = MemberHandlerConfig.WelcomeMessage_CN
    if member.language_code is not None and "zh" in member.language_code:
        pass
    else:
        welcome_message = MemberHandlerConfig.WelcomeMessage_ALL
    await context.bot.send_message(chat_id=chat_id,
                                   text=welcome_message.format(username=member.username),
                                   parse_mode=ParseMode.MARKDOWN_V2)


@log_on_trigger(logging.DEBUG)
async def new_member_handler(update: Update, context: CallbackContext, member: User, is_invited: bool) -> None:
    logging.info(f"New member triggered: {member.username}")
    if member.is_bot:
        return
    if is_invited:
        await welcome_handler(update.message.chat_id, context, member)
    else:
        await update.message.chat.restrict_member(
            member.id,
            ChatPermissions.no_permissions())
        question, answer = MemberHandlerConfig.random_select_button()
        keyboard = [[]]
        for i, x in enumerate(question):
            keyboard[-1].append((x, i, ClickControl.MAKER))
            if len(keyboard[-1]) >= MemberHandlerConfig.AuthButtonsPerRow:
                keyboard.append([])
        keyboard.append([
            ("ADMIN KILL", -1, ClickControl.ADMIN),
            ("ADMIN PASS", -2, ClickControl.ADMIN)
        ])
        msg = (MemberHandlerConfig.AuthMessage_CN
               if member.language_code is not None and "zh" not in member.language_code else
               MemberHandlerConfig.AuthMessage_ALL).format(username=member.username, correct_button=question[answer])
        result = await select_value_by_inline_keyboard(context.bot, update, msg, selection=keyboard,
                                                       replay_to_message=False,
                                                       timeout=MemberHandlerConfig.AuthAuthTimeOut)
        print(f"{result is None or result != answer or result != -2}")

        if result is not None and (result==answer or result==-2):
            await welcome_handler(update.message.chat_id, context, member)
        else:
            await context.bot.banChatMember(chat_id=update.message.chat_id, user_id=member.id,
                                                until_date=MemberHandlerConfig.AuthFailTimeOut)


@log_on_trigger(logging.DEBUG)
async def left_chat_member_handler(update: Update, context: CallbackContext):
    pass


MemberHandler = ChatMemberHandler(MemberUpdateCallback, block=False)
MemberJoinCallBack = CallbackQueryHandler(universal_callback_handler, pattern="^" + MEMBER_JOIN_PREFIX, block=False)
