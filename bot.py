import os
import asyncio
import logging
from typing import Any, Dict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp

from dispatcher import MessageDispatcher

BOT_TOKEN = os.getenv("BOT_TOKEN")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)

router = Router()
dispatcher: MessageDispatcher | None = None


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
    if dispatcher:
        await dispatcher.dispatch(message, response)


@router.message()
async def handle_all_messages(message: Message, bot: Bot) -> None:
    payload = await build_message_payload(message)
    response = await send_to_server(payload)
    if dispatcher:
        await dispatcher.dispatch(message, response)


@router.callback_query()
async def handle_callbacks(callback: CallbackQuery, bot: Bot) -> None:
    payload = await build_callback_payload(callback)
    response = await send_to_server(payload)
    if dispatcher:
        await dispatcher.dispatch(callback, response)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot = Bot(BOT_TOKEN)
    global dispatcher
    dispatcher = MessageDispatcher(bot)

    dp.run_polling(bot)


if __name__ == "__main__":
    main()
