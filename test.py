import gspread
from google.oauth2.service_account import Credentials

# 1. Setup
SPREADSHEET_ID = "1nLCL9cn1jAwXneKYuqnCUx9iVKBWLGM1VZFuDdbpDLc"
SERVICE_ACCOUNT_FILE = "service_account.json"

def check_connection():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Try to open the sheet
        sheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✅ Connection Successful! Connected to: {sheet.title}")
        
        # Try to read the tabs
        worksheets = [ws.title for ws in sheet.worksheets()]
        print(f"✅ Tabs found: {worksheets}")
        
    except Exception as e:
        print(f"❌ Connection Failed!")
        print(f"Error Details: {e}")

if __name__ == "__main__":
    check_connection()