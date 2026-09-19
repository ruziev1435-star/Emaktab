import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot.handlers import (
    ATTENDANCE_CONFIRM_CALLBACK,
    LESSON_CONFIRM_CALLBACK_PREFIX,
    attendance,
    attendance_confirm,
    lesson,
    lesson_confirm,
    link,
    start,
    whoami,
)


def _ensure_event_loop():
    """python-telegram-bot 21.x's Application.run_polling() calls the
    deprecated asyncio.get_event_loop() internally, expecting it to
    auto-create a loop when none exists for this thread. Python removed
    that auto-creation (a RuntimeError instead, as of 3.14) — explicitly
    creating and registering one here keeps run_polling() working without
    patching the library itself."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


class Command(BaseCommand):
    help = (
        "Run the Kundalik+ Telegram bot using long polling. Requires "
        "TELEGRAM_BOT_TOKEN to be set (see .env.example). Polling, not a "
        "webhook, is used so this works from any machine without a public "
        "HTTPS endpoint — swap to a webhook only if/when this is deployed "
        "behind one."
    )

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            raise CommandError(
                "TELEGRAM_BOT_TOKEN is not set. Add it to your .env file (see .env.example) "
                "with a token from @BotFather, then re-run this command."
            )

        _ensure_event_loop()
        application = Application.builder().token(token).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("link", link))
        application.add_handler(CommandHandler("whoami", whoami))
        application.add_handler(CommandHandler("attendance", attendance))
        application.add_handler(
            CallbackQueryHandler(attendance_confirm, pattern=f"^{ATTENDANCE_CONFIRM_CALLBACK}$")
        )
        application.add_handler(CommandHandler("lesson", lesson))
        application.add_handler(
            CallbackQueryHandler(lesson_confirm, pattern=f"^{LESSON_CONFIRM_CALLBACK_PREFIX}\\d+$")
        )

        self.stdout.write(self.style.SUCCESS("Kundalik+ bot starting (long polling)... Ctrl+C to stop."))
        application.run_polling()
