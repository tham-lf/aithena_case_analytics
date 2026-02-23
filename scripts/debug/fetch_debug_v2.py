import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+27?ref=sg-sc"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"Navigating to {url}...")
        await page.goto(url)
        
        # Wait for something significant.
        # If we don't know the class, wait for specific text we expect like "Decision Date"
        try:
            # Try waiting for a common legal term or the citation year
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000) # Force wait 5s
            
            content = await page.content()
            text = await page.inner_text("body")
            
            print("--- Page Text Sample (First 500 chars) ---")
            print(text[:500])
            print("------------------------------------------")
            
            with open("debug_case_v2.html", "w", encoding="utf-8") as f:
                f.write(content)
                
            if "Decision Date" in text:
                print("SUCCESS: Found 'Decision Date' in text.")
            else:
                print("FAILURE: 'Decision Date' not found in rendered text.")
                
        except Exception as e:
            print(f"Error during wait/extraction: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
