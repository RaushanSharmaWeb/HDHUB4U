import requests
from bs4 import BeautifulSoup
import os
import json

# --- CONFIGURATION ---
FIREBASE_URL = os.environ.get("FIREBASE_URL")
# URL check kar lena, agar change hua ho to update karein
SITE_URL = "https://new3.hdhub4u.fo/" 

def simple_scrape():
    print("🚀 Connecting to HDHub4u (Simple Mode)...")

    # --- 1. HEADERS (Bhes badalna) ---
    # Hum website ko bolenge ki hum ek 'Chrome Browser' hain, Python script nahi.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://google.com"
    }

    try:
        # --- 2. REQUEST ---
        # Note: verify=False SSL errors ko ignore karne ke liye hai (kabhi kabhi zarurat padti hai)
        response = requests.get(SITE_URL, headers=headers, timeout=15)

        print(f"📡 Status Code: {response.status_code}")

        # Agar 403 (Forbidden) ya 503 (Service Unavailable) aaye, to matlab Cloudflare ne roka hai
        if response.status_code in [403, 503]:
            print("❌ Result: Cloudflare Active Hai. Simple request block ho gayi.")
            return

        if response.status_code != 200:
            print(f"❌ Failed to connect. Reason: {response.reason}")
            return

        print("✅ SUCCESS! Website direct access ho gayi.")

        # --- 3. PARSING (Jo screenshot me dekha tha) ---
        soup = BeautifulSoup(response.text, 'html.parser')

        # 'thumb' class wali list dhundho
        all_movies = soup.find_all('li', class_='thumb')
        
        if not all_movies:
            print("⚠️ Website khuli par 'thumb' class nahi mili. HTML print kar raha hu check karne ke liye:")
            print(response.text[:500]) # Shuru ke 500 akshar dikhao
            return

        print(f"\n--- 🎬 Found {len(all_movies)} Movies ---")
        
        count = 0
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

                    # --- 4. FIREBASE UPLOAD ---
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
                    if count >= 5: 
                        break

            except Exception as e:
                print(f"⚠️ Error parsing item: {e}")
                continue

    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    simple_scrape()
