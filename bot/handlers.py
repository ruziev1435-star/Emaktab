"""python-telegram-bot command handlers. Kept thin: all account-linking
logic lives in bot/linking.py (sync, ORM-touching, unit-testable without
asyncio); handlers here just parse the update and relay the result.

Django's ORM refuses synchronous queries from an async context unless
explicitly marked safe, so every call into bot.linking goes through
asgiref's sync_to_async.
"""

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ContextTypes

from .linking import describe_linked_account, link_chat_to_code

WELCOME_TEXT = (
    "Welcome to Kundalik+! \U0001F44B\n\n"
    "To link your account, open the platform, find your Telegram link code "
    "on your dashboard, then send:\n/link YOUR_CODE\n\n"
    "Once linked, you'll get meeting and attendance notifications here."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start, optionally with a deep-link payload: /start <code>
    (Telegram passes the ?start= query param from a t.me/<bot>?start=<code>
    link straight through as context.args[0])."""
    if context.args:
        await _do_link(update, context.args[0])
    else:
        await update.message.reply_text(WELCOME_TEXT)


async def link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/link <code>"""
    if not context.args:
        await update.message.reply_text("Please include your code, e.g. /link ABCD1234")
        return
    await _do_link(update, context.args[0])


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/whoami — confirms the bot is alive and reports link status."""
    chat_id = update.effective_chat.id
    text = await sync_to_async(describe_linked_account)(chat_id)
    await update.message.reply_text(text)


async def _do_link(update: Update, code: str) -> None:
    chat_id = update.effective_chat.id
    _success, message = await sync_to_async(link_chat_to_code)(code, chat_id)
    await update.message.reply_text(message)
