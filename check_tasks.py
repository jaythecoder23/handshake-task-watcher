"""
Checks Handshake for new available tasks and pushes a notification via ntfy.sh
when any appear. State (last-seen task IDs) is persisted to seen_tasks.json,
which GitHub Actions commits back to the repo so it survives between runs.
"""

import base64
import json
import os
import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

TASKS_URL = "https://ai.joinhandshake.com/fellow/aebaf7d0-8cc1-4b11-82bc-3a57a2f4ff4f/tasks"
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
AUTH_STATE_B64 = os.environ["HANDSHAKE_AUTH_STATE"]
SEEN_FILE = Path("seen_tasks.json")


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2))


def notify(title: str, body: str) -> None:
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "high",
            "Tags": "briefcase",
            "Click": TASKS_URL,
        },
        timeout=15,
    )


def scrape_tasks() -> list[dict]:
    """Returns list of {id, title} for tasks visible under Available tasks."""
    # Write auth state to a temp file Playwright can load
    auth_path = Path("/tmp/auth_state.json")
    auth_path.write_bytes(base64.b64decode(AUTH_STATE_B64))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(auth_path))
        page = context.new_page()
        page.goto(TASKS_URL, wait_until="networkidle", timeout=60_000)

        # Make sure Available tasks tab is active. The screenshot shows it's
        # already selected by default, but click defensively.
        try:
            page.get_by_role("tab", name="Available tasks").click(timeout=5_000)
        except Exception:
            pass

        # Wait for either task cards or the "No results" empty state.
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.wait_for_timeout(2_000)  # let React settle

        # If we see "No results", session is good but list is empty.
        if page.get_by_text("No results", exact=False).count() > 0:
            browser.close()
            return []

        # Heuristic: each task is a card/row. Without seeing a populated page,
        # the safest selector is "any element inside the tasks panel that looks
        # like a list item with a title". Adjust SELECTOR below once you've
        # seen a real task render.
        #
        # Common patterns: role=listitem, role=link to /task/<id>, or a div
        # with data-testid. Start broad, then tighten.
        tasks = []
        # Try anchors pointing to a task detail page first.
        anchors = page.locator(
            "a[href*='/task/'], a[href*='/tasks/'][href*='-']"
        ).all()
        for a in anchors:
            href = a.get_attribute("href") or ""
            text = (a.inner_text() or "").strip()
            if not href or not text:
                continue
            task_id = href.rstrip("/").split("/")[-1]
            tasks.append({"id": task_id, "title": text.split("\n")[0][:200]})

        # Dedupe by id, preserve order.
        seen_ids = set()
        unique = []
        for t in tasks:
            if t["id"] in seen_ids:
                continue
            seen_ids.add(t["id"])
            unique.append(t)

        browser.close()
        return unique


def main() -> int:
    try:
        tasks = scrape_tasks()
    except Exception as e:
        # Tell yourself when the bot breaks instead of failing silently.
        notify("Handshake bot error", f"Scrape failed: {e!r}\n\nLikely session expired — re-run save_auth.py.")
        print(f"ERROR: {e!r}", file=sys.stderr)
        return 1

    seen = load_seen()
    current_ids = {t["id"] for t in tasks}
    new_tasks = [t for t in tasks if t["id"] not in seen]

    print(f"Found {len(tasks)} available tasks ({len(new_tasks)} new)")

    if new_tasks:
        lines = [f"• {t['title']}" for t in new_tasks[:10]]
        if len(new_tasks) > 10:
            lines.append(f"…and {len(new_tasks) - 10} more")
        notify(
            title=f"{len(new_tasks)} new Handshake task{'s' if len(new_tasks) != 1 else ''}",
            body="\n".join(lines),
        )

    # Persist current set (not the union — so tasks that disappear can re-notify
    # if they come back. If you'd rather only ever notify once per id, use
    # seen | current_ids instead.)
    save_seen(current_ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
