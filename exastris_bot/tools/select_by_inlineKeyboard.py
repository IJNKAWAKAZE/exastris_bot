import asyncio
import logging
from typing import TypeVar

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update, ChatPermissions, Message
from telegram.constants import ChatMemberStatus
from telegram.ext import CallbackContext

T = TypeVar('T')

__callback_map: dict[str, int] = {}

'''
This can only be used in non-blocking handler, do not use it in blocking handler it will block the bot
'''


async def select_value_by_inline_keyboard(bot: Bot,
                                          update: Update,
                                          text: str,
                                          answer: str,
                                          selection: list[list[tuple[str, T]]],
                                          timeout: int | None = None,
                                          fail_timeout: int | None = None) -> T | None:
    # get some infomation
    message = update.effective_message
    chat_id: int = message.chat_id
    user_id: int = message.from_user.id
    callback_id = f"{chat_id}{user_id}"
    # build callback map
    inline_keyboard: list[list[InlineKeyboardButton]] = []
    for i in range(len(selection)):
        inline_keyboard.append([])
        for j in range(len(selection[i])):
            callback_txt, data = selection[i][j]
            inline_keyboard[-1].append(
                InlineKeyboardButton(text=callback_txt,
                                     callback_data=f"MJ,{callback_id},{callback_txt},{answer},{data}, {fail_timeout}"))
    __callback_map[callback_id] = user_id
    # send the msg
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard))
    asyncio.get_event_loop().create_task(verify_timeout(bot, callback_id, chat_id, user_id, timeout, fail_timeout, msg))
    return None


async def verify_timeout(bot: Bot, key: str, chat_id: int, user_id: int, timeout: int, fail_timeout: int, msg: Message):
    await asyncio.sleep(timeout)
    if key in __callback_map.keys():
        await bot.banChatMember(chat_id=chat_id, user_id=user_id)
        await msg.delete()
        __callback_map.pop(key)
        await asyncio.sleep(fail_timeout)
        await bot.unbanChatMember(chat_id=chat_id, user_id=user_id)


async def universal_callback_handler(update: Update, context: CallbackContext):
    bot = context.bot
    chat_id = update.effective_chat.id
    click_user_id = update.effective_user.id
    callback_query_id = update.callback_query.id
    _, callback_id, user_select_str, answer, access_control_str, fail_timeout = update.callback_query.data.split(",")
    if callback_id in __callback_map:
        user_id = __callback_map[callback_id]
        if (int(access_control_str) == -1) or (int(access_control_str) == -2):
            k = await bot.get_chat_member(chat_id=chat_id,
                                          user_id=click_user_id)
            if (k.status == ChatMemberStatus.ADMINISTRATOR) or (k.status == ChatMemberStatus.OWNER):
                if int(access_control_str) == -1:
                    await bot.banChatMember(chat_id=chat_id, user_id=user_id)
                    __callback_map.pop(callback_id)
                    await update.callback_query.delete_message()
                elif int(access_control_str) == -2:
                    await pass_verify(bot, chat_id, user_id, update)
            else:
                await bot.answerCallbackQuery(callback_query_id=callback_query_id, text="您无权点击这个按钮",
                                              show_alert=True)
            return

        if click_user_id != user_id:
            await bot.answerCallbackQuery(callback_query_id=callback_query_id, text="这不是你的验证", show_alert=True)
            return
        if user_select_str != answer:
            await bot.answerCallbackQuery(callback_query_id=callback_query_id, text="验证失败请稍后再试",
                                          show_alert=True)
            await update.callback_query.delete_message()
            asyncio.get_event_loop().create_task(fail_verify(bot, chat_id, user_id, int(fail_timeout)))
        else:
            await bot.answerCallbackQuery(callback_query_id=callback_query_id, text="验证通过",
                                          show_alert=True)
            await pass_verify(bot, chat_id, user_id, update)
        __callback_map.pop(callback_id)

    else:
        logging.warning("[ Callback ] Callback id {} not exist".format(callback_id))


async def fail_verify(bot: Bot, chat_id: int, user_id: int, fail_timeout: int):
    await bot.banChatMember(chat_id=chat_id, user_id=user_id)
    await asyncio.sleep(fail_timeout)
    await bot.unbanChatMember(chat_id=chat_id, user_id=user_id)


async def pass_verify(bot: Bot, chat_id: int, user_id: int, callback: Update):
    await bot.restrictChatMember(chat_id=chat_id, user_id=user_id, permissions=ChatPermissions.all_permissions())
    await callback.callback_query.delete_message()
