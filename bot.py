import os
import asyncio
import logging
from typing import Any, Dict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp

BOT_TOKEN = os.getenv("BOT_TOKEN")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)

router = Router()


async def send_to_server(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send payload to ServidorGame and return the JSON response."""
    url = SERVER_URL.rstrip("/") + "/user/webhook"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.content_type == "application/json":
                    return await resp.json()
                return {}
    except Exception:
        logging.exception("Failed to reach server")
        return {}


async def perform_action(event: Any, response: Dict[str, Any], bot: Bot) -> None:
    """Execute action from server response."""
    action = response.get("action")
    data = response.get("data", {})

    if action == "reply":
        text = data.get("text", "")
        if isinstance(event, Message):
            await event.answer(text)
        else:  # CallbackQuery
            await event.message.answer(text)

    elif action == "send_photo":
        photo = data.get("photo")
        caption = data.get("caption")
        if isinstance(event, Message):
            chat_id = event.chat.id
        else:
            chat_id = event.message.chat.id
        if photo:
            await bot.send_photo(chat_id, photo, caption=caption)

    elif action:
        # For other actions, try calling Bot methods directly
        method = getattr(bot, action, None)
        if callable(method):
            if isinstance(event, Message):
                chat_id = event.chat.id
            else:
                chat_id = event.message.chat.id
            try:
                await method(chat_id=chat_id, **data)
            except TypeError:
                logging.warning("Invalid parameters for action %s", action)


async def build_message_payload(message: Message) -> Dict[str, Any]:
    return {
        "user_id": message.from_user.id if message.from_user else None,
        "username": message.from_user.username if message.from_user else None,
        "message_type": message.content_type,
        "message_content": message.text or message.caption,
        "data": message.model_dump(mode="json"),
    }


async def build_callback_payload(callback: CallbackQuery) -> Dict[str, Any]:
    return {
        "user_id": callback.from_user.id if callback.from_user else None,
        "username": callback.from_user.username if callback.from_user else None,
        "message_type": "callback_query",
        "message_content": callback.data,
        "data": callback.model_dump(mode="json"),
    }


@router.message(CommandStart())
async def start_handler(message: Message, bot: Bot) -> None:
    payload = await build_message_payload(message)
    response = await send_to_server(payload)
    await perform_action(message, response, bot)


@router.message()
async def handle_all_messages(message: Message, bot: Bot) -> None:
    payload = await build_message_payload(message)
    response = await send_to_server(payload)
    await perform_action(message, response, bot)


@router.callback_query()
async def handle_callbacks(callback: CallbackQuery, bot: Bot) -> None:
    payload = await build_callback_payload(callback)
    response = await send_to_server(payload)
    await perform_action(callback, response, bot)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot = Bot(BOT_TOKEN)

    dp.run_polling(bot)


if __name__ == "__main__":
    main()
