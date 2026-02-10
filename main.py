import gspread
import pandas as pd
from fastmcp import FastMCP
from google.oauth2.service_account import Credentials
from datetime import datetime

# Initialize FastMCP
mcp = FastMCP("SkylarkCoordinator")

# --- CONFIGURATION ---
SPREADSHEET_ID = "1nLCL9cn1jAwXneKYuqnCUx9iVKBWLGM1VZFuDdbpDLc" 
SERVICE_ACCOUNT_FILE = "service_account.json"

def get_sheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    return gspread.authorize(creds)

# --- HELPER TOOLS ---

@mcp.tool()
def get_all_data():
    """Fetches current data from all 3 sheets: pilot_roster, drone_fleet, and missions."""
    client = get_sheet_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    
    data = {
        "pilots": pd.DataFrame(sh.worksheet("pilot_roster").get_all_records()).to_dict(orient="records"),
        "drones": pd.DataFrame(sh.worksheet("drone_fleet").get_all_records()).to_dict(orient="records"),
        "missions": pd.DataFrame(sh.worksheet("missions").get_all_records()).to_dict(orient="records")
    }
    return data

@mcp.tool()
def update_pilot_status(pilot_id: str, new_status: str):
    """Updates a pilot's status (Available/On Leave/Assigned) in Google Sheets."""
    client = get_sheet_client()
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("pilot_roster")
    
    cell = sheet.find(pilot_id)
    # Status is column 6 (F) in our schema
    sheet.update_cell(cell.row, 6, new_status)
    return f"Success: Pilot {pilot_id} status updated to {new_status}."

@mcp.tool()
def detect_conflicts():
    """Analyzes the data to find scheduling, skill, or maintenance conflicts."""
    data = get_all_data()
    pilots = pd.DataFrame(data['pilots'])
    drones = pd.DataFrame(data['drones'])
    missions = pd.DataFrame(data['missions'])
    
    conflicts = []
    
    # 1. Maintenance Check
    maint_drones = drones[drones['status'] == 'Maintenance']
    for _, d in maint_drones.iterrows():
        if d['current_assignment'] != '–':
            conflicts.append(f"CRITICAL: Drone {d['drone_id']} is in Maintenance but assigned to {d['current_assignment']}.")

    # 2. Location Mismatch (Simplified logic)
    for _, m in missions.iterrows():
        # Check assigned pilot location
        pilot = pilots[pilots['current_assignment'] == m['project_id']]
        if not pilot.empty:
            p = pilot.iloc[0]
            if p['location'] != m['location']:
                conflicts.append(f"WARNING: Pilot {p['name']} is in {p['location']} but mission {m['project_id']} is in {m['location']}.")
            
            # 3. Skill Mismatch
            if m['required_skills'] not in p['skills']:
                 conflicts.append(f"SKILL GAP: {p['name']} lacks {m['required_skills']} for mission {m['project_id']}.")

    return conflicts if conflicts else ["No conflicts detected!"]

if __name__ == "__main__":
    mcp.run()