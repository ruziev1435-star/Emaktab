"""python-telegram-bot command handlers. Kept thin: all account-linking
logic lives in bot/linking.py (sync, ORM-touching, unit-testable without
asyncio); handlers here just parse the update and relay the result.

Django's ORM refuses synchronous queries from an async context unless
explicitly marked safe, so every call into bot.linking goes through
asgiref's sync_to_async.
"""

from asgiref.sync import sync_to_async
from django.db import IntegrityError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from attendance.services import confirm_student_attendance

from .linking import describe_linked_account, find_student_by_chat_id, link_chat_to_code

WELCOME_TEXT = (
    "Welcome to Kundalik+! \U0001F44B\n\n"
    "To link your account, open the platform, find your Telegram link code "
    "on your dashboard, then send:\n/link YOUR_CODE\n\n"
    "Once linked, you'll get meeting and attendance notifications here, and "
    "students can send /attendance to confirm they're at school."
)

NOT_LINKED_STUDENT_TEXT = (
    "This Telegram chat isn't linked to a Kundalik+ student account. "
    "Open the platform, find your link code on your dashboard, then send "
    "/link YOUR_CODE here — only students confirm attendance."
)

ATTENDANCE_CONFIRM_CALLBACK = "confirm_attendance"


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


async def attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/attendance — shows a one-tap inline button for a linked student to
    confirm they're in the building today. Staff/parent chats (or unlinked
    ones) get a plain explanation instead, since only students confirm
    attendance."""
    student = await sync_to_async(find_student_by_chat_id)(update.effective_chat.id)
    if student is None:
        await update.message.reply_text(NOT_LINKED_STUDENT_TEXT)
        return
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ I'm at school today", callback_data=ATTENDANCE_CONFIRM_CALLBACK)]]
    )
    await update.message.reply_text(
        "Tap below to confirm you're at school today. Your homeroom teacher, "
        "today's subject teachers, and your parents will be notified.",
        reply_markup=keyboard,
    )


async def attendance_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback for the inline '✅ I'm at school today' button registered by
    attendance() above."""
    query = update.callback_query
    await query.answer()
    student = await sync_to_async(find_student_by_chat_id)(query.message.chat_id)
    if student is None:
        await query.edit_message_text(NOT_LINKED_STUDENT_TEXT)
        return
    try:
        await sync_to_async(confirm_student_attendance)(student, via="telegram")
    except IntegrityError:
        await query.edit_message_text("You already confirmed attendance today. ✅")
        return
    await query.edit_message_text("✅ Attendance confirmed — teachers and parents notified.")
