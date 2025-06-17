import asyncio
import os
import logging
from typing import Any, Dict

from aiogram import Bot, Dispatcher, Router, types
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


async def perform_action(target: types.Message, response: Dict[str, Any], bot: Bot) -> None:
    action = response.get("action")
    data = response.get("data", {})

    if not action:
        return

    if action == "reply":
        await target.answer(data.get("text", ""))
        return
    if action == "send_photo":
        await bot.send_photo(chat_id=target.chat.id, photo=data.get("photo"), caption=data.get("caption"))
        return

    method = getattr(bot, action, None)
    if method:
        if "chat_id" not in data:
            data["chat_id"] = target.chat.id
        await method(**data)
    else:
        logger.warning("Unknown action received from server: %s", action)


@router.message(CommandStart())
async def start_handler(message: types.Message, bot: Bot):
    payload = build_payload_from_message(message, "command")
    response = await send_to_server(payload)
    await perform_action(message, response, bot)


@router.message()
async def universal_message_handler(message: types.Message, bot: Bot):
    message_type = "command" if message.text and message.text.startswith("/") else "text"
    payload = build_payload_from_message(message, message_type)
    response = await send_to_server(payload)
    await perform_action(message, response, bot)


@router.callback_query()
async def callback_handler(callback: types.CallbackQuery, bot: Bot):
    payload = build_payload_from_callback(callback)
    response = await send_to_server(payload)
    await perform_action(callback.message, response, bot)
    await callback.answer()


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
