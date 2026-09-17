---
description: Build/launch/drive recipe for verifying Kundalik+ (Django) locally.
---

# Verifying Kundalik+

## Setup

```bash
cd /home/user/Emaktab   # or wherever the repo is checked out
python3 -m venv .venv && source .venv/bin/activate   # if .venv doesn't exist yet
pip install -r requirements.txt
pip install playwright   # not in requirements.txt; only needed for browser-driven verification
rm -f db.sqlite3
python manage.py migrate
```

## Seed data

There's no seed command yet (task #8, not built). Seed via a one-off script run
with `PYTHONPATH=<repo root>` so `kundalikplus.settings` resolves:

```bash
PYTHONPATH=/home/user/Emaktab python /path/to/seed_script.py
```

`django.setup()` first, then create `User.objects.create_user(...)` per role
(`principal`/`counsellor`/`teacher`/`student` in `accounts.models.User.Role`),
`core.models.SchoolClass`/`Subject`/`ClassSubjectTeacher`, and
`meetings.models.StaffAvailability` if you need bookable slots (weekday
0-4, e.g. `time(9,0)`-`time(10,0)`).

## Launch

```bash
nohup python manage.py runserver 127.0.0.1:PORT >/tmp/server.log 2>&1 &
sleep 2
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:PORT/login/   # sanity check
```

Pick a fresh port per verification run rather than reusing 8000 — stray
backgrounded servers from earlier runs are easy to leave behind.

## Drive it

Playwright + the pre-installed Chromium (not the pip-downloaded one):

```python
browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
```

(Check `ls /opt/pw-browsers/` if that exact version dir is gone.)

Demo accounts: `principal`/`counsellor`/`teacher`/`student` usernames with
matching `<role>123` passwords is a convention used across prior sessions —
not enforced anywhere, just keep it consistent if you want prior scripts'
assumptions to still hold.

## Gotchas

- **Re-logging in without logging out first, in the same Playwright page,
  intermittently fails CSRF validation** (reproduced via curl too — looks
  like a Django `rotate_token()`-on-login interaction, not app-specific).
  Always do `page.context.clear_cookies()` before each `login()` call in a
  test script rather than trying to detect/click a "Log out" button.
- Static files 404 unless `STATICFILES_DIRS` includes the project's
  `static/` dir (already fixed in `kundalikplus/settings.py`, but if a page
  renders unstyled, check this first).
- Bootstrap is vendored in `static/vendor/bootstrap/` (not a CDN) —
  `page.content()` should never need to reach `cdn.jsdelivr.net`.
- Forms often have >1 `csrfmiddlewaretoken` hidden input on the same page
  (navbar logout form + page's own form), so
  `page.locator('input[name="csrfmiddlewaretoken"]')` needs `.first`.
- ~~`meetings._open_slots_for` built slot datetimes with
  `tzinfo=timezone.now().tzinfo` (UTC) instead of the project's local
  `TIME_ZONE`~~ — **fixed 2026-09-17**: now uses `timezone.make_aware()`
  and anchors day-iteration on `timezone.localtime(now).date()`. If a
  future change reintroduces raw `datetime.combine(..., tzinfo=...)` in
  this file, check it against a `StaffAvailability` window the same way:
  seed a window, check the *displayed* slot times match the *configured*
  hours, not just that slots appear.
- Known-broken pages as of 2026-09-17 (missing templates, `TemplateDoesNotExist`,
  500s): `/attendance/confirm/`, `/attendance/status/`, `/quizzes/`,
  `/library/`. `/meetings/mine/` was in this list too but was fixed.
- `login.html`'s `<label>`s aren't linked to their inputs via `for`/`id`
  (no `id` on the `<input>` elements at all) — a real accessibility gap,
  not yet fixed.

## Useful checks beyond the obvious click-through

- A11y DOM audit via `page.evaluate()`: unlinked `<label>`s, form controls
  with no accessible name, heading-level skips, `<html lang>`. See any
  recent verify pass's script for the exact JS snippet.
- Contrast: compute WCAG ratios for custom CSS colors in
  `static/css/kundalikplus.css` with a plain Python luminance/contrast
  function rather than eyeballing screenshots — several `kp-*` tokens
  (`#7a8699` on white/near-white) sit around 3.3-3.7:1, under the 4.5:1
  AA threshold for normal text.
- ~~The booking view never validated a submitted `start`/`end` against
  the staff's actual `StaffAvailability` windows~~ — **fixed 2026-09-17**:
  the POST handler now checks the submitted (start, end) against the
  `slots` list computed for that request. HTTP status alone (302) looks
  fine either way for a rejected attempt, so verifying this means
  checking the DB afterward, not just the response code.
- ~~`Meeting.topic` (`max_length=255`) wasn't validated before
  `.get_or_create()`~~ — **fixed 2026-09-17**: the view now checks
  `len(topic) > Meeting._meta.get_field("topic").max_length` explicitly.
  When re-testing a fix like this, don't build the crafted POST's
  `start`/`end` from local `datetime.now()` — this container's system
  clock is UTC, not the app's `TIME_ZONE`, and the slot-validity check
  (see above) will reject a naive/mismatched timestamp for a different
  reason than the one you're trying to test, giving a false pass/fail.
  Pull the real slot value from the rendered page's slot-button
  `onclick` attribute instead (it's server-computed and tz-correct).
