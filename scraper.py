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

# A simple dictionary to translate FA codes to nice names
comp_names = {
    "YMD2": "York League Div 2",
    "CC": "West Riding County Cup",
    "YFA": "York League Cup"
}

for row in all_rows:
    # 1. Grab the Competition Cell (the very first one in the row)
    comp_cell = row.find('td', class_='bold')
    
    # 2. Grab the other cells using the classes we found
    date_cell = row.find('span', class_='spacer-right')
    home_cell = row.find('td', class_='home-team')
    score_cell = row.find('td', class_='score')
    away_cell = row.find('td', class_='road-team')

    if home_cell and away_cell:
        # Get the raw code (YMD2, CC, etc.)
        raw_comp = comp_cell.text.strip() if comp_cell else "Unknown"
        
        # Translate it if it's in our dictionary, otherwise use the raw code
        friendly_comp = comp_names.get(raw_comp, raw_comp)

        match_data = {
            "date": date_cell.text.strip() if date_cell else "TBC",
            "competition": friendly_comp,
            "home_team": home_cell.text.strip(),
            "away_team": away_cell.text.strip(),
            "score": score_cell.text.strip().split('\n')[0].strip() if score_cell else "VS"
        }
        
        try:
            supabase.table("matches").insert(match_data).execute()
            print(f"Synced {friendly_comp}: {match_data['home_team']} vs {match_data['away_team']}")
        except Exception as e:
            print(f"Error: {e}")

print("Sync Complete!")