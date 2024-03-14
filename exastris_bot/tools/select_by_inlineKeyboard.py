import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update, Message
from typing import TypeVar
from enum import IntFlag

from telegram.constants import ChatMemberStatus

T = TypeVar('T')


class ClickControl(IntFlag):
    MAKER = 1
    ADMIN = 2
    OTHER = 4


callback_map: dict[str, int] = {}
available_callback_map: dict[str, int] = {}

'''
This can only be used in non-blocking handler, do not use it in blocked handler
'''


async def select_value_by_inline_keyboard(bot: Bot,
                                          update: Update,
                                          text: str,
                                          parse_mode,
                                          selection: list[list[tuple[str, T, ClickControl]]],
                                          timeout: int | None = None,
                                          replay_to_message: bool = True,
                                          delete_message_when_finish: bool = True) -> T:
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
            text, data, control = selection[i][j]
            callback_data.append(data)
            inline_keyboard[-1].append(
                InlineKeyboardButton(text=selection[i][j][0],
                                     callback_data=f"SV,{callback_id},{counter + 1},{control}"))
            counter += 1
    replay_to_message_id = message_id if replay_to_message else None
    callback_map[callback_id] = user_id
    # send the msg
    msg: Message = await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode,
                                          reply_markup=InlineKeyboardMarkup(inline_keyboard),
                                          reply_to_message_id=replay_to_message_id)
    available_callback_map[callback_id] = 0
    # waiting for the callback
    while (timeout is None or timeout >= 0) and not available_callback_map[callback_id]:
        await asyncio.sleep(1)
        if timeout is not None:
            timeout -= 1
    result: T | None = None
    # timeout or callback got
    if available_callback_map[callback_id]:
        result = callback_data[counter - 1]
    else:
        del available_callback_map[callback_id]
    del callback_map[callback_id]
    if delete_message_when_finish:
        await msg.delete()
    return result


async def universal_callback_handler(update: Update, bot: Bot):
    _, callback_id, user_select_str, access_control_str = update.callback_query.data.split(",")
    if callback_id in callback_map:
        user_id = callback_map[callback_id]
        if update.effective_user.id == user_id:
            state = ClickControl.MAKER
        elif (await bot.get_chat_member(chat_id=update.effective_chat.id,
                                        user_id=update.effective_user.id)).status == ChatMemberStatus.ADMINISTRATOR:
            state = ClickControl.ADMIN
        else:
            state = ClickControl.OTHER
        if _check_permission(int(access_control_str), state):
            available_callback_map[callback_id] = int(user_select_str)
        else:
            await bot.send_message(chat_id=update.effective_chat.id, text="您无权点击这个按钮")
    else:
        logging.warning("[ Callback ] Callback id {} not exist".format(callback_id))


def _check_permission(access_control: int, user_state: ClickControl) -> bool:
    return (user_state & access_control) != 0
