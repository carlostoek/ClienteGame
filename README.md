# ClienteGame

ClienteGame is a Telegram bot built with Aiogram 3.x. Its sole purpose is to
act as an interface for the game server `ServidorGame`.

When a user sends any message or presses a button, ClienteGame forwards the
complete event data to `ServidorGame` at `/user/webhook` via a POST request.
The server responds with an action to perform, such as sending a reply or a
photo. ClienteGame executes this action and relays the response back to the
user.

## Quick start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set the following environment variables:
   - `BOT_TOKEN`: Telegram bot token.
   - `SERVER_URL`: Base URL of `ServidorGame` (default: `http://localhost:8000`).
3. Run the bot:
   ```bash
   python bot.py
   ```
