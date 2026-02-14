import cloudscraper
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, db
import os

# --- 1. FIREBASE SETUP ---
# (Abhi ke liye hum sirf print karenge taaki error na aaye)
print("🤖 Bot Start ho gaya hai...")

# --- 2. SCRAPING START ---
scraper = cloudscraper.create_scraper()
url = "https://new3.hdhub4u.fo/" # Naya link check karte rahna

try:
    print(f"🌍 Connecting to {url}...")
    response = scraper.get(url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # HDHub4u structure (Change ho sakta hai, inspect karke dekhna padega)
        # Maan lete hain wahan movies <li> tag me class "post-item" ke sath hain
        movies = soup.find_all('li', class_='post-item') 
        
        if not movies:
            # Fallback: Agar upar wala fail ho jaye to <img> tags dhundo
            print("⚠️ Class nahi mili, Images check kar raha hu...")
            images = soup.find_all('img')
            for img in images[:5]:
                name = img.get('alt')
                if name and len(name) > 5:
                    print(f"🎬 Movie Found: {name}")
        else:
            for movie in movies[:5]:
                # Yahan hum title nikalne ki koshish karenge
                img = movie.find('img')
                if img:
                    print(f"🎬 Movie Found: {img.get('alt')}")
                    
    else:
        print(f"❌ Site nahi khuli. Status: {response.status_code}")

except Exception as e:
    print(f"❌ Error aaya: {e}")

print("✅ Bot ka kaam khatam.")
