import asyncio
import json
import requests
import pandas as pd
from playwright.async_api import async_playwright

# رابط الـ API بتاعك
API_URL = "https://script.google.com/macros/s/AKfycbxA8qQ5j8AnfpxHEQzyEzFH-2jZzauPHpawKlt_ZaSLFgDHMtVleYh-892gYP8oW3ZM/exec"

def send_to_google_sheet(df):
    print("Sending data to Google Sheet via API...")
    # تحويل الداتا لـ JSON
    data_json = df.to_dict(orient='records')
    
    try:
        # إرسال البيانات للـ Web App
        response = requests.post(API_URL, json=data_json)
        result = response.json()
        if result.get("status") == "success":
            print(f"Success! Added {result.get('rows_added')} rows to 'Amazon_scraper'.")
        else:
            print(f"Error from Apps Script: {result.get('message')}")
    except Exception as e:
        print(f"Failed to send data: {e}")

async def scrape_price_chunk(page, base_url, min_price, max_price):
    all_items = []
    chunk_url = f"{base_url}&low-price={min_price}&high-price={max_price}"
    await page.goto(chunk_url, timeout=60000)
    
    page_num = 1
    while True:
        print(f"Scraping {min_price}-{max_price} EGP | Page: {page_num}")
        await page.wait_for_selector('.s-main-slot', timeout=15000)
        
        products = await page.query_selector_all('div[data-component-type="s-search-result"]')
        for product in products:
            try:
                # الاسم
                title_el = await product.query_selector('h2 a span')
                title = await title_el.inner_text() if title_el else "N/A"
                
                # السعر
                price_el = await product.query_selector('.a-price-whole')
                price = await price_el.inner_text() if price_el else "0"
                
                # رابط المنتج
                link_el = await product.query_selector('h2 a')
                link = "https://www.amazon.eg" + await link_el.get_attribute('href') if link_el else "N/A"
                
                # رابط الصورة (الجديد)
                img_el = await product.query_selector('img.s-image')
                img_src = await img_el.get_attribute('src') if img_el else "N/A"
                
                all_items.append({
                    "Title": title, 
                    "Price": price.replace(',', ''), 
                    "Product_Link": link,
                    "Image_Link": img_src
                })
            except Exception as e:
                continue
                
        # الانتقال للصفحة التالية
        next_button = await page.query_selector('.s-pagination-next:not(.s-pagination-disabled)')
        if next_button:
            await next_button.click()
            await page.wait_for_load_state('domcontentloaded')
            page_num += 1
            await asyncio.sleep(2)
        else:
            break
            
    return all_items

async def main():
    # رابط قسم ماكينات القهوة
    BASE_URL = "https://www.amazon.eg/s?rh=n%3A21864088031&fs=true" 
    
    # الفلاتر لتخطي حد الـ 1000 منتج
    price_ranges = [(0, 1000), (1000, 3000), (3000, 7000), (7000, 15000), (15000, 50000)]
    
    final_data = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for min_p, max_p in price_ranges:
            chunk_data = await scrape_price_chunk(page, BASE_URL, min_p, max_p)
            final_data.extend(chunk_data)
            
        await browser.close()
    
    # تنظيف وإرسال البيانات
    if final_data:
        df = pd.DataFrame(final_data)
        df.drop_duplicates(subset=['Product_Link'], inplace=True) 
        print(f"Total Unique Items Scraped: {len(df)}")
        send_to_google_sheet(df)
    else:
        print("No data scraped.")

if __name__ == "__main__":
    asyncio.run(main())