#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google API Access Check

This script checks access to Google Sheets and Drive APIs using the configured credentials.
It helps diagnose permission issues with your Google service account.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the GoogleSheetsIntegration class
from integrations.google_sheets import GoogleSheetsIntegration


def main():
    """Run the diagnostic script."""
    # Load environment variables from .env file
    load_dotenv()
    
    print("=== Google API Access Diagnostic ===\n")
    
    # Check environment variables
    print("1. Checking environment variables...")
    creds_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    creds_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    
    if creds_file:
        print(f"✓ GOOGLE_SERVICE_ACCOUNT_FILE is set: {creds_file}")
        if os.path.exists(creds_file):
            print(f"✓ Credentials file exists")
            # Print basic info from credentials file
            try:
                with open(creds_file, 'r') as f:
                    creds_data = json.load(f)
                    print(f"  - Service account email: {creds_data.get('client_email', 'N/A')}")
                    print(f"  - Project ID: {creds_data.get('project_id', 'N/A')}")
            except Exception as e:
                print(f"✗ Could not read credentials file: {str(e)}")
        else:
            print(f"✗ Credentials file does not exist: {creds_file}")
    elif creds_json:
        print("✓ GOOGLE_SERVICE_ACCOUNT_JSON is set")
        try:
            creds_data = json.loads(creds_json)
            print(f"  - Service account email: {creds_data.get('client_email', 'N/A')}")
            print(f"  - Project ID: {creds_data.get('project_id', 'N/A')}")
        except Exception as e:
            print(f"✗ Could not parse credentials JSON: {str(e)}")
    else:
        print("✗ No credentials environment variables are set")
        
    if spreadsheet_id:
        print(f"✓ GOOGLE_SHEETS_SPREADSHEET_ID is set: {spreadsheet_id}")
    else:
        print("✗ GOOGLE_SHEETS_SPREADSHEET_ID is not set")
    
    # Initialize Google Sheets integration
    print("\n2. Initializing GoogleSheetsIntegration...")
    sheets = GoogleSheetsIntegration()
    
    # Authenticate
    print("\n3. Attempting authentication...")
    try:
        auth_success = sheets.authenticate()
        if auth_success:
            print("✓ Authentication successful")
            
            # Print service account email
            if hasattr(sheets.credentials, 'service_account_email'):
                print(f"  - Authenticated as: {sheets.credentials.service_account_email}")
        else:
            print("✗ Authentication failed")
    except Exception as e:
        print(f"✗ Authentication error: {str(e)}")
        return
    
    # Check API access
    print("\n4. Checking API access...")
    try:
        api_status = sheets.check_api_access()
        print(f"  - Google Sheets API: {'✓ Accessible' if api_status['sheets'] else '✗ Not accessible'}")
        print(f"  - Google Drive API: {'✓ Accessible' if api_status['drive'] else '✗ Not accessible'}")
    except Exception as e:
        print(f"✗ API access check error: {str(e)}")
    
    # Try to list spreadsheets
    print("\n5. Attempting to list spreadsheets...")
    try:
        # Use openall() instead of list_spreadsheet_files with limit
        spreadsheets = sheets.client.openall()  # Get all accessible spreadsheets
        print(f"✓ Successfully listed {len(spreadsheets)} spreadsheets")
        for sheet in spreadsheets:
            print(f"  - {sheet.title} ({sheet.id})")
    except Exception as e:
        print(f"✗ Error listing spreadsheets: {str(e)}")
    
    # Try to open the configured spreadsheet
    if spreadsheet_id:
        print(f"\n6. Attempting to open spreadsheet with ID: {spreadsheet_id}")
        try:
            sheets.open_spreadsheet_by_id(spreadsheet_id)
            print("✓ Successfully opened spreadsheet")
            
            # Try to get permissions
            print("\n7. Attempting to get spreadsheet permissions...")
            try:
                permissions = sheets.get_spreadsheet_permissions()
                print(f"✓ Successfully retrieved {len(permissions)} permissions")
                for perm in permissions:
                    email = perm.get('emailAddress', 'N/A')
                    role = perm.get('role')
                    perm_type = perm.get('type')
                    print(f"  - {email}: {role} ({perm_type})")
                    
                # Check if service account has access
                service_account_email = sheets.credentials.service_account_email if hasattr(sheets.credentials, 'service_account_email') else None
                if service_account_email:
                    service_account_perms = [p for p in permissions if p.get('emailAddress') == service_account_email]
                    if service_account_perms:
                        print(f"✓ Service account has access to this spreadsheet with role: {service_account_perms[0].get('role')}")
                    else:
                        print("✗ Service account does not have explicit permission to this spreadsheet")
            except Exception as e:
                print(f"✗ Error getting permissions: {str(e)}")
                
            # Try to list worksheets
            print("\n8. Attempting to list worksheets...")
            try:
                worksheets = sheets.spreadsheet.worksheets()
                print(f"✓ Successfully listed {len(worksheets)} worksheets")
                for ws in worksheets:
                    print(f"  - {ws.title}")
            except Exception as e:
                print(f"✗ Error listing worksheets: {str(e)}")
        except Exception as e:
            print(f"✗ Error opening spreadsheet: {str(e)}")
    
    # Conclusion
    print("\n=== Diagnostic Summary ===")
    if not auth_success:
        print("Authentication failed. Please check your credentials.")
    elif not api_status.get('sheets', False):
        print("Google Sheets API is not accessible. Ensure it's enabled in the Google Cloud Console.")
    elif not api_status.get('drive', False):
        print("Google Drive API is not accessible. Ensure it's enabled in the Google Cloud Console.")
    elif spreadsheet_id and not sheets.spreadsheet:
        print("Could not access the specified spreadsheet. Ensure the ID is correct and the service account has access.")
    else:
        print("Basic API access looks good. If you're still having issues with a specific spreadsheet,")
        print("ensure your service account has been explicitly granted access to it.")


if __name__ == "__main__":
    main()
