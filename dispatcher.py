import logging
from typing import Any, Dict, Callable, Awaitable, Optional

from aiogram import Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

logger = logging.getLogger(__name__)


class MessageDispatcher:
    """Dispatch actions from the server to Telegram API calls."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.handlers: Dict[str, Callable[[Message, Dict[str, Any]], Awaitable[Optional[Message]]]] = {
            "reply": self._reply,
            "show_menu": self._show_menu,
            "send_photo": self._send_photo,
            "edit_message": self._edit_message,
            "delete_message": self._delete_message,
        }
        self._last_bot_message: Dict[int, Message] = {}

    async def dispatch(self, event: Message | CallbackQuery, response: Dict[str, Any]) -> None:
        action = response.get("action")
        data = response.get("data", {})
        if not action:
            return

        handler = self.handlers.get(action)
        if not handler:
            logger.warning("Unknown action received from server: %s", action)
            return

        message = event.message if isinstance(event, CallbackQuery) else event
        sent = await handler(message, data)
        if sent:
            self._last_bot_message[message.chat.id] = sent

    async def _reply(self, message: Message, data: Dict[str, Any]) -> Optional[Message]:
        text = data.get("text", "")
        return await message.answer(text)

    async def _show_menu(self, message: Message, data: Dict[str, Any]) -> Optional[Message]:
        buttons_cfg = data.get("buttons", [])
        markup: Optional[InlineKeyboardMarkup] = None
        if buttons_cfg:
            keyboard = [
                [InlineKeyboardButton(text=btn.get("text", ""), callback_data=btn.get("callback_data", ""))]
                for btn in buttons_cfg
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        return await message.answer(data.get("text", ""), reply_markup=markup)

    async def _send_photo(self, message: Message, data: Dict[str, Any]) -> Optional[Message]:
        return await self.bot.send_photo(
            chat_id=message.chat.id,
            photo=data.get("photo"),
            caption=data.get("caption"),
        )

    async def _edit_message(self, message: Message, data: Dict[str, Any]) -> Optional[Message]:
        message_id = data.get("message_id")
        if not message_id:
            last = self._last_bot_message.get(message.chat.id)
            if last:
                message_id = last.message_id
        if not message_id:
            return None
        buttons_cfg = data.get("buttons")
        markup: Optional[InlineKeyboardMarkup] = None
        if buttons_cfg:
            keyboard = [
                [InlineKeyboardButton(text=btn.get("text", ""), callback_data=btn.get("callback_data", ""))]
                for btn in buttons_cfg
            ]
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await self.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=data.get("text", ""),
            reply_markup=markup,
        )
        return None

    async def _delete_message(self, message: Message, data: Dict[str, Any]) -> Optional[Message]:
        message_id = data.get("message_id")
        if not message_id:
            last = self._last_bot_message.pop(message.chat.id, None)
            if last:
                message_id = last.message_id
        if not message_id:
            return None
        try:
            await self.bot.delete_message(chat_id=message.chat.id, message_id=message_id)
        except Exception:
            logger.exception("Failed to delete message")
        return None
