import os
import re
import asyncio
from playwright.async_api import async_playwright
from supabase import create_client, Client

# Supabase Credentials from Environment Variables
SUPABASE_URL = "https://enpaoyytmshedndwssbx.supabase.co"  # <--- Replace with your actual Supabase URL
SUPABASE_KEY = os.environ.get("SUPABASE_KEY","eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVucGFveXl0bXNoZWRuZHdzc2J4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE5OTA2OTEsImV4cCI6MjEwNzU2NjY5MX0.Yt0dqdA2muGZHLYnMogPtXTumj6omJa2ydaeIA6J8uo")

if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is not set!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Word-to-number mapping for ratings
RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5
}

async def scrape_all_books():
    async with async_playwright() as p:
        # Launch Chromium in headless mode for GitHub Actions compatibility
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        base_url = "http://books.toscrape.com/catalogue/page-1.html"
        current_url = base_url
        all_books = []
        page_num = 1

        print("Starting multi-page scraping process...")

        while current_url:
            print(f"Scraping Page {page_num}: {current_url}")
            await page.goto(current_url)
            await page.wait_for_selector("article.product_pod")

            products = await page.query_selector_all("article.product_pod")

            for product in products:
                # 1. Title
                title_el = await product.query_selector("h3 a")
                title = await title_el.get_attribute("title") if title_el else ""

                # 2. Price
                price_el = await product.query_selector(".price_color")
                price_text = await price_el.inner_text() if price_el else "0"
                # Strip currency symbol
                price = float(re.sub(r"[^\d.]", "", price_text)) if price_text else 0.0

                # 3. Availability / Stock Status
                stock_el = await product.query_selector(".instock.availability")
                stock_text = await stock_el.inner_text() if stock_el else ""
                in_stock = "In stock" in stock_text

                # 4. Rating
                rating_el = await product.query_selector("p.star-rating")
                rating = 0
                if rating_el:
                    classes = await rating_el.get_attribute("class")
                    for word, val in RATING_MAP.items():
                        if word in classes:
                            rating = val
                            break

                # 5. Cover Image URL
                img_el = await product.query_selector(".image_container img")
                img_src = await img_el.get_attribute("src") if img_el else ""
                # Clean up relative URL path
                image_url = "http://books.toscrape.com/" + img_src.replace("../", "") if img_src else ""

                all_books.append({
                    "title": title,
                    "price": price,
                    "in_stock": in_stock,
                    "rating": rating,
                    "image_url": image_url
                })

            # Check for Next Page button
            next_button = await page.query_selector("li.next a")
            if next_button:
                next_href = await next_button.get_attribute("href")
                # Construct full URL for next page
                if "catalogue/" in next_href:
                    current_url = f"http://books.toscrape.com/{next_href}"
                else:
                    current_url = f"http://books.toscrape.com/catalogue/{next_href}"
                page_num += 1
            else:
                current_url = None

        await browser.close()
        print(f"Scraping complete! Total books scraped across all pages: {len(all_books)}")

        # Sync to Supabase in batches of 100
        print("Syncing data to Supabase...")
        batch_size = 100
        for i in range(0, len(all_books), batch_size):
            batch = all_books[i:i + batch_size]
            # Upsert using 'title' as unique constraint key
            supabase.table("books").upsert(batch, on_conflict="title").execute()

        print("Successfully synced all books to Supabase database!")

if __name__ == "__main__":
    asyncio.run(scrape_all_books())