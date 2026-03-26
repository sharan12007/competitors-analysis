"""
Diagnose Playwright browser connectivity on Windows.
Run from backend/ folder: python test_playwright.py
"""
import asyncio
import sys
print("=== Playwright Connectivity Test ===")

async def main():
    try:
        from playwright.async_api import async_playwright
        print("Playwright import OK")
    except ImportError as e:
        print(f"Playwright import FAILED: {e}")
        return

    async with async_playwright() as p:
        print("\n--- Test 1: Headless Chromium ---")
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto("https://example.com", timeout=15000)
            title = await page.title()
            print(f"  headless=True  -> SUCCESS: '{title}'")
            await browser.close()
        except Exception as e:
            print(f"  headless=True  -> FAILED: {e}")

        print("\n--- Test 2: Headed Chromium (window should appear) ---")
        try:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto("https://example.com", timeout=15000)
            title = await page.title()
            print(f"  headless=False -> SUCCESS: '{title}'")
            await asyncio.sleep(2)
            await browser.close()
        except Exception as e:
            print(f"  headless=False -> FAILED: {e}")

        print("\n--- Test 3: With disable_security args ---")
        try:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-web-security", "--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = await browser.new_page()
            await page.goto("https://example.com", timeout=15000)
            title = await page.title()
            print(f"  with args      -> SUCCESS: '{title}'")
            await asyncio.sleep(2)
            await browser.close()
        except Exception as e:
            print(f"  with args      -> FAILED: {e}")

asyncio.run(main())
print("\n=== Done ===")