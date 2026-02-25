import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Setup & Credentials
load_dotenv()
url_supabase: str = os.environ.get("SUPABASE_URL")
key_supabase: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url_supabase, key_supabase)

def scrape_and_push_table():
    # --- SCRAPING PART ---
    target_url = "https://fulltime.thefa.com/table.html?selectedSeason=9631242&selectedDivision=368866241"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(target_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    table_container = soup.find('div', {'id': 'fixed-col-table-container'})
    rows = table_container.find('tbody').find_all('tr')
    
    formatted_data = []

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 10:
            continue
            
        # We prepare the data exactly how our Supabase table expects it
        team_entry = {
            "position": int(cells[0].text.strip()),
            "team_name": cells[1].text.strip(),
            "played": int(cells[2].text.strip()),
            "home_w": int(cells[3].text.strip()),
            "home_d": int(cells[4].text.strip()),
            "home_l": int(cells[5].text.strip()),
            "home_f": int(cells[6].text.strip()),
            "home_a": int(cells[7].text.strip()),
            "away_w": int(cells[8].text.strip()),
            "away_d": int(cells[9].text.strip()),
            "away_l": int(cells[10].text.strip()),
            "away_f": int(cells[11].text.strip()),
            "away_a": int(cells[12].text.strip()),
            "overall_w": int(cells[13].text.strip()),
            "overall_d": int(cells[14].text.strip()),
            "overall_l": int(cells[15].text.strip()),
            "overall_f": int(cells[16].text.strip()),
            "overall_a": int(cells[17].text.strip()),
            "goal_difference": int(cells[18].text.strip()),
            "points": int(cells[19].text.strip()),
        }
        formatted_data.append(team_entry)

    # --- SUPABASE PUSH PART ---
    print(f"Syncing {len(formatted_data)} teams to Supabase...")
    
    # .upsert() handles updating existing teams or adding new ones
    # We use 'team_name' as the unique key to identify rows
    response = supabase.table("league_table").upsert(formatted_data, on_conflict="team_name").execute()
    
    print("Success! League table updated.")

if __name__ == "__main__":
    scrape_and_push_table()