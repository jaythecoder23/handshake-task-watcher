"""
Run this ONCE locally to save your Handshake login session.

Usage:
    pip install playwright
    playwright install chromium
    python save_auth.py

A browser window will open. Log into Handshake with Google.
Once you see the tasks page, come back to the terminal and press Enter.
The script will save your session to auth_state.json.

Then base64-encode that file and paste it into a GitHub secret
named HANDSHAKE_AUTH_STATE (instructions in README).

You'll need to re-run this whenever the bot starts failing to find tasks
(session expired — usually weeks, sometimes longer).
"""

from playwright.sync_api import sync_playwright

TASKS_URL = "https://ai.joinhandshake.com/fellow/aebaf7d0-8cc1-4b11-82bc-3a57a2f4ff4f/tasks"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(TASKS_URL)

    print("\n" + "=" * 60)
    print("Log in with Google in the browser window.")
    print("Navigate to the Available tasks tab.")
    print("Once you can see the page normally, come back here.")
    print("=" * 60)
    input("\nPress Enter when you're logged in and on the tasks page... ")

    context.storage_state(path="auth_state.json")
    print("\nSaved auth_state.json")
    print("\nNext: encode it for GitHub secrets with:")
    print("  base64 -i auth_state.json | pbcopy")
    print("Then paste into a secret named HANDSHAKE_AUTH_STATE.")
    browser.close()
