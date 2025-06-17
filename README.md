# ClienteGame

This is a simple Telegram interface bot built with [Aiogram 3.x](https://docs.aiogram.dev/).
It forwards all user interactions to a backend server and performs the actions
returned by that server.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Export the following environment variables before running the bot:

- `BOT_TOKEN` – Telegram bot token
- `SERVER_URL` – base URL of ServidorGame (default: `http://localhost:8000`)

Run the bot with:

```bash
python bot.py
```
