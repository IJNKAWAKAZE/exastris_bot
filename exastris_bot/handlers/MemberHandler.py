import asyncio
import dataclasses
import datetime
import logging
import random
from typing import Optional, Union, Tuple, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import ChatMember, User, Chat
from telegram.constants import ParseMode
from telegram import ChatPermissions
from telegram.ext import CallbackContext, ChatMemberHandler, CallbackQueryHandler
from exastris_bot.handlers.tools import no_backtrace, log_on_trigger
from random import randint

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


class WaitingCallback:
    __waiting_list: dict = {}

    def __init__(self, chat: Chat, user: User, correct_id: Optional[int], msg):
        self.chat: Chat = chat
        self.user: User = user
        self.correct_index: int = correct_id
        self.default_permission: ChatPermissions = chat.permissions
        self.msg = msg

    @staticmethod
    def random_with_N_digits(n):
        range_start = 10 ** (n - 1)
        range_end = (10 ** n) - 1
        return randint(range_start, range_end)

    @staticmethod
    def add_to_waiting_callback(chat: Chat, user: User, msg) -> Tuple[int, Any]:
        waiting_member = WaitingCallback(chat, user, None, msg)
        uuid = WaitingCallback.random_with_N_digits(6)
        while uuid in WaitingCallback.__waiting_list:
            uuid = WaitingCallback.random_with_N_digits(6)
        WaitingCallback.__waiting_list[uuid] = waiting_member
        return uuid, waiting_member

    @staticmethod
    def pop_waiting_callback(uuid: int):
        result = WaitingCallback.peek_waiting_callback(uuid)
        if result is not None:
            del WaitingCallback.__waiting_list[uuid]
        return result

    @staticmethod
    def peek_waiting_callback(uuid: int):
        if uuid in WaitingCallback.__waiting_list:
            return WaitingCallback.__waiting_list[uuid]
        return None


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
        chat = await context.bot.get_chat(chat_id=update.message.chat_id)
        await update.message.chat.restrict_member(
            member.id,
            ChatPermissions.no_permissions())
        question, answer = MemberHandlerConfig.random_select_button()
        wait_member: Optional[WaitingCallback] = None
        uuid, wait_member = WaitingCallback.add_to_waiting_callback(chat, member, None)
        keyboard = [[]]
        for i, x in enumerate(question):
            keyboard[-1].append(InlineKeyboardButton(x, callback_data=f'{MEMBER_JOIN_PREFIX},{uuid},{i}'))
            if len(keyboard[-1]) >= MemberHandlerConfig.AuthButtonsPerRow:
                keyboard.append([])
        keyboard.append([
            InlineKeyboardButton("ADMIN KILL", callback_data=f'{MEMBER_JOIN_PREFIX},{uuid},{-1}'),
            InlineKeyboardButton("ADMIN PASS", callback_data=f'{MEMBER_JOIN_PREFIX},{uuid},{-2}')
        ])
        wait_member.correct_index = answer
        msg = (MemberHandlerConfig.AuthMessage_CN
               if member.language_code is not None and "zh" not in member.language_code else
               MemberHandlerConfig.AuthMessage_ALL).format(username=member.username, correct_button=question[answer])
        auth_msg = await context.bot.send_message(chat_id=update.message.chat_id, text=msg,
                                                  reply_markup=InlineKeyboardMarkup(keyboard))
        wait_member.msg = auth_msg.message_id
        await asyncio.sleep(MemberHandlerConfig.AuthAuthTimeOut)
        user_ban = WaitingCallback.pop_waiting_callback(uuid)
        if user_ban is not None:
            await context.bot.banChatMember(chat_id=update.message.chat_id, user_id=user_ban.user_id,
                                            until_date=MemberHandlerConfig.AuthFailTimeOut)
            await context.bot.delete_message(chat_id=update.message.chat_id, message_id=auth_msg.message_id)


@log_on_trigger(logging.DEBUG)
async def left_chat_member_handler(update: Update, context: CallbackContext):
    pass


@log_on_trigger(logging.DEBUG)
async def callback_handler(update: Update, context: CallbackContext):
    async def allow(chat: Chat, user: User, default_perm: ChatPermissions) -> None:
        user_id = user.id
        if DEBUG:
            logging.error(f"allow user: {user_id} in chat: {chat.id}")
        else:
            await chat.restrict_member(user_id, default_perm)
        await context.bot.deleteMessage(callback.chat.id, callback.msg)

    async def fail(chat: Chat, user: User) -> None:
        user_id = user.id
        if DEBUG:
            logging.error(f"baned user: {user_id} in chat: {chat.id}")
        else:
            await chat.ban_member(user_id, until_date=int(
                datetime.datetime.now().timestamp()) + MemberHandlerConfig.AuthFailTimeOut)
        await context.bot.deleteMessage(callback.chat.id, callback.msg)

    query = update.callback_query.data.split(",")
    try:
        uuid = int(query[1])
        select = int(query[2])
        callback: WaitingCallback = WaitingCallback.peek_waiting_callback(uuid)
        if select < 0:  # Admin Kill or Admin Pass
            k = await context.bot.get_chat_member(chat_id=update.message.chat_id, user_id=update.effective_user.id)
            if k.status != ChatMember.ADMINISTRATOR:
                await context.bot.send_message(chat_id=update.message.chat_id, text="Admin only")
            elif select == ADMIN_PASS:
                await allow(callback.chat, callback.user, callback.default_permission)
            elif select == ADMIN_KILL:
                await fail(callback.chat, callback.user)
        if callback.user.id != update.effective_user.id:
            msg = await context.bot.send_message(chat_id=update.message.chat_id, text="Not Your Button")

        if select != callback.correct_index:
            await fail(callback.chat, callback.user)
        else:
            await allow(callback.chat, callback.user, callback.default_permission)
            await welcome_handler(callback.chat.id, context, callback.user)
    except ValueError:
        logging.warning(f"invalid call massage {query} for callback_handler")


MemberHandler = ChatMemberHandler(MemberUpdateCallback, block=False)
MemberJoinCallBack = CallbackQueryHandler(callback_handler, pattern="^" + MEMBER_JOIN_PREFIX, block=False)
