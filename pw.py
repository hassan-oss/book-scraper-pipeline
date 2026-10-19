


import os
from playwright.sync_api import sync_playwright
import requests

# 1. Base URL with on_conflict
SUPABASE_URL = "https://enpaoyytmshedndwssbx.supabase.co/rest/v1/books?on_conflict=title"

# 2. Read the key securely from environment variables (works locally and on GitHub Actions)
SUPABASE_KEY = os.environ.get("SUPABASE_KEY","eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVucGFveXl0bXNoZWRuZHdzc2J4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE5OTA2OTEsImV4cCI6MjEwNzU2NjY5MX0.Yt0dqdA2muGZHLYnMogPtXTumj6omJa2ydaeIA6J8uo")

# 2. Update HEADERS to include resolution=merge-duplicates
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}
def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True) 
        page = browser.new_page()
        
        print("Navigating to website...")
        page.goto("https://books.toscrape.com/")
        
        max_pages = 2  # Let's keep it to 2 pages for testing
        current_page = 1

        while current_page <= max_pages:
            print(f"Scraping page {current_page}...")
            
            page.wait_for_selector("article.product_pod")
            book_pods = page.query_selector_all("article.product_pod")
            
            for book in book_pods:
                title_element = book.query_selector("h3 a")
                title = title_element.get_attribute("title") if title_element else "N/A"
                
                price_element = book.query_selector(".price_color")
                price = price_element.inner_text() if price_element else "N/A"
                
                # 2. Package the scraped book into a dictionary
                book_payload = {
                    "title": title,
                    "price": price
                }
                
                # 3. Send it instantly to the cloud via API POST request!
                response = requests.post(SUPABASE_URL, json=book_payload, headers=HEADERS)
                
                # Accept both 201 (Created) and 204 (Updated/Merged via upsert)
                if response.status_code in [200,201, 204]:
                    print(f"Successfully synced: {title}")
                else:
                    print(f"Failed to upload {title}: Status {response.status_code} - {response.text}")
            
            next_button = page.query_selector("li.next a")
            if not next_button:
                print("No more pages found. Stopping.")
                break
                
            next_button.click()
            current_page += 1
            
        print("Done! All scraped data has been pushed to the cloud database.")
        browser.close()

if __name__ == "__main__":
    run()