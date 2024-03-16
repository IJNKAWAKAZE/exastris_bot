import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update, Message
from typing import TypeVar
from enum import IntFlag

from telegram.constants import ChatMemberStatus
from telegram.ext import CallbackContext

T = TypeVar('T')


class ClickControl(IntFlag):
    MAKER = 1
    ADMIN = 2
    OTHER = 4


__callback_map: dict[str, int] = {}
__available_callback_map: dict[str, int|None] = {}

'''
This can only be used in non-blocking handler, do not use it in blocking handler it will block the bot
'''


async def select_value_by_inline_keyboard(bot: Bot,
                                          update: Update,
                                          text: str,
                                          selection: list[list[tuple[str, T, ClickControl]]],
                                          parse_mode: str | None = None,
                                          timeout: int | None = None,
                                          replay_to_message: bool = True,
                                          delete_message_when_finish: bool = True) -> T | None:
    # get some infomation
    chat_id: int = update.effective_chat.id
    message_id: int = update.effective_message.message_id
    user_id: int = update.effective_message.from_user.id
    callback_id = f"{chat_id}{message_id}"
    counter = 0
    callback_data = []
    # build callback map
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    for i in range(len(selection)):
        inline_keyboard.append([])
        for j in range(len(selection[i])):
            callback_txt, data, control = selection[i][j]
            callback_data.append(data)
            inline_keyboard[-1].append(
                InlineKeyboardButton(text=callback_txt,
                                     callback_data=f"{UNIVERSAL_CALLBACK_PREFIX},{callback_id},{counter},{control}"))
            counter += 1
    replay_to_message_id = message_id if replay_to_message else None
    __callback_map[callback_id] = user_id
    # send the msg
    msg: Message = await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode,
                                          reply_markup=InlineKeyboardMarkup(inline_keyboard),
                                          reply_to_message_id=replay_to_message_id)
    __available_callback_map[callback_id] = None
    # waiting for the callback
    while (timeout is None or timeout >= 0) and not __available_callback_map[callback_id]:
        await asyncio.sleep(1)
        if timeout is not None:
            timeout -= 1
    result: T | None = None
    # timeout or callback got
    if __available_callback_map[callback_id] is not None:
        result = callback_data[__available_callback_map[callback_id]]
    else:
        del __available_callback_map[callback_id]
    del __callback_map[callback_id]
    if delete_message_when_finish:
        await msg.delete()
    return result


UNIVERSAL_CALLBACK_PREFIX = "UCP"


async def universal_callback_handler(update: Update, context: CallbackContext):
    bot = context.bot
    _, callback_id, user_select_str, access_control_str = update.callback_query.data.split(",")
    if callback_id in __callback_map:
        user_id = __callback_map[callback_id]
        state = 0
        if update.effective_user.id == user_id:
            state = state | ClickControl.MAKER
        k = await bot.get_chat_member(chat_id=update.effective_chat.id,
                                        user_id=update.effective_user.id)
        if k.status == ChatMemberStatus.ADMINISTRATOR or ChatMemberStatus.OWNER:
            state = state | ClickControl.ADMIN
        else:
            state = state | ClickControl.OTHER
        if _check_permission(int(access_control_str), state):
            __available_callback_map[callback_id] = int(user_select_str)
        else:
            await bot.send_message(chat_id=update.effective_chat.id, text="您无权点击这个按钮")
    else:
        logging.warning("[ Callback ] Callback id {} not exist".format(callback_id))


def _check_permission(access_control: int, user_state: ClickControl) -> bool:
    return (user_state & access_control) != 0
