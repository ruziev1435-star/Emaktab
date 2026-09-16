# Kundalik+ — architecture notes

Kundalik+ is an improvement layer on top of Kundalik (the widely-used Uzbek
school platform) — not a replacement. It fixes Kundalik's UI/UX while keeping
the school–parent–student connection clear and active. This build is a
**demoable MVP for a pitch (Yoshlar Ventures)**, not a production system:
favor working, showable features over completeness or polish.

## Stack

- **Backend:** Django 5 (Python), SQLite for local/demo use
- **Frontend:** Django templates + Bootstrap 5 (via CDN), no build step — kept
  intentionally lightweight; a dedicated frontend may come later
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
`StudentProfile`s) purely as a notification target. Default passwords are
simple; students can change their own via `/password-change/`
(`accounts.views.KundalikPasswordChangeView`).

## Database

`kundalikplus/settings.py` reads `DATABASE_URL` via `dj-database-url` and
falls back to local SQLite (`db.sqlite3`) when it's unset — this is a
placeholder, not a production configuration. To point at Postgres/MySQL
later, set `DATABASE_URL` (see `.env.example`) and install the matching
driver (`psycopg2-binary` / `mysqlclient`); neither is installed by default
to keep the base install light.

## Telegram bot

`bot/notify.py` is the single choke point for outbound Telegram messages
(`notify(recipient, message)`). It degrades gracefully: if `TELEGRAM_BOT_TOKEN`
is unset or the send fails, it still records the attempt in
`attendance.models.NotificationLog` so the notification fan-out is visible in
the admin/demo without a live bot. Set `TELEGRAM_BOT_TOKEN` /
`TELEGRAM_BOT_USERNAME` in `.env` to enable real sends.

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
