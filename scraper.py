import requests
from bs4 import BeautifulSoup
import os
import json
import re # ID banane ke liye

# --- CONFIGURATION ---
FIREBASE_URL = os.environ.get("FIREBASE_URL")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") 
SITE_URL = "https://new3.hdhub4u.fo/"

def create_id(title):
    """
    Movie Title se unique ID banata hai.
    Example: "Tiger 3: Action" -> "tiger_3_action"
    """
    # Sirf A-Z aur 0-9 rakho, baaki sab hata do
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    # Spaces ko underscore (_) bana do aur lowercase kar do
    return clean_title.strip().replace(' ', '_').lower()

def get_full_details(details_url):
    print(f"   └── 🕵️ Visiting: {details_url}...")
    
    payload = { 'api_key': SCRAPER_API_KEY, 'url': details_url, 'keep_headers': 'true' }
    
    details = { "rating": "N/A", "plot": "No synopsis.", "links": [] }

    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        if res.status_code != 200: return details
            
        soup = BeautifulSoup(res.text, 'html.parser')
        text_content = soup.get_text()

        # Rating
        rating_match = re.search(r'IMDb Rating[:\s]+(\d\.\d)', text_content)
        if rating_match: details["rating"] = rating_match.group(1)

        # Plot
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50 and "Download" not in text:
                details["plot"] = text
                break

        # Links
        all_links = soup.find_all('a')
        for a in all_links:
            txt = a.get_text().strip()
            href = a.get('href')
            if href and ("720p" in txt or "1080p" in txt or "480p" in txt):
                if "trailer" not in txt.lower():
                    details["links"].append({ "name": txt, "url": href })
        
        details["links"] = details["links"][:6]
        return details

    except Exception:
        return details

def start_scraping():
    print("🚀 Connecting via ScraperAPI...")

    if not SCRAPER_API_KEY:
        print("❌ Error: SCRAPER_API_KEY nahi mili!")
        return

    payload = { 'api_key': SCRAPER_API_KEY, 'url': SITE_URL, 'keep_headers': 'true' }

    try:
        response = requests.get('http://api.scraperapi.com', params=payload)
        if response.status_code != 200:
            print(f"❌ Failed! Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        all_movies = soup.find_all('li', class_='thumb')
        
        print(f"\n--- 🎬 Found Total {len(all_movies)} Movies ---")
        
        count = 0
        for movie in all_movies:
            try:
                img_tag = movie.find('img')
                link_tag = movie.find('a')

                if img_tag and link_tag:
                    full_title = img_tag.get('alt')
                    poster = img_tag.get('src')
                    details_page = link_tag.get('href')

                    if not full_title or not details_page: continue

                    title_clean = full_title.split('|')[0].strip()
                    
                    # 🔥 UNIQUE ID CREATE KARO 🔥
                    movie_id = create_id(title_clean)

                    print(f"\n[{count+1}] Checking: {title_clean} (ID: {movie_id})")

                    # --- 2. ANDAR JAKAR DATA LAO ---
                    full_data = get_full_details(details_page)

                    # --- 3. FIREBASE UPLOAD (PUT Request) ---
                    if FIREBASE_URL:
                        movie_data = {
                            "id": movie_id, # ID bhi save kar lete hain
                            "title": title_clean,
                            "poster": poster,
                            "rating": full_data["rating"],
                            "plot": full_data["plot"],
                            "quality": "HD",
                            "category": "Bollywood",
                            "links": full_data["links"],
                            "updatedAt": {".sv": "timestamp"} # Pata chalega kab update hui
                        }
                        
                        # 🔥 YAHAN MAGIC HAI: POST ki jagah PUT 🔥
                        # Hum URL me movie_id laga rahe hain.
                        # Agar ye ID pehle se hai, to bas data update hoga. Duplicate nahi banega.
                        final_url = f"{FIREBASE_URL}/movies/{movie_id}.json"
                        
                        requests.put(final_url, json=movie_data)
                        print(f"   ✅ Data Updated/Saved successfully!")
                    
                    count += 1
                    if count >= 3: 
                        print("\n🛑 Stopping to save API credits.")
                        break

            except Exception as e:
                print(f"⚠️ Error: {e}")
                continue

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    start_scraping()
