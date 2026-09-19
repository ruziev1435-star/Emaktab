import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from django.test import TestCase, TransactionTestCase

from accounts.models import Parent, StudentProfile, User
from attendance.models import AttendanceRecord, SubjectAttendanceRecord
from core.models import ClassSubjectTeacher, SchoolClass, Subject

from . import handlers
from .linking import describe_linked_account, find_student_by_chat_id, link_chat_to_code


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


def _make_callback_update(chat_id=555, data=None):
    """A minimal fake telegram.Update for a CallbackQueryHandler:
    update.callback_query.{answer,edit_message_text,message.chat_id,data}.
    attendance_confirm() ignores .data; lesson_confirm() reads it."""
    message = SimpleNamespace(chat_id=chat_id)
    callback_query = SimpleNamespace(
        answer=AsyncMock(), edit_message_text=AsyncMock(), message=message, data=data
    )
    update = SimpleNamespace(callback_query=callback_query)
    context = SimpleNamespace(args=[])
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


class FindStudentByChatIdTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT
        )
        self.teacher = User.objects.create_user(
            username="cara", password="x", role=User.Role.TEACHER
        )

    def test_unlinked_chat_returns_none(self):
        self.assertIsNone(find_student_by_chat_id("111"))

    def test_linked_student_is_found(self):
        self.student.telegram_chat_id = "111"
        self.student.save(update_fields=["telegram_chat_id"])
        self.assertEqual(find_student_by_chat_id("111"), self.student)

    def test_linked_non_student_is_not_returned(self):
        self.teacher.telegram_chat_id = "222"
        self.teacher.save(update_fields=["telegram_chat_id"])
        self.assertIsNone(find_student_by_chat_id("222"))


class AttendanceHandlerTests(TransactionTestCase):
    """/attendance and its inline-button callback, via fake Update/Context —
    same rationale as HandlerTests above for using TransactionTestCase."""

    def setUp(self):
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )
        self.teacher = User.objects.create_user(
            username="cara", password="x", role=User.Role.TEACHER, first_name="Cara"
        )

    def test_attendance_command_unlinked_chat_does_not_crash(self):
        update, context = _make_update("/attendance", chat_id=1001)
        asyncio.run(handlers.attendance(update, context))
        update.message.reply_text.assert_awaited_once()
        (text,), kwargs = update.message.reply_text.call_args
        self.assertIn("isn't linked", text)
        self.assertNotIn("reply_markup", kwargs)

    def test_attendance_command_linked_non_student_chat_is_declined(self):
        self.teacher.telegram_chat_id = "1002"
        self.teacher.save(update_fields=["telegram_chat_id"])
        update, context = _make_update("/attendance", chat_id=1002)
        asyncio.run(handlers.attendance(update, context))
        (text,), _ = update.message.reply_text.call_args
        self.assertIn("isn't linked", text)

    def test_attendance_command_linked_student_gets_button(self):
        self.student.telegram_chat_id = "1003"
        self.student.save(update_fields=["telegram_chat_id"])
        update, context = _make_update("/attendance", chat_id=1003)
        asyncio.run(handlers.attendance(update, context))
        _args, kwargs = update.message.reply_text.call_args
        self.assertIn("reply_markup", kwargs)
        button = kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(button.callback_data, handlers.ATTENDANCE_CONFIRM_CALLBACK)

    def test_confirm_button_creates_record_and_edits_message(self):
        self.student.telegram_chat_id = "1004"
        self.student.save(update_fields=["telegram_chat_id"])
        update, context = _make_callback_update(chat_id="1004")
        asyncio.run(handlers.attendance_confirm(update, context))
        update.callback_query.answer.assert_awaited_once()
        update.callback_query.edit_message_text.assert_awaited_once()
        (text,), _ = update.callback_query.edit_message_text.call_args
        self.assertIn("confirmed", text.lower())
        self.assertEqual(AttendanceRecord.objects.filter(student=self.student).count(), 1)

    def test_confirm_button_tapped_twice_does_not_crash(self):
        self.student.telegram_chat_id = "1005"
        self.student.save(update_fields=["telegram_chat_id"])
        update1, context1 = _make_callback_update(chat_id="1005")
        asyncio.run(handlers.attendance_confirm(update1, context1))

        update2, context2 = _make_callback_update(chat_id="1005")
        asyncio.run(handlers.attendance_confirm(update2, context2))
        (text,), _ = update2.callback_query.edit_message_text.call_args
        self.assertIn("already confirmed", text.lower())
        self.assertEqual(AttendanceRecord.objects.filter(student=self.student).count(), 1)

    def test_confirm_button_from_unlinked_chat_does_not_crash(self):
        update, context = _make_callback_update(chat_id="9999")
        asyncio.run(handlers.attendance_confirm(update, context))
        (text,), _ = update.callback_query.edit_message_text.call_args
        self.assertIn("isn't linked", text)


class LessonHandlerTests(TransactionTestCase):
    """/lesson and its per-subject inline-button callback."""

    def setUp(self):
        self.homeroom_teacher = User.objects.create_user(
            username="homeroom", password="x", role=User.Role.TEACHER, first_name="Homeroom"
        )
        self.math_teacher = User.objects.create_user(
            username="mathteacher", password="x", role=User.Role.TEACHER, first_name="MathT"
        )
        self.school_class = SchoolClass.objects.create(
            name="9-A", homeroom_teacher=self.homeroom_teacher
        )
        self.math = Subject.objects.create(name="Math")
        ClassSubjectTeacher.objects.create(
            school_class=self.school_class, subject=self.math, teacher=self.math_teacher
        )
        self.student = User.objects.create_user(
            username="dilnoza", password="x", role=User.Role.STUDENT, first_name="Dilnoza"
        )
        StudentProfile.objects.create(user=self.student, school_class=self.school_class)

    def test_lesson_command_unlinked_chat_does_not_crash(self):
        update, context = _make_update("/lesson", chat_id=2001)
        asyncio.run(handlers.lesson(update, context))
        (text,), kwargs = update.message.reply_text.call_args
        self.assertIn("isn't linked", text)
        self.assertNotIn("reply_markup", kwargs)

    def test_lesson_command_student_with_no_subjects_does_not_crash(self):
        lonely = User.objects.create_user(username="lonely", password="x", role=User.Role.STUDENT)
        lonely.telegram_chat_id = "2002"
        lonely.save(update_fields=["telegram_chat_id"])
        update, context = _make_update("/lesson", chat_id=2002)
        asyncio.run(handlers.lesson(update, context))
        (text,), kwargs = update.message.reply_text.call_args
        self.assertIn("No subjects", text)
        self.assertNotIn("reply_markup", kwargs)

    def test_lesson_command_lists_subjects_as_buttons(self):
        self.student.telegram_chat_id = "2003"
        self.student.save(update_fields=["telegram_chat_id"])
        update, context = _make_update("/lesson", chat_id=2003)
        asyncio.run(handlers.lesson(update, context))
        _args, kwargs = update.message.reply_text.call_args
        buttons = kwargs["reply_markup"].inline_keyboard
        self.assertEqual(len(buttons), 1)
        self.assertIn("Math", buttons[0][0].text)
        self.assertEqual(
            buttons[0][0].callback_data, f"{handlers.LESSON_CONFIRM_CALLBACK_PREFIX}{self.math.id}"
        )

    def test_lesson_confirm_creates_record_and_notifies(self):
        self.student.telegram_chat_id = "2004"
        self.student.save(update_fields=["telegram_chat_id"])
        update, context = _make_callback_update(
            chat_id="2004", data=f"{handlers.LESSON_CONFIRM_CALLBACK_PREFIX}{self.math.id}"
        )
        asyncio.run(handlers.lesson_confirm(update, context))
        update.callback_query.answer.assert_awaited_once()
        (text,), _ = update.callback_query.edit_message_text.call_args
        self.assertIn("Checked into", text)
        self.assertEqual(
            SubjectAttendanceRecord.objects.filter(student=self.student, subject=self.math).count(), 1
        )

    def test_lesson_confirm_tapped_twice_same_subject_does_not_crash(self):
        self.student.telegram_chat_id = "2005"
        self.student.save(update_fields=["telegram_chat_id"])
        data = f"{handlers.LESSON_CONFIRM_CALLBACK_PREFIX}{self.math.id}"
        update1, context1 = _make_callback_update(chat_id="2005", data=data)
        asyncio.run(handlers.lesson_confirm(update1, context1))
        update2, context2 = _make_callback_update(chat_id="2005", data=data)
        asyncio.run(handlers.lesson_confirm(update2, context2))
        (text,), _ = update2.callback_query.edit_message_text.call_args
        self.assertIn("already checked into", text.lower())
        self.assertEqual(
            SubjectAttendanceRecord.objects.filter(student=self.student, subject=self.math).count(), 1
        )

    def test_lesson_confirm_subject_not_taught_to_class_does_not_crash(self):
        self.student.telegram_chat_id = "2006"
        self.student.save(update_fields=["telegram_chat_id"])
        chemistry = Subject.objects.create(name="Chemistry")
        update, context = _make_callback_update(
            chat_id="2006", data=f"{handlers.LESSON_CONFIRM_CALLBACK_PREFIX}{chemistry.id}"
        )
        asyncio.run(handlers.lesson_confirm(update, context))
        (text,), _ = update.callback_query.edit_message_text.call_args
        self.assertIn("isn't taught", text)
        self.assertEqual(SubjectAttendanceRecord.objects.count(), 0)

    def test_lesson_confirm_unknown_subject_id_does_not_crash(self):
        self.student.telegram_chat_id = "2007"
        self.student.save(update_fields=["telegram_chat_id"])
        update, context = _make_callback_update(
            chat_id="2007", data=f"{handlers.LESSON_CONFIRM_CALLBACK_PREFIX}999999"
        )
        asyncio.run(handlers.lesson_confirm(update, context))
        (text,), _ = update.callback_query.edit_message_text.call_args
        self.assertIn("no longer exists", text)

    def test_lesson_confirm_from_unlinked_chat_does_not_crash(self):
        update, context = _make_callback_update(
            chat_id="9998", data=f"{handlers.LESSON_CONFIRM_CALLBACK_PREFIX}{self.math.id}"
        )
        asyncio.run(handlers.lesson_confirm(update, context))
        (text,), _ = update.callback_query.edit_message_text.call_args
        self.assertIn("isn't linked", text)
        self.assertEqual(SubjectAttendanceRecord.objects.count(), 0)
        self.assertEqual(AttendanceRecord.objects.count(), 0)
