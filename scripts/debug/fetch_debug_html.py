import sys
import os
# Add project root to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


import asyncio
from src.scraper import fetch_case_html

async def main():
    url = "https://www.lawnet.com/openlaw/cases/citation/[2026]+SGHC+27?ref=sg-sc"
    html = await fetch_case_html(url)
    with open("debug_case.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML saved to debug_case.html")

if __name__ == "__main__":
    asyncio.run(main())
