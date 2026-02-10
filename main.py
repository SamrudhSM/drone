import gspread
import pandas as pd
from fastmcp import FastMCP
from google.oauth2.service_account import Credentials

# Initialize the FastMCP Server
mcp = FastMCP("SkylarkCoordinator")

# --- VERIFIED CONFIGURATION ---
SPREADSHEET_ID = "1nLCL9cn1jAwXneKYuqnCUx9iVKBWLGM1VZFuDdbpDLc" #late add these are env 
SERVICE_ACCOUNT_FILE = "service_account.json"

def get_sheet_client():
    """Authenticates with Google Sheets using the service account."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    return gspread.authorize(creds)

@mcp.tool()
def get_all_data():
    """Fetches all current data for Pilots, Drones, and Missions."""
    client = get_sheet_client()
    sh = client.open_by_key(SPREADSHEET_ID)
    
    return {
        "pilots": pd.DataFrame(sh.worksheet("pilot_roster").get_all_records()).to_dict(orient="records"),
        "drones": pd.DataFrame(sh.worksheet("drone_fleet").get_all_records()).to_dict(orient="records"),
        "missions": pd.DataFrame(sh.worksheet("missions").get_all_records()).to_dict(orient="records")
    }

@mcp.tool()
def update_pilot_status(pilot_id: str, new_status: str):
    """
    Updates a pilot's status in the Google Sheet.
    Accepts: pilot_id (e.g., 'P001') and new_status (e.g., 'On Leave').
    """
    client = get_sheet_client()
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet("pilot_roster")
    
    # Locate the Pilot ID in Column A
    ids = sheet.col_values(1)
    if pilot_id not in ids:
        return f"ERROR: Pilot ID {pilot_id} not found."
    
    row = ids.index(pilot_id) + 1 # Convert to 1-indexed
    
    # Update Column 6 (Status)
    sheet.update_cell(row, 6, new_status)
    
    # Read back values to verify to the AI that it actually happened
    p_name = sheet.cell(row, 2).value
    v_status = sheet.cell(row, 6).value
    
    return f"VERIFIED_SYNC: {p_name} ({pilot_id}) is now {v_status} at row {row}."

@mcp.tool()
def detect_conflicts():
    """Identifies drones in maintenance assigned to active missions."""
    data = get_all_data()
    drones = pd.DataFrame(data['drones'])
    
    m_drones = drones[drones['status'] == 'Maintenance']
    conflicts = [f"Drone {d['drone_id']} is in Maintenance but assigned to {d['current_assignment']}" 
                 for _, d in m_drones.iterrows() if d['current_assignment'] not in ['–', '', 'None']]
    
    return "\n".join(conflicts) if conflicts else "Health Check: No conflicts detected."

if __name__ == "__main__":
    mcp.run()