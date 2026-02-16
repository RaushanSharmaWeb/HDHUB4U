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

def clean_plot_text(text):
    """
    Ye function kahani ko saaf karega (Garbage hatayega).
    """
    if not text: return None
    
    # 1. Shuruwat saaf karo (Storyline: ... -> ...)
    text = re.sub(r'^(DESCRIPTION|SYNOPSIS|PLOT|STORYLINE|STORY)[:\s\-]+', '', text, flags=re.IGNORECASE).strip()
    
    # 2. STOP WORDS: Jahan ye words dikhein, wahi BAS kar do (Cut kar do)
    stop_markers = [
        "Watch Online", "Download", "9xmovies", "world4free", "Khatrimaza", 
        "123Movies", "fmovies", "Gomovies", "300Mb", "Dual Audio", "Hindi Dubbed",
        "AMAZON PRIME", "NETFLIX", "G-Drive", "Direct Links", "Bolly4u"
    ]
    
    # Text ko lowercase me check karo markers ke liye
    text_lower = text.lower()
    
    cut_index = len(text) # Default: Pura text rakho
    
    for marker in stop_markers:
        marker_lower = marker.lower()
        if marker_lower in text_lower:
            # Sabse pehla jo garbage mile, wahi se kaat do
            idx = text_lower.find(marker_lower)
            if idx != -1 and idx < cut_index:
                cut_index = idx
    
    # Text ko kaat do
    final_text = text[:cut_index].strip()
            
    # Agar cut karne ke baad text bahut chhota bacha, to ignore karo
    if len(final_text) < 10:
        return None
        
    return final_text

def get_full_details(details_url):
    print(f"   └── 🕵️ Visiting: {details_url}...")
    
    payload = { 'api_key': SCRAPER_API_KEY, 'url': details_url, 'keep_headers': 'true' }
    
    details = { 
        "rating": "N/A", "plot": "No synopsis available.", "links": [],
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

        # --- 2. RATING ---
        rating_match = re.search(r'IMDb Rating[:\s]+(\d\.\d)', soup.get_text())
        if rating_match: details["rating"] = rating_match.group(1)

        # --- 3. SMART PLOT EXTRACTION (Header ke neeche wala) ---
        found_plot = None
        
        # Keywords jinke neeche kahani hoti hai
        plot_keywords = ["Storyline", "Synopsis", "Description", "Plot", "Story"]
        
        for keyword in plot_keywords:
            # Keyword dhundo (Case insensitive)
            # Hum 'strong', 'b', 'span', 'h3', 'h4' me dhundenge
            header = soup.find(['strong', 'b', 'span', 'h3', 'h4', 'p'], string=re.compile(keyword, re.IGNORECASE))
            
            if header:
                # HEADER MIL GAYA! (Jaise: "Storyline :")
                # Ab hum iske aage ya neeche ka text dhundenge.
                
                # Option A: Kya text usi line me aage likha hai? (Parent check)
                parent_text = header.parent.get_text().strip()
                cleaned_parent = clean_plot_text(parent_text)
                # Agar parent text me keyword hatane ke baad bhi 50 words bache hain, to wahi plot hai
                if cleaned_parent and len(cleaned_parent) > 50:
                    found_plot = cleaned_parent
                    break
                
                # Option B: Agar us line me nahi hai, to NEXT Paragraph (<p>) uthao
                # Ye tab kaam karega jab Storyline heading ho aur plot niche ho (Screenshot jaisa)
                next_elem = header.find_next('p')
                if next_elem:
                    next_text = next_elem.get_text().strip()
                    cleaned_next = clean_plot_text(next_text)
                    if cleaned_next and len(cleaned_next) > 20:
                        found_plot = cleaned_next
                        break

        # Fallback: Agar upar wala tareeka fail ho jaye, to Longest Paragraph uthao
        if not found_plot:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 60 and "Download" not in text and "Join" not in text:
                    cleaned = clean_plot_text(text)
                    if cleaned:
                        found_plot = cleaned
                        break

        if found_plot:
            details["plot"] = found_plot

        # --- 4. LINKS ---
        main_body = soup.find('div', class_='page-body')
        
        if main_body:
            junk_words = ["trailer", "telegram", "whatsapp", "facebook", "twitter", 
                          "login", "register", "dmca", "contact", "home", "page", 
                          "posted by", "unknown", "comment"]
            
            good_keywords = ["download", "watch", "link", "drive", "480p", "720p", "1080p", "4k", "2160p", "episode", "season", "zip", "file", "g-direct"]

            all_links = main_body.find_all('a')
            
            for a in all_links:
                txt = a.get_text().strip()
                href = a.get('href')
                txt_lower = txt.lower()

                if not href or not txt: continue
                if any(bad in txt_lower for bad in junk_words): continue
                if len(txt) > 80: continue 
                if len(txt) < 3: continue

                is_good_link = False
                if any(good in txt_lower for good in good_keywords): is_good_link = True
                elif a.get('style') and ("background" in a.get('style') or "color" in a.get('style')): is_good_link = True
                elif a.get('class') and any("btn" in c for c in a.get('class')): is_good_link = True

                if is_good_link or (len(txt) > 5 and len(txt) < 60):
                     details["links"].append({ "name": txt, "url": href })

        # Remove Duplicates
        unique_links = []
        seen_urls = set()
        for link in details["links"]:
            if link["url"] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link["url"])
        
        details["links"] = unique_links[:20]
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
                            print(f"   ✅ Saved! Plot Length: {len(full_data['plot'])}")
                        
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
