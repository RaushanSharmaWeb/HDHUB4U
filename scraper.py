import requests
from bs4 import BeautifulSoup
import os
import json

# --- CONFIGURATION ---
FIREBASE_URL = os.environ.get("FIREBASE_URL")
# Yahan hum wo Key uthayenge jo aapne GitHub Secrets me dali hai
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") 
SITE_URL = "https://new3.hdhub4u.fo/"

def start_scraping():
    print("🚀 Connecting via ScraperAPI (Bypassing Cloudflare)...")

    # Agar Secret set nahi hai, to error dikhao
    if not SCRAPER_API_KEY:
        print("❌ Error: SCRAPER_API_KEY nahi mili! GitHub Secrets check karo.")
        return

    # --- 1. PROXY REQUEST (Aapka wala code) ---
    payload = { 
        'api_key': SCRAPER_API_KEY, 
        'url': SITE_URL,
        'keep_headers': 'true' # Original headers bhejne ke liye
    }

    try:
        # Request ScraperAPI ko bhej rahe hain
        response = requests.get('http://api.scraperapi.com', params=payload)
        
        if response.status_code != 200:
            print(f"❌ Failed! Status: {response.status_code}")
            print("Reason:", response.text)
            return

        print("✅ SUCCESS! Cloudflare Bypassed. HTML mil gaya.")

        # --- 2. PARSING (Movie dhundho) ---
        soup = BeautifulSoup(response.text, 'html.parser')

        # 'thumb' class wali list dhundho (Screenshot logic)
        all_movies = soup.find_all('li', class_='thumb')
        
        count = 0
        print(f"\n--- 🎬 Found {len(all_movies)} Movies ---")

        for movie in all_movies:
            try:
                img_tag = movie.find('img')
                link_tag = movie.find('a')

                if img_tag and link_tag:
                    full_title = img_tag.get('alt')
                    poster = img_tag.get('src')
                    link = link_tag.get('href')

                    # Title Clean karo
                    if full_title:
                        title = full_title.split('|')[0].strip()
                    else:
                        title = "Unknown Movie"

                    print(f"Found: {title}")

                    # --- 3. FIREBASE UPLOAD ---
                    if FIREBASE_URL:
                        movie_data = {
                            "title": title,
                            "poster": poster,
                            "download_page": link,
                            "quality": "HD",
                            "language": "Hindi",
                            "addedAt": {".sv": "timestamp"}
                        }
                        
                        final_url = f"{FIREBASE_URL}/movies.json"
                        requests.post(final_url, json=movie_data)
                        print("   └── ✅ Uploaded!")
                    
                    count += 1
                    if count >= 5: # Sirf Top 5 movies
                        break

            except Exception as e:
                continue

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    start_scraping()
