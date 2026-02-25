import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Setup & Credentials
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

# Our handy dictionary for standard abbreviations
comp_names = {
    "YMD2": "York League Div 2",
    "YFA": "York League Cup",
    "CC": "County Cup"
}

print("--- Syncing Upcoming Fixtures ---")

page = 1
saved_count = 0

# --- PAGINATION LOOP ---
while True:
    print(f"\nScanning Page {page}...")
    
    # The dedicated URL for upcoming fixtures, using our {page} variable
    fixtures_url = f"https://fulltime.thefa.com/fixtures/{page}/100.html?selectedSeason=9631242&selectedFixtureGroupAgeGroup=0&previousSelectedFixtureGroupAgeGroup=&selectedFixtureGroupKey=1_419533493&previousSelectedFixtureGroupKey=1_419533493&selectedDateCode=all&selectedRelatedFixtureOption=3&selectedClub=&previousSelectedClub=&selectedTeam=&selectedFixtureDateStatus=&selectedFixtureStatus=0"
    
    res = requests.get(fixtures_url, headers=headers)
    soup = BeautifulSoup(res.content, "html.parser")

    # The Fixtures page uses traditional table rows (tr)
    all_rows = soup.find_all('tr')
    matches_found_on_page = 0

    for row in all_rows:
        # Target the specific table cells (td) using classes
        home_cell = row.find('td', class_=lambda c: c and 'home-team' in c)
        away_cell = row.find('td', class_=lambda c: c and 'road-team' in c)
        score_cell = row.find('td', class_='score')
        
        if home_cell and away_cell and score_cell:
            link_tag = home_cell.find('a', href=True)
            if not link_tag or 'id=' not in link_tag['href']: 
                continue
            
            matches_found_on_page += 1
            f_id = link_tag['href'].split('id=')[1].split('&')[0]
            
            h_name = home_cell.get_text(strip=True)
            a_name = away_cell.get_text(strip=True)
            score = score_cell.get_text(strip=True) # This will usually say "VS"
            
           # --- EXTRACT DATE & TIME ---
            date_str = "Unknown"
            # Find ALL cells with the class 'cell-divider'
            all_dividers = row.find_all('td', class_='cell-divider')
            
            # The date is always in the SECOND cell-divider (index 1)
            if len(all_dividers) >= 2:
                date_cell = all_dividers[1]
                date_spans = date_cell.find_all('span')
                if len(date_spans) >= 2:
                    # Joins the date and time, e.g., "28/02/26 14:00"
                    date_str = f"{date_spans[0].get_text(strip=True)} {date_spans[1].get_text(strip=True)}"

            # Extract Competition Logic
            # First, check the abbreviation in the very first column
            first_td = row.find('td')
            comp_abbr = first_td.get_text(strip=True) if first_td else "Unknown"
            
            # Then, look for explicit Cup names in the trailing cells 
            # (e.g., "York FA Cup Men's Junior (Sat)")
            all_dividers = row.find_all('td', class_='cell-divider')
            full_comp_name = ""
            if len(all_dividers) >= 3:
                full_comp_name = all_dividers[-1].get_text(strip=True)

            # Determine the final competition name
            if comp_abbr in comp_names:
                competition = comp_names[comp_abbr]
            elif full_comp_name and full_comp_name != "Unknown":
                competition = full_comp_name
            else:
                competition = comp_abbr
            
            # UPSERT into Supabase
            match_data = {
                "fixture_id": f_id,
                "competition": competition,
                "home_team": h_name,
                "away_team": a_name,
                "date": date_str,
                "score": score
            }
            
            try:
                supabase.table("matches").upsert(match_data).execute()
                saved_count += 1
                print(f"Fixture Saved: [{competition}] {h_name} {score} {a_name} ({date_str})")
            except Exception as e:
                print(f"Error saving match {f_id}: {e}")

    # If no games were found on this page, break the loop
    if matches_found_on_page == 0:
        print(f"No more fixtures found. Ending pagination.")
        break
        
    page += 1

print(f"\n--- FIXTURES SYNC COMPLETE: Saved {saved_count} matches ---")