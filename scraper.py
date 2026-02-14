import requests
from bs4 import BeautifulSoup
import os
import json
import re

# --- CONFIGURATION ---
FIREBASE_URL = os.environ.get("FIREBASE_URL")
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY") 
SITE_URL = "https://new3.hdhub4u.fo/"

def create_id(title):
    clean_title = re.sub(r'[^a-zA-Z0-9\s]', '', title)
    return clean_title.strip().replace(' ', '_').lower()

def get_full_details(details_url):
    print(f"   └── 🕵️ Visiting: {details_url}...")
    
    payload = { 'api_key': SCRAPER_API_KEY, 'url': details_url, 'keep_headers': 'true' }
    
    # Default khali data
    details = { 
        "rating": "N/A", "plot": "No synopsis.", "links": [],
        "language": "Hindi", "quality": "HD", "category": "Bollywood", "size": "N/A"
    }

    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        if res.status_code != 200: return details
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # --- 1. TARGETING EXACT CLASS NAME (Jaisa screenshot me hai) ---
        # Hum Python ko bolenge: Aisa div dhundo jiski class EXACT ye ho:
        target_box = soup.find('div', {'class': 'NFQFxe CQKTwc mod'})
        
        if target_box:
            print("      (🎯 Mil gaya! 'NFQFxe CQKTwc mod' se data nikal raha hu...)")
            text_content = target_box.get_text(separator=' | ')
            
            # Text ko todkar scan karenge
            parts = text_content.split('|')
            for part in parts:
                part = part.strip()
                if "Language" in part:
                    details["language"] = part.replace("Language", "").replace(":", "").strip()
                elif "Quality" in part or "Format" in part:
                    details["quality"] = part.replace("Quality", "").replace("Format", "").replace(":", "").strip()
                elif "Size" in part:
                    details["size"] = part.replace("Size", "").replace(":", "").strip()
                elif "Genres" in part or "Category" in part:
                    details["category"] = part.replace("Genres", "").replace("Category", "").replace(":", "").strip()
        
        else:
            # Fallback: Agar wo div nahi mila (kabhi kabhi Google structure alag hota hai)
            print("      (⚠️ Target div nahi mila, pure page me dhund raha hu...)")
            full_text = soup.get_text()
            
            # Simple Text Search
            lang = re.search(r'Language[:\s]+(.*?)\n', full_text)
            if lang: details["language"] = lang.group(1).strip()
            
            qual = re.search(r'Quality[:\s]+(.*?)\n', full_text)
            if qual: details["quality"] = qual.group(1).strip()

        # --- 2. RATING & PLOT ---
        # Screenshot 2 me dikh raha hai ki ye data Google reviews jaisa lag raha hai.
        # Fir bhi hum koshish karenge.
        rating_match = re.search(r'IMDb Rating[:\s]+(\d\.\d)', soup.get_text())
        if rating_match: details["rating"] = rating_match.group(1)

        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 60 and "Download" not in text:
                details["plot"] = text
                break

        # --- 3. LINKS (Screenshot 1 ke hisab se) ---
        # Screenshot 1 me link <figure> ke andar <a> tag me hai.
        # Lekin ye function DETAILS page ke liye hai.
        # Details page par links <a> tags me hote hain (480p, 720p...)
        all_links = soup.find_all('a')
        for a in all_links:
            txt = a.get_text().strip()
            href = a.get('href')
            if href and ("720p" in txt or "1080p" in txt or "480p" in txt):
                if "trailer" not in txt.lower():
                    details["links"].append({ "name": txt, "url": href })
        
        details["links"] = details["links"][:6]
        return details

    except Exception as e:
        print(f"   ⚠️ Details Error: {e}")
        return details

def start_scraping():
    print("🚀 Connecting via ScraperAPI...")
    if not SCRAPER_API_KEY:
        print("❌ Error: SCRAPER_API_KEY missing!")
        return

    payload = { 'api_key': SCRAPER_API_KEY, 'url': SITE_URL, 'keep_headers': 'true' }

    try:
        response = requests.get('http://api.scraperapi.com', params=payload)
        if response.status_code != 200:
            print(f"❌ Failed! Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Screenshot 1 Logic: <li class="thumb"> dhundo
        all_movies = soup.find_all('li', class_='thumb')
        
        print(f"\n--- 🎬 Found Total {len(all_movies)} Movies ---")
        
        count = 0
        for movie in all_movies:
            try:
                # Screenshot 1: <figure> ke andar <img> aur <a> hai
                figure = movie.find('figure')
                if figure:
                    img_tag = figure.find('img')
                    link_tag = figure.find('a')

                    if img_tag and link_tag:
                        full_title = img_tag.get('alt')
                        poster = img_tag.get('src')
                        details_page = link_tag.get('href')

                        if not full_title or not details_page: continue

                        title_clean = full_title.split('|')[0].strip()
                        movie_id = create_id(title_clean)

                        print(f"\n[{count+1}] Checking: {title_clean}")

                        # Andar jao
                        full_data = get_full_details(details_page)

                        if FIREBASE_URL:
                            movie_data = {
                                "id": movie_id,
                                "title": title_clean,
                                "poster": poster,
                                "rating": full_data["rating"],
                                "plot": full_data["plot"],
                                "quality": full_data["quality"], 
                                "language": full_data["language"],
                                "category": full_data["category"],
                                "size": full_data["size"], 
                                "links": full_data["links"],
                                "updatedAt": {".sv": "timestamp"}
                            }
                            
                            final_url = f"{FIREBASE_URL}/movies/{movie_id}.json"
                            requests.put(final_url, json=movie_data)
                            print(f"   ✅ Saved! Qual: {full_data['quality']}")
                        
                        count += 1
                        if count >= 3: 
                            print("\n🛑 Limit reached.")
                            break
            except Exception as e:
                continue

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    start_scraping()
