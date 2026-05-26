# Handshake task watcher

Polls Handshake's "Available tasks" tab on a private project page every 15 minutes
and pushes a phone notification via [ntfy.sh](https://ntfy.sh) when new tasks appear.

## One-time setup

### 1. Install ntfy on your phone

- iOS: https://apps.apple.com/app/ntfy/id1625396347
- Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy

Open the app and **subscribe to this topic**:

```
jay-hs-nvufeowvie4dnqht
```

Anyone with the topic name can read your notifications, so don't share it.
If you ever think it's been seen by someone else, generate a new one with
`python3 -c "import secrets; print('jay-hs-' + secrets.token_urlsafe(12).lower().replace('_','').replace('-',''))"`
and update both the phone subscription and the `NTFY_TOPIC` GitHub secret.

### 2. Save your Handshake session locally

```bash
git clone <this-repo>
cd handshake-bot
pip install -r requirements.txt
playwright install chromium
python save_auth.py
```

A Chromium window opens. Log into Handshake with Google. Navigate to the tasks
page. Press Enter in the terminal. This creates `auth_state.json`.

### 3. Add GitHub secrets

In the repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**

- `HANDSHAKE_AUTH_STATE` — base64-encoded contents of `auth_state.json`. On Mac:
  ```bash
  base64 -i auth_state.json | pbcopy
  ```
  Then paste.
- `NTFY_TOPIC` — the topic string you picked in step 1.

**Do not commit `auth_state.json` to the repo.** It's in `.gitignore`.

### 4. Push and enable Actions

```bash
git add .
git commit -m "Initial commit"
git push
```

Go to the **Actions** tab on GitHub, enable workflows if prompted, and click
**Run workflow** on "Check Handshake tasks" to test it manually before relying
on the schedule.

## When the bot stops working

If you stop getting notifications and the Actions logs show errors, your
Handshake session has probably expired. Re-run `python save_auth.py` locally
and update the `HANDSHAKE_AUTH_STATE` secret.

The bot also pushes an ntfy notification to you when it errors, so you'll know.

## Tuning the selector

The first run with real tasks will tell you whether the scraper's selectors
work. If notifications don't fire when tasks are clearly present, check the
Actions log — it prints how many tasks it found. If it's finding zero, you'll
need to inspect the rendered HTML once a task is live and adjust the
`anchors = page.locator(...)` line in `check_tasks.py`.
