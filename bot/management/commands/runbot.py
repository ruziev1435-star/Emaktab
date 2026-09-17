from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from telegram.ext import Application, CommandHandler

from bot.handlers import link, start, whoami


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

        application = Application.builder().token(token).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("link", link))
        application.add_handler(CommandHandler("whoami", whoami))

        self.stdout.write(self.style.SUCCESS("Kundalik+ bot starting (long polling)... Ctrl+C to stop."))
        application.run_polling()
