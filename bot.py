import asyncio
import os
import logging
from typing import Any, Dict, Callable, Awaitable, Optional

from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
import aiohttp

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

async def send_to_server(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{SERVER_URL.rstrip('/')}/user/webhook"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            try:
                data = await resp.json()
            except Exception:
                logger.exception("Failed to parse server response")
                data = {}
            return data


def build_payload_from_message(message: types.Message, message_type: str) -> Dict[str, Any]:
    return {
        "user_id": message.from_user.id if message.from_user else None,
        "username": message.from_user.username if message.from_user else None,
        "message_type": message_type,
        "message_content": message.text or message.caption,
        "data": message.model_dump(mode="python"),
    }


def build_payload_from_callback(callback: types.CallbackQuery) -> Dict[str, Any]:
    return {
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "message_type": "callback",
        "message_content": callback.data,
        "data": callback.model_dump(mode="python"),
    }


class ActionDispatcher:
    """Dispatches server actions to Telegram API calls."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.handlers: Dict[str, Callable[[types.Message, Dict[str, Any]], Awaitable[Optional[types.Message]]]] = {
            "reply": self._reply,
            "show_menu": self._show_menu,
            "send_photo": self._send_photo,
            "edit_message": self._edit_message,
            "delete_message": self._delete_message,
        }
        self._last_bot_message: Dict[int, types.Message] = {}

    async def dispatch(self, target: types.Message, response: Dict[str, Any]) -> None:
        action = response.get("action")
        data = response.get("data", {})
        if not action:
            return

        handler = self.handlers.get(action)
        if handler:
            message = await handler(target, data)
            if message:
                self._last_bot_message[target.chat.id] = message
        else:
            logger.warning("Unknown action received from server: %s", action)

    async def _reply(self, target: types.Message, data: Dict[str, Any]) -> Optional[types.Message]:
        return await target.answer(data.get("text", ""))

    async def _show_menu(self, target: types.Message, data: Dict[str, Any]) -> Optional[types.Message]:
        buttons = [
            [InlineKeyboardButton(text=btn.get("text", ""), callback_data=btn.get("callback_data", ""))]
            for btn in data.get("buttons", [])
        ]
        markup = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        return await target.answer(data.get("text", ""), reply_markup=markup)

    async def _send_photo(self, target: types.Message, data: Dict[str, Any]) -> Optional[types.Message]:
        return await self.bot.send_photo(
            chat_id=target.chat.id,
            photo=data.get("photo"),
            caption=data.get("caption"),
        )

    async def _edit_message(self, target: types.Message, data: Dict[str, Any]) -> Optional[types.Message]:
        message_id = data.get("message_id")
        if not message_id:
            last = self._last_bot_message.get(target.chat.id)
            message_id = last.message_id if last else None
        if not message_id:
            return None
        await self.bot.edit_message_text(
            chat_id=target.chat.id,
            message_id=message_id,
            text=data.get("text", ""),
        )
        # fetch the edited message object is not trivial; return None
        return None

    async def _delete_message(self, target: types.Message, data: Dict[str, Any]) -> Optional[types.Message]:
        message_id = data.get("message_id")
        if not message_id:
            last = self._last_bot_message.pop(target.chat.id, None)
            message_id = last.message_id if last else None
        if not message_id:
            return None
        await self.bot.delete_message(chat_id=target.chat.id, message_id=message_id)
        return None


action_dispatcher: Optional[ActionDispatcher] = None


@router.message(CommandStart())
async def start_handler(message: types.Message, bot: Bot):
    payload = build_payload_from_message(message, "command")
    response = await send_to_server(payload)
    if action_dispatcher:
        await action_dispatcher.dispatch(message, response)


@router.message()
async def universal_message_handler(message: types.Message, bot: Bot):
    message_type = "command" if message.text and message.text.startswith("/") else "text"
    payload = build_payload_from_message(message, message_type)
    response = await send_to_server(payload)
    if action_dispatcher:
        await action_dispatcher.dispatch(message, response)


@router.callback_query()
async def callback_handler(callback: types.CallbackQuery, bot: Bot):
    payload = build_payload_from_callback(callback)
    response = await send_to_server(payload)
    if action_dispatcher:
        await action_dispatcher.dispatch(callback.message, response)
    await callback.answer()


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(BOT_TOKEN)
    global action_dispatcher
    action_dispatcher = ActionDispatcher(bot)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
