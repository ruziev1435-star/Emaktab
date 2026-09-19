# Kundalik+

Kundalik+ is an improvement layer built on top of [Kundalik](https://kundalik.com), the
widely-used Uzbek school platform — not a replacement for it. It fixes Kundalik's
poor UI/UX while keeping the school–parent–student connection clear and active.

This build is a **demoable MVP for a pitch (Yoshlar Ventures)**, not a production
system — it favors working, showable features over completeness or polish.

## Roles

Four separate logins/access levels, each with its own dashboard:

- **Principal** (директор)
- **Counsellor** (завуч)
- **Teacher**
- **Student**

Parents are *not* a login role — they're tracked as a notification target (name +
Telegram) but don't sign into the platform.

Accounts start with simple, school-assigned default passwords (no complexity
requirements). Students can later opt to set their own password (underlying
support exists; the self-service UI isn't built yet).

## Core features

- **Meeting booking**: students book a calendar slot with a counsellor or
  principal; staff confirm/decline requests from their dashboard or a
  dedicated "my meetings" page.
- **Telegram bot**: connects a platform account to Telegram (`/link <code>` or
  a one-tap deep link) so notifications — meeting requests, confirmations —
  reach people where they already are.
- **Role dashboards**: students see their schedule/grades placeholder and a
  meeting entry point; teachers see their classes and rosters; counsellors/
  principals see meeting requests and the student list.

## Not yet built

- Attendance confirmation (manual Telegram button)
- Subject unit tests (quizzes)
- Library / news aggregation
- Prominent "upcoming exam" dashboard button
- A proper demo-data seed command (see manual steps below in the meantime)

## Stack

- **Backend:** Django 5 (Python), SQLite for local/demo use (swappable for
  Postgres via `DATABASE_URL`)
- **Frontend:** Django templates + Bootstrap 5, vendored locally (no CDN
  dependency), no build step
- **Bot:** python-telegram-bot, long polling (see below)

## Running locally

```bash
git clone -b claude/skills-d5v615 https://github.com/ruziev1435-star/Emaktab.git
cd Emaktab
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

### Create demo accounts

There's no seed command yet, so create them via the Django shell:

```bash
python manage.py shell
```
```python
from accounts.models import User
User.objects.create_user(username="principal", password="principal123", role=User.Role.PRINCIPAL, first_name="Amira")
User.objects.create_user(username="counsellor", password="counsellor123", role=User.Role.COUNSELLOR, first_name="Bek")
User.objects.create_user(username="teacher", password="teacher123", role=User.Role.TEACHER, first_name="Cara")
User.objects.create_user(username="student", password="student123", role=User.Role.STUDENT, first_name="Dilnoza")
exit()
```

### Run the server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/login/` and log in with any of the accounts above.

### Optional: run the Telegram bot

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram to get a token and username.
2. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN` and `TELEGRAM_BOT_USERNAME` (uncomment those lines — a line starting with `#` is ignored).
3. In a second terminal (same venv activated):
   ```bash
   python manage.py runbot
   ```
4. Log into the web app, go to the "Connect Telegram" link in the navbar, and either tap the deep link or send `/link <code>` to your bot directly.

## Project layout

Django organizes code into "apps" rather than flat `models/`/`routes/` folders:

| Concern | Where it lives |
|---|---|
| Shared/cross-cutting models | `core/` — `Subject`, `SchoolClass`, `ClassSubjectTeacher` |
| Auth & roles | `accounts/` — custom `User` model, `Parent`, dashboards |
| Meetings / calendar booking | `meetings/` |
| Attendance confirmation | `attendance/` |
| Unit tests & exam schedule | `quizzes/` |
| Library / news aggregation | `library/` |
| Telegram bot | `bot/` — `notify.py` (outbound), `linking.py`/`handlers.py` (inbound) |
| Settings & root config | `kundalikplus/` |

See `CLAUDE.md` for full architecture notes, conventions, and known gaps.
