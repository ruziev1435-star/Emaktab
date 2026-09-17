import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from django.test import TestCase, TransactionTestCase

from accounts.models import Parent, User

from . import handlers
from .linking import describe_linked_account, link_chat_to_code


class LinkChatToCodeTests(TestCase):
    """Core linking logic — no bot, no network, just the ORM."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )
        self.teacher = User.objects.create_user(
            username="cara", password="x", role=User.Role.TEACHER, first_name="Cara"
        )
        self.parent = Parent.objects.create(full_name="Parent of Dilnoza")

    def test_valid_code_links_chat(self):
        ok, message = link_chat_to_code(self.student.telegram_link_code, "111")
        self.assertTrue(ok)
        self.student.refresh_from_db()
        self.assertEqual(self.student.telegram_chat_id, "111")
        self.assertIn("linked", message.lower())

    def test_unknown_code_rejected(self):
        ok, message = link_chat_to_code("not-a-real-code", "111")
        self.assertFalse(ok)
        self.assertIn("doesn't match", message)

    def test_empty_code_rejected(self):
        ok, message = link_chat_to_code("", "111")
        self.assertFalse(ok)
        self.assertIn("include your link code", message)

        ok, message = link_chat_to_code(None, "111")
        self.assertFalse(ok)

    def test_code_is_case_and_whitespace_insensitive(self):
        code = self.student.telegram_link_code
        ok, _ = link_chat_to_code(f"  {code.upper()}  ", "111")
        self.assertTrue(ok)
        self.student.refresh_from_db()
        self.assertEqual(self.student.telegram_chat_id, "111")

    def test_resending_same_code_from_same_chat_is_idempotent(self):
        link_chat_to_code(self.student.telegram_link_code, "111")
        ok, message = link_chat_to_code(self.student.telegram_link_code, "111")
        self.assertTrue(ok)
        self.assertIn("already linked", message)
        self.assertEqual(User.objects.get(pk=self.student.pk).telegram_chat_id, "111")

    def test_chat_already_linked_to_a_different_user_is_rejected(self):
        link_chat_to_code(self.student.telegram_link_code, "111")
        ok, message = link_chat_to_code(self.teacher.telegram_link_code, "111")
        self.assertFalse(ok)
        self.assertIn("already linked to a different", message)
        # teacher must NOT have been linked
        self.teacher.refresh_from_db()
        self.assertIsNone(self.teacher.telegram_chat_id)

    def test_chat_already_linked_to_a_parent_blocks_a_student_too(self):
        link_chat_to_code(self.parent.telegram_link_code, "111")
        ok, message = link_chat_to_code(self.student.telegram_link_code, "111")
        self.assertFalse(ok)
        self.student.refresh_from_db()
        self.assertIsNone(self.student.telegram_chat_id)

    def test_same_account_can_relink_to_a_new_chat(self):
        link_chat_to_code(self.student.telegram_link_code, "111")
        ok, message = link_chat_to_code(self.student.telegram_link_code, "222")
        self.assertTrue(ok)
        self.student.refresh_from_db()
        self.assertEqual(self.student.telegram_chat_id, "222")

    def test_parent_can_be_linked_via_code(self):
        ok, message = link_chat_to_code(self.parent.telegram_link_code, "333")
        self.assertTrue(ok)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.telegram_chat_id, "333")

    def test_sql_injection_like_code_is_just_treated_as_no_match(self):
        ok, message = link_chat_to_code("'; DROP TABLE accounts_user; --", "111")
        self.assertFalse(ok)
        self.assertIn("doesn't match", message)
        # table's still there
        self.assertTrue(User.objects.filter(pk=self.student.pk).exists())


class DescribeLinkedAccountTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )

    def test_unlinked_chat(self):
        text = describe_linked_account("999")
        self.assertIn("not linked", text)

    def test_linked_chat(self):
        link_chat_to_code(self.student.telegram_link_code, "999")
        text = describe_linked_account("999")
        self.assertIn("Dilnoza", text)
        self.assertIn("Student", text)


def _make_update(text, chat_id=555):
    """A minimal fake telegram.Update good enough for our handlers: they
    only touch update.message.reply_text, update.effective_chat.id, and
    (via CommandHandler parsing, simulated here manually) context.args."""
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message, effective_chat=SimpleNamespace(id=chat_id))
    args = text.split()[1:] if text.startswith("/") else text.split()
    context = SimpleNamespace(args=args)
    return update, context


class HandlerTests(TransactionTestCase):
    """Exercise the actual async handlers with a fake Update/Context —
    no network, no real Telegram server — to prove the bot's replies are
    correct, not just the underlying linking() function.

    TransactionTestCase (not TestCase): asyncio.run() + sync_to_async hands
    the ORM call to a different thread, and TestCase's outer transaction is
    bound to the main thread's connection — on SQLite that combination
    deadlocks with "database table is locked". TransactionTestCase doesn't
    wrap tests in an outer transaction (it truncates between tests instead),
    which sidesteps it.
    """

    def setUp(self):
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )

    def test_start_with_no_args_sends_welcome(self):
        update, context = _make_update("/start")
        asyncio.run(handlers.start(update, context))
        update.message.reply_text.assert_awaited_once()
        (text,), _ = update.message.reply_text.call_args
        self.assertIn("Welcome to Kundalik+", text)

    def test_start_with_code_payload_links(self):
        update, context = _make_update(f"/start {self.student.telegram_link_code}", chat_id=777)
        asyncio.run(handlers.start(update, context))
        update.message.reply_text.assert_awaited_once()
        (text,), _ = update.message.reply_text.call_args
        self.assertIn("linked", text.lower())
        self.student.refresh_from_db()
        self.assertEqual(self.student.telegram_chat_id, "777")

    def test_link_with_no_args_prompts_for_code(self):
        update, context = _make_update("/link")
        asyncio.run(handlers.link(update, context))
        (text,), _ = update.message.reply_text.call_args
        self.assertIn("include your code", text)

    def test_link_with_bad_code(self):
        update, context = _make_update("/link garbage", chat_id=888)
        asyncio.run(handlers.link(update, context))
        (text,), _ = update.message.reply_text.call_args
        self.assertIn("doesn't match", text)

    def test_whoami_before_and_after_linking(self):
        update, context = _make_update("/whoami", chat_id=999)
        asyncio.run(handlers.whoami(update, context))
        (text,), _ = update.message.reply_text.call_args
        self.assertIn("not linked", text)

        link_chat_to_code(self.student.telegram_link_code, "999")

        update2, context2 = _make_update("/whoami", chat_id=999)
        asyncio.run(handlers.whoami(update2, context2))
        (text2,), _ = update2.message.reply_text.call_args
        self.assertIn("Dilnoza", text2)
