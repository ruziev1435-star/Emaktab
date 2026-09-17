"""Core account-linking logic, kept separate from the python-telegram-bot
handlers so it can be unit-tested directly (no bot, no network, no asyncio)."""

from accounts.models import Parent, User

_MODELS = (User, Parent)


def _find_account_by_code(code):
    for model in _MODELS:
        account = model.objects.filter(telegram_link_code__iexact=code).first()
        if account:
            return model, account
    return None, None


def _chat_already_linked_elsewhere(chat_id, model, account):
    for other_model in _MODELS:
        qs = other_model.objects.filter(telegram_chat_id=chat_id)
        if other_model is model:
            qs = qs.exclude(pk=account.pk)
        if qs.exists():
            return True
    return False


def link_chat_to_code(code, chat_id):
    """Link a Telegram chat to the User/Parent whose link code matches.

    Returns (success: bool, message: str). Never raises — every failure
    path (bad code, chat already linked elsewhere) is reported back as a
    message so the bot handler can just relay it to the user.
    """
    code = (code or "").strip()
    if not code:
        return False, "Please include your link code, e.g. /link ABCD1234"

    chat_id = str(chat_id)
    model, account = _find_account_by_code(code)
    if account is None:
        return False, "That code doesn't match any Kundalik+ account. Double-check it and try again."

    if account.telegram_chat_id == chat_id:
        return True, f"You're already linked as {account}. ✅"

    if _chat_already_linked_elsewhere(chat_id, model, account):
        return False, (
            "This Telegram account is already linked to a different Kundalik+ account. "
            "Ask your school to unlink it first if you need to switch."
        )

    account.telegram_chat_id = chat_id
    account.save(update_fields=["telegram_chat_id"])
    return True, f"You're linked! ✅ This chat is now connected as {account}."


def describe_linked_account(chat_id):
    chat_id = str(chat_id)
    for model in _MODELS:
        account = model.objects.filter(telegram_chat_id=chat_id).first()
        if account:
            role = account.get_role_display() if model is User else "parent"
            return f"You're linked as {account} ({role})."
    return "You're not linked to a Kundalik+ account yet. Send /link YOUR_CODE to connect."
