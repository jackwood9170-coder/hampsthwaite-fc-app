import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Setup & Credentials
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

comp_names = {
    "YMD2": "York League Div 2",
    "YFA": "York League Cup"
}

print("--- Syncing League Results ---")

page = 1
saved_count = 0

# --- PAGINATION LOOP ---
while True:
    print(f"\nScanning Page {page}...")
    
    # Added selectedDateCode=all to get the whole season, and Option=3 for Cup games
    results_url = f"https://fulltime.thefa.com/results/{page}/100.html?selectedSeason=9631242&selectedFixtureGroupAgeGroup=0&previousSelectedFixtureGroupAgeGroup=&selectedFixtureGroupKey=1_419533493&previousSelectedFixtureGroupKey=1_419533493&selectedDateCode=all&selectedRelatedFixtureOption=3&selectedClub=&previousSelectedClub=&selectedTeam="
    
    res = requests.get(results_url, headers=headers)
    soup = BeautifulSoup(res.content, "html.parser")

    # The FA Results page anchors every match around a "score-col" div
    score_columns = soup.find_all("div", class_="score-col")
    
    # If we find 0 score columns on a page, we have reached the end!
    if not score_columns:
        print(f"No more matches found. Ending pagination.")
        break

    for score_col in score_columns:
        row = score_col.parent
        
        # 1. Get Fixture ID from the expand link
        expand_link = row.find("a", href=lambda href: href and "expandFixtureID=" in href)
        if not expand_link: 
            continue
            
        f_id = expand_link['href'].split('expandFixtureID=')[1].split('#')[0] 
        
        # 2. Extract Data Columns
        home_col = row.find("div", class_="home-team-col")
        away_col = row.find("div", class_="road-team-col")
        date_col = row.find("div", class_="datetime-col")
        type_col = row.find("div", class_="type-col")
        fg_col = row.find("div", class_="fg-col")
        
        if home_col and away_col:
            h_name_tag = home_col.find("div", class_="team-name")
            a_name_tag = away_col.find("div", class_="team-name")
            
            h_name = h_name_tag.get_text(strip=True) if h_name_tag else "Unknown"
            a_name = a_name_tag.get_text(strip=True) if a_name_tag else "Unknown"
            score = score_col.get_text(strip=True)
            
            date_span = date_col.find("span") if date_col else None
            date_str = date_span.get_text(strip=True) if date_span else "Unknown"
            
            # 3. Handle the Custom Competition Logic
            competition = "League/Cup"
            if type_col:
                comp_link = type_col.find("a")
                if comp_link:
                    comp_abbr = comp_link.get_text(strip=True)
                    
                    if comp_abbr == "CC":
                        # Look inside the fg-col for the <p class="smaller"> tag
                        fg_p = fg_col.find("p", class_="smaller") if fg_col else None
                        if fg_p:
                            competition = fg_p.get_text(strip=True)
                        else:
                            competition = "County Cup"
                    else:
                        # Use our dictionary, defaulting to the abbreviation if not found
                        competition = comp_names.get(comp_abbr, comp_abbr)
            
            # 4. Save to Supabase (UPSERT handles new rows AND updating existing ones)
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
                print(f"Result Saved: [{competition}] {h_name} {score} {a_name}")
            except Exception as e:
                print(f"Error saving match {f_id}: {e}")

    # Move to the next page!
    page += 1

print(f"\n--- RESULTS SYNC COMPLETE: Saved {saved_count} matches ---")