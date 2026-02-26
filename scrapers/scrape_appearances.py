import os
import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client

# 1. Setup & Credentials
load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

def scrape_match_appearances(f_id, home_name, away_name):
    detail_url = f"https://fulltime.thefa.com/displayFixture.html?id={f_id}"
    print(f"Fetching data for Fixture: {f_id}...")
    
    try:
        res = requests.get(detail_url, headers=headers)
        soup = BeautifulSoup(res.content, "html.parser")

        grid = soup.find("div", class_="fixture-lineup-statistics")
        if not grid:
            print("No lineup data found for this match.")
            return 0 

        player_count = 0
        
        # We process Home team first, then Away team
        sections = [
            {"class": "home-team", "actual_name": home_name},
            {"class": "road-team", "actual_name": away_name}
        ]

        for section in sections:
            team_div = grid.find("div", class_=lambda x: x and section["class"] in x)
            if not team_div: continue
            
            for group in ["starters", "subs"]:
                container = team_div.find("div", class_=group)
                if not container: continue
                
                players = container.find_all("div", class_="player")
                for p in players:
                    name_tag = p.find("p")
                    if not name_tag: continue
                    p_name = name_tag.get_text(strip=True)
                    
                    # Trackers for our stats
                    goal_mins = []
                    unknown_goals = 0  # <--- NEW TRACKER
                    s_on = []
                    s_off = []
                    yellows = 0
                    reds = 0
                    
                    stat_containers = p.find_all("div", class_="flex left middle")
                    for stat in stat_containers:
                        icon = stat.find("i")
                        if not icon: continue
                        
                        classes = icon.get("class", [])
                        raw_text = stat.text.strip()
                        
                        # Keep only numbers and commas
                        minute_val = re.sub(r'[^0-9,]', '', raw_text)
                        
                        # --- UPDATED GOAL & SUB LOGIC ---
                        if "ball" in classes:
                            if minute_val:
                                goal_mins.extend(minute_val.split(","))
                            else:
                                unknown_goals += 1 # Scored, but no minute given!
                                
                        elif "subson" in classes and minute_val:
                            s_on.extend(minute_val.split(","))
                            
                        elif "subsoff" in classes and minute_val:
                            s_off.extend(minute_val.split(","))
                                
                        # Handle Cards
                        if "yellow-card" in classes or "yellowcard" in classes:
                            yellows += 1
                        if "red-card" in classes or "redcard" in classes:
                            reds += 1

                    appearance_data = {
                        "fixture_id": f_id,
                        "player_name": p_name,
                        "team_name": section["actual_name"],
                        "is_starter": (group == "starters"),
                        "goals": len(goal_mins) + unknown_goals, # Combine known and unknown goals!
                        "goal_minutes": ", ".join(goal_mins) if goal_mins else None,
                        "sub_on_minutes": ", ".join(s_on) if s_on else None,
                        "sub_off_minutes": ", ".join(s_off) if s_off else None,
                        "yellow_cards": yellows,
                        "red_cards": reds
                    }

                    supabase.table("appearances").upsert(appearance_data).execute()
                    player_count += 1

        return player_count

    except Exception as e:
        print(f"      !!! Error on {f_id}: {e}")
        return 0

# --- MAIN ENGINE: AUTOMATED APPEARANCE SYNC ---
print("\n--- Syncing Player Appearances ---")

try:
    # 1. Get all matches that are FINISHED
    matches_res = supabase.table("matches").select("fixture_id, home_team, away_team, score").execute()
    
    finished_matches = [
        m for m in matches_res.data 
        if m['score'] 
        and "VS" not in m['score'] 
        and "P - P" not in m['score']
        and "P-P" not in m['score']
        and "Postponed" not in m['score']
    ]
    
    print(f"Found {len(finished_matches)} finished matches. Checking which ones need player stats...")
    
    saved_count = 0
    
    # 2. Loop through and check each match individually (Bypasses the 1,000 row limit!)
    for match in finished_matches:
        f_id = str(match['fixture_id'])
        h_name = match['home_team']
        a_name = match['away_team']
        
        # Ask Supabase: Do we have ANY players for this specific fixture_id?
        # .limit(1) makes this query lightning fast
        check_res = supabase.table("appearances").select("fixture_id").eq("fixture_id", f_id).limit(1).execute()
        
        # If the list is empty (0 players found), we need to scrape it!
        if len(check_res.data) == 0:
            print(f"Missing stats for: {h_name} vs {a_name}. Scraping...")
            players_saved = scrape_match_appearances(f_id, h_name, a_name)
            print(f"  -> Saved {players_saved} players.")
            saved_count += 1
            
            # Polite scraping delay number of seconds between calls
            import time
            time.sleep(2)
            
    if saved_count == 0:
        print("All matches already have player stats. Nothing new to scrape!")
        
    print("\n--- APPEARANCE SYNC COMPLETE ---")

except Exception as e:
    print(f"Error in automated sync engine: {e}")