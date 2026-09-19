# Kundalik+ — Overview & Task Roadmap

## Overview

Kundalik+ is an improvement layer built on top of [Kundalik](https://kundalik.com),
the widely-used Uzbek school platform — not a replacement for it. It fixes
Kundalik's poor UI/UX while keeping the school–parent–student connection clear
and active. This build is a **demoable MVP for a pitch (Yoshlar Ventures)**,
not a production system: working, showable features matter more than
completeness or polish.

Four login roles only — **principal**, **counsellor**, **teacher**, **student**
— each with simple default passwords and their own dashboard. Parents are
tracked as a notification target (via Telegram) but don't get a platform
login. Telegram is the primary channel for reaching people, since it's the
most-used platform in Uzbekistan.

Stack: **Django 5 (Python)** backend, **SQLite** for local/demo use (swappable
for Postgres later), **Bootstrap 5** templates with no build step, and
**python-telegram-bot** for the bot.

## Tasks

### Done

1. **Backend skeleton & architecture docs** — Django project structure,
   folders for models/routes/auth/bot mapped onto Django's app convention,
   `CLAUDE.md` architecture notes, curated `requirements.txt`, an env-driven
   database placeholder (`DATABASE_URL`, defaulting to local SQLite).
2. **Data models & 4-role authentication** — custom `User` model with the
   four roles, simple passwords (no complexity requirements), the
   `can_change_password` flag as underlying support for a future student
   self-service password change.
3. **Student dashboard** — the demo centerpiece: a clean, minimal view with
   a schedule/grades placeholder and a prominent entry point into the
   meeting section.
4. **Teacher & counsellor/principal dashboards** — teachers see their
   classes and rosters; counsellors/principals see meeting requests (with
   inline confirm/decline) and the student list.
5. **Meeting section** — a calendar-style UI for students to request a
   meeting with a counsellor or principal, and for staff to accept/manage
   requests, accessible from the web and referenced from the Telegram bot.
6. **Telegram bot — basic framework** — account linking (a platform user
   connects their Telegram via a link code or one-tap deep link), confirmed
   the bot responds (`/start`, `/link`, `/whoami`), running via long
   polling. The plumbing other bot features build on.
7. **Attendance confirmation — two-step check-in.** Step 1: `/attendance`
   (with a web fallback at `/attendance/confirm/`) confirms building entry,
   notifying the homeroom teacher and parents. Step 2: `/lesson` lists that
   day's subjects for the student's class as inline buttons; tapping one
   confirms they're in that specific class, notifying that subject's
   teacher, the homeroom teacher, and parents. Both steps use a
   `CallbackQueryHandler` for the button tap and restrict to student
   accounts (`limit_choices_to` alone doesn't enforce that at the ORM
   level). Step 2 is repeatable per subject per day; step 1 is once/day.

### Pending

8. **Subject unit tests (quizzes)** — short tests delivered after a topic
   is studied. (Models exist in `quizzes/`; templates are missing.)
9. **Library / news aggregation** — aggregated (not authored) articles on
   Uzbek current events, teen mental health, and the digital world.
   (Models exist in `library/`; templates are missing.)
10. **Prominent exam button** — when a student has an upcoming exam/control
    work, make it visually larger on the dashboard so it can't be missed.
11. **Demo seed data + polished setup instructions** — a real seed command
    (accounts are currently created manually via the Django shell each
    time) and finishing touches on `README.md`.

### Explicitly out of scope for this MVP

The gamification/virtual-currency system (earning currency for discipline,
grades, olympiad wins; redeemable for absence days or exam-fee coverage) —
a future roadmap item for the pitch, not a core feature to build now.
