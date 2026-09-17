# Kundalik+ — architecture notes

Kundalik+ is an improvement layer on top of Kundalik (the widely-used Uzbek
school platform) — not a replacement. It fixes Kundalik's UI/UX while keeping
the school–parent–student connection clear and active. This build is a
**demoable MVP for a pitch (Yoshlar Ventures)**, not a production system:
favor working, showable features over completeness or polish.

## Stack

- **Backend:** Django 5 (Python), SQLite for local/demo use
- **Frontend:** Django templates + Bootstrap 5, no build step — kept
  intentionally lightweight; a dedicated frontend may come later. Bootstrap's
  CSS/JS are vendored into `static/vendor/bootstrap/` (not loaded from a CDN)
  so the demo doesn't depend on outbound network access to a third party —
  update by re-pulling the `bootstrap` npm package's `dist/` files at the
  version pinned there.
- **Bot:** python-telegram-bot, since Telegram is the primary channel for
  Uzbek users (notifications + quick actions)

## Project layout

Django organizes code into "apps" rather than flat `models/`/`routes/`
folders — each app below owns its own `models.py`, `views.py`, `urls.py`,
`admin.py`, and `migrations/`. Read this table as the map from that generic
structure to this project's actual folders:

| Concern | Where it lives |
|---|---|
| Shared/cross-cutting models | `core/models.py` — `Subject`, `SchoolClass`, `ClassSubjectTeacher` |
| Auth & roles | `accounts/` — custom `User` model (role: principal / counsellor / teacher / student), `Parent` model (notification-only, no login), role-based dashboard views, student password-change |
| Routes | `kundalikplus/urls.py` is the root router; it `include()`s each app's own `urls.py` (e.g. `meetings/urls.py`, `attendance/urls.py`) under an app namespace |
| Meetings / calendar booking | `meetings/` — `StaffAvailability`, `Meeting` |
| Attendance confirmation | `attendance/` — `AttendanceRecord`, `NotificationLog`, `services.py` (the notify-homeroom-teacher/subject-teachers/parents fan-out) |
| Unit tests & exam schedule | `quizzes/` — `Quiz`/`Question`/`Choice`/`QuizAttempt`, `Exam` |
| Library / news aggregation | `library/` — `Article` (aggregated, not authored, content) |
| Telegram bot | `bot/` — `notify.py` (outbound sender used by other apps); bot command handlers (`/start`, meeting booking, attendance button) live here too |
| Settings & root config | `kundalikplus/` — `settings.py`, `urls.py`, `wsgi.py`/`asgi.py` |
| Templates | `templates/<app>/...`, extending `templates/base.html` |
| Static assets | `static/css/kundalikplus.css` |

New features should follow this pattern: either extend an existing app if the
model clearly belongs there, or `python manage.py startapp <name>` for a new
concern and register it in `INSTALLED_APPS` in `kundalikplus/settings.py`.

## Auth & roles

Four login roles only: `principal`, `counsellor`, `teacher`, `student` (see
`accounts.models.User.Role`). Parents are **not** a login role — they're
tracked via `accounts.models.Parent` (name + Telegram chat id + linked
`StudentProfile`s) purely as a notification target. One shared login page
(`/login/`) authenticates any role; `accounts.views.dashboard` then dispatches
to a role-specific dashboard template.

Passwords are simple by default (`AUTH_PASSWORD_VALIDATORS` is deliberately
empty — see `kundalikplus/settings.py`). `User.can_change_password`
(default `False`, clamped to `False` for non-students on save) is the
underlying support for letting a student opt into setting their own password
later; there is no self-service password-change UI yet — building it means
adding a view/form gated on that flag, not a new model.

## Database

`kundalikplus/settings.py` reads `DATABASE_URL` via `dj-database-url` and
falls back to local SQLite (`db.sqlite3`) when it's unset — this is a
placeholder, not a production configuration. To point at Postgres/MySQL
later, set `DATABASE_URL` (see `.env.example`) and install the matching
driver (`psycopg2-binary` / `mysqlclient`); neither is installed by default
to keep the base install light.

## Telegram bot

**Outbound:** `bot/notify.py` is the single choke point for outbound
Telegram messages (`notify(recipient, message)`). It degrades gracefully: if
`TELEGRAM_BOT_TOKEN` is unset or the send fails, it still records the
attempt in `attendance.models.NotificationLog` so the notification fan-out
is visible in the admin/demo without a live bot. Set `TELEGRAM_BOT_TOKEN` /
`TELEGRAM_BOT_USERNAME` in `.env` to enable real sends.

**Inbound:** `bot/linking.py` (pure, sync, unit-tested — no bot/network
involved) holds the account-linking logic; `bot/handlers.py` has the thin
async python-telegram-bot `CommandHandler`s (`/start`, `/link`, `/whoami`)
that call into it via `asgiref.sync_to_async`; `python manage.py runbot`
starts the bot with **long polling** (not a webhook — that needs a public
HTTPS endpoint this local/demo setup doesn't have; swap to a webhook only if
this gets deployed behind one). A logged-in user's link code and one-tap
deep link (`https://t.me/<bot>?start=<code>`) are shown at `/telegram/`
(linked from every dashboard's navbar). `User`/`Parent.telegram_link_code`
is auto-generated on save; `telegram_chat_id` is `unique=True` per model, so
`link_chat_to_code()` explicitly checks *both* models before linking to stop
one Telegram chat from silently stealing another account's notifications —
don't bypass that check when adding new linking entry points.

When testing linking logic in code, note that `TestCase` (transactional,
single connection) and `sync_to_async` (runs on a different thread) deadlock
against each other on SQLite — use `TransactionTestCase` for anything that
exercises an async handler, as `bot/tests.py` does.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Conventions

- Function-based views throughout (keep it simple for a small MVP team).
- No `routes/` or `models/` top-level folders — see the table above instead.
- No automated tests yet; each app has an empty `tests.py` stub from
  `startapp` (unused so far).
- Out of scope for the MVP (mention only if asked; don't build): the
  gamification / virtual-currency system (earning currency for discipline,
  grades, olympiad wins; redeemable for absence days or exam-fee coverage).
  It's a future roadmap item for the pitch, not a core feature.
