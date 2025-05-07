#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la integración de ValidationProcessor con Google Sheets.

Este script verifica:
1. La existencia del archivo de credenciales
2. La autenticación correcta con Google API
3. El acceso a Google Sheets y Google Drive APIs
4. La capacidad de leer/escribir en la hoja de cálculo configurada
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path to allow imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import required modules
from integrations.google_sheets import GoogleSheetsIntegration

# Load environment variables
load_dotenv()

def main():
    """Run verification checks for Google Sheets integration"""
    print("\n=== ValidationProcessor + Google Sheets Integration Verification ===\n")
    
    # Get credentials file path
    credentials_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if not credentials_file:
        credentials_file = os.path.join(project_root, "config", "scrapermvp-f254174c1385.json")
    
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID', '')
    
    # Step 1: Check if credentials file exists
    print(f"Step 1: Checking credentials file...")
    if os.path.exists(credentials_file):
        print(f"✅ Credentials file found at: {credentials_file}")
    else:
        print(f"❌ Credentials file NOT found at: {credentials_file}")
        print("\nPossible solutions:")
        print("  1. Create a service account in Google Cloud Console")
        print("  2. Download the JSON credentials file")
        print("  3. Set the GOOGLE_SERVICE_ACCOUNT_FILE environment variable")
        print("  4. Or place the file in config/scrapermvp-f254174c1385.json")
        return
    
    # Step 2: Initialize Google Sheets integration
    sheets = GoogleSheetsIntegration(
        credentials_file=credentials_file,
        spreadsheet_id=spreadsheet_id
    )
    
    # Step 3: Check authentication
    print("\nStep 2: Testing authentication...")
    try:
        auth_result = sheets.authenticate()
        if auth_result:
            print("✅ Authentication successful!")
        else:
            print("❌ Authentication failed!")
            return
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        print("\nPossible solutions:")
        print("  1. Check that the credentials file is valid and not corrupted")
        print("  2. Ensure that the service account has the necessary permissions")
        print("  3. Check that your Google Cloud project is active")
        return
    
    # Step 4: Check API access
    print("\nStep 3: Checking API access...")
    try:
        api_status = sheets.check_api_access()
        
        if api_status['sheets']:
            print("✅ Google Sheets API: Accessible")
        else:
            print("❌ Google Sheets API: Not accessible")
            print("   Enable the Google Sheets API in your Google Cloud Console")
        
        if api_status['drive']:
            print("✅ Google Drive API: Accessible")
        else:
            print("❌ Google Drive API: Not accessible")
            print("   Enable the Google Drive API in your Google Cloud Console")
            
        if not api_status['sheets'] or not api_status['drive']:
            return
    except Exception as e:
        print(f"❌ API access check error: {str(e)}")
        return
    
    # Step 5: Check spreadsheet access
    print("\nStep 4: Checking spreadsheet access...")
    
    if not spreadsheet_id:
        print("ℹ️ No spreadsheet ID provided. Will create a test spreadsheet.")
        try:
            new_id = sheets.create_spreadsheet("ValidationProcessor Test")
            print(f"✅ Successfully created test spreadsheet with ID: {new_id}")
            print(f"   URL: https://docs.google.com/spreadsheets/d/{new_id}/edit")
            spreadsheet_id = new_id
        except Exception as e:
            print(f"❌ Failed to create test spreadsheet: {str(e)}")
            return
    else:
        try:
            sheets.open_spreadsheet_by_id(spreadsheet_id)
            print(f"✅ Successfully opened spreadsheet with ID: {spreadsheet_id}")
        except Exception as e:
            print(f"❌ Failed to open spreadsheet: {str(e)}")
            print("\nPossible solutions:")
            print("  1. Verify the spreadsheet ID is correct")
            print("  2. Make sure the service account has access to this spreadsheet")
            print("  3. Share the spreadsheet with the service account email")
            return
    
    # Step 6: Test writing to spreadsheet
    print("\nStep 5: Testing write access...")
    try:
        import pandas as pd
        test_data = pd.DataFrame({
            'test_column': ['ValidationProcessor integration test was successful!']
        })
        
        sheets.upload_data(test_data, "IntegrationTest")
        print("✅ Successfully wrote test data to spreadsheet")
    except Exception as e:
        print(f"❌ Failed to write to spreadsheet: {str(e)}")
        return
    
    # All checks passed!
    print("\n==== All Checks Passed! ====")
    print("\nValidationProcessor + Google Sheets integration is working correctly!")
    print(f"\nYou can access your spreadsheet at:")
    print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    
    # Set environment variable for future use
    if not os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID'):
        print(f"\nTIP: Add this to your .env file to use this spreadsheet by default:")
        print(f"GOOGLE_SHEETS_SPREADSHEET_ID={spreadsheet_id}")

if __name__ == "__main__":
    main()
