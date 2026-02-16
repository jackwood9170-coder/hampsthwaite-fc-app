import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Load your credentials from the .env file
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 2. Scrape the FA website
fa_url = "https://fulltime.thefa.com/displayTeam.html?divisionseason=419533493&teamID=804057539"
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(fa_url, headers=headers)
soup = BeautifulSoup(response.content, "html.parser")

all_rows = soup.find_all('tr')

print(f"--- Syncing Hampsthwaite FC Data to Supabase ---")

for row in all_rows:
    row_text = row.text.strip()
    
    # Filter for match rows only (ignoring summary rows)
    if "Hampsthwaite" in row_text and "Overall" not in row_text and "Home" not in row_text:
        cells = row.find_all('td')
        
        if len(cells) >= 4:
            # Prepare the data object
            match_data = {
                "date": cells[0].text.strip(),
                "home_team": cells[2].text.strip(),
                "away_team": cells[4].text.strip()
            }
            
            # 3. Push to Supabase 'matches' table
            try:
                data, count = supabase.table("matches").insert(match_data).execute()
                print(f"Saved: {match_data['home_team']} vs {match_data['away_team']}")
            except Exception as e:
                print(f"Error saving row: {e}")

print("Sync Complete!")