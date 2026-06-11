import asyncio
from playwright.async_api import async_playwright
import time
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        print("Navigating to frontend...")
        await page.goto("http://localhost:3000")
        await page.wait_for_load_state("networkidle")

        print("Clicking Integration tab...")
        await page.click("#tab-integration")

        print("Setting up Python API URL...")
        await page.fill("#input-python-url", "http://localhost:8000/api/quotes")

        print("Starting polling...")
        await page.click("#btn-toggle-polling")

        # Wait for connection
        print("Waiting for connection status...")
        try:
            await page.wait_for_selector("text=CONNECTED & REFRESHING", timeout=15000)
        except:
            print("Connection status indicator not found, but proceeding...")

        print("Switching back to Terminal...")
        await page.click("#tab-terminal")

        # Ensure some data is visible
        await asyncio.sleep(2)

        # Take screenshot of the terminal
        await page.screenshot(path="/tmp/screenshots/terminal_integrated.png", full_page=True)
        print("Screenshot saved as /tmp/screenshots/terminal_integrated.png")

        # Verify Replay mode
        print("Testing Replay mode...")
        await page.click("#quick-set-replay")
        await page.wait_for_selector("#duckdb-replay-deck")

        # Select a file
        await page.select_option("#replay-file-select", "20260421.duckdb")
        await asyncio.sleep(2) # Wait for dates to load

        # Start replay
        await page.click("#replay-play-pause")
        await asyncio.sleep(5) # Let it run for a bit

        await page.screenshot(path="/tmp/screenshots/replay_active.png", full_page=True)
        print("Screenshot saved as /tmp/screenshots/replay_active.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
