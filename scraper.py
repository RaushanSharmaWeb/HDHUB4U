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

def get_existing_movies():
    print("📂 Checking existing movies...")
    if not FIREBASE_URL: return []
    try:
        res = requests.get(f"{FIREBASE_URL}/movies.json?shallow=true")
        if res.status_code == 200 and res.json():
            return list(res.json().keys())
        return []
    except Exception:
        return []

def get_full_details(details_url):
    print(f"   └── 🕵️ Visiting: {details_url}...")
    
    payload = { 'api_key': SCRAPER_API_KEY, 'url': details_url, 'keep_headers': 'true' }
    
    details = { 
        "rating": "N/A", "plot": "No synopsis.", "links": [],
        "language": "Hindi", "quality": "HD", "category": "Bollywood", "size": "N/A"
    }

    try:
        res = requests.get('http://api.scraperapi.com', params=payload)
        if res.status_code != 200: return details
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # --- 1. METADATA ---
        target_box = soup.find('div', {'class': 'NFQFxe CQKTwc mod'})
        if target_box:
            text_content = target_box.get_text(separator='|')
            parts = text_content.split('|')
            for part in parts:
                part = part.strip()
                if "Language" in part: details["language"] = part.replace("Language", "").replace(":", "").strip()
                elif "Quality" in part: details["quality"] = part.replace("Quality", "").replace(":", "").strip()
                elif "Size" in part: details["size"] = part.replace("Size", "").replace(":", "").strip()
                elif "Genres" in part: details["category"] = part.replace("Genres", "").replace(":", "").strip()

        # Rating & Plot
        rating_match = re.search(r'IMDb Rating[:\s]+(\d\.\d)', soup.get_text())
        if rating_match: details["rating"] = rating_match.group(1)

        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 60 and "Download" not in text:
                details["plot"] = text
                break

        # --- 🔥 2. LINKS (SMART FILTER) 🔥 ---
        main_body = soup.find('div', class_='page-body')
        
        if main_body:
            print("      (🎯 'page-body' found! Filtering junk links...)")
            all_links = main_body.find_all('a')
            
            for a in all_links:
                txt = a.get_text().strip()
                href = a.get('href')
                
                # Check 1: Text bahut lamba nahi hona chahiye (Movie titles lambe hote hain)
                if len(txt) > 50:
                    continue 

                # Check 2: Text me '|' nahi hona chahiye (Titles me aksar pipe '|' hota hai)
                if "|" in txt:
                    continue

                # Check 3: Asli keywords hone chahiye
                if href and ("720p" in txt or "1080p" in txt or "480p" in txt or "Download" in txt):
                    if "trailer" not in txt.lower():
                        details["links"].append({ "name": txt, "url": href })
        else:
            print("      (⚠️ 'page-body' nahi mila)")
        
        # Duplicate Hatana (Set use karke)
        # Kabhi kabhi same link 2 baar aa jata hai
        unique_links = []
        seen_urls = set()
        for link in details["links"]:
            if link["url"] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link["url"])
        
        details["links"] = unique_links[:10] # Top 10 links
        return details

    except Exception as e:
        print(f"   ⚠️ Details Error: {e}")
        return details

def start_scraping():
    print("🚀 Connecting via ScraperAPI...")
    if not SCRAPER_API_KEY:
        print("❌ Error: SCRAPER_API_KEY missing!")
        return

    existing_ids = get_existing_movies()
    print(f"ℹ️ Database me {len(existing_ids)} movies hain.")

    payload = { 'api_key': SCRAPER_API_KEY, 'url': SITE_URL, 'keep_headers': 'true' }

    try:
        response = requests.get('http://api.scraperapi.com', params=payload)
        if response.status_code != 200:
            print(f"❌ Failed! Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        all_movies = soup.find_all('li', class_='thumb')
        if not all_movies: all_movies = soup.find_all('li', class_='post-item')

        print(f"\n--- 🎬 Found {len(all_movies)} Movies on Homepage ---")
        
        new_count = 0
        for movie in all_movies:
            try:
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

                        if movie_id in existing_ids:
                            print(f"⏩ Skipping: {title_clean} (Exists)")
                            continue

                        print(f"\n[{new_count+1}] NEW: {title_clean}")

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
                            print(f"   ✅ Saved! Valid Links: {len(full_data['links'])}")
                        
                        new_count += 1
                        if new_count >= 3: 
                            print("\n🛑 Limit reached.")
                            break
            except Exception as e:
                continue

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    start_scraping()
