#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que la integración de ValidationProcessor con Google Sheets funciona correctamente.
"""

import os
import sys
import pandas as pd
import json
from datetime import datetime
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import required modules
from processing.data_processor import ValidationProcessor
from integrations.google_sheets import GoogleSheetsIntegration

def main():
    print("\n=== ValidationProcessor + Google Sheets Integration Test ===\n")
    
    # Step 1: Create test data
    print("Step 1: Creating test data...")
    test_data = create_test_data()
    print(f"Created test data with {len(test_data)} records")
    
    # Step 2: Process with ValidationProcessor
    print("\nStep 2: Processing data with ValidationProcessor...")
    validator = ValidationProcessor(test_data)
    processed_data = validator.process()
    print(f"Processed {len(processed_data)} records with ValidationProcessor")
    
    # Step 3: Initialize Google Sheets Integration
    print("\nStep 3: Initializing Google Sheets Integration...")
    
    # Use explicit spreadsheet ID
    spreadsheet_id = "19VQZ6Ua5oBx55QkGw9B0WZyX7Z2ard9Gh8YQ4tUstIs"  # ID de la nueva hoja creada por la cuenta de servicio
    
    # Initialize GoogleSheetsIntegration with explicit spreadsheet ID
    sheets = GoogleSheetsIntegration(spreadsheet_id=spreadsheet_id)
    
    try:
        auth_result = sheets.authenticate()
        if auth_result:
            print("✅ Authentication successful")
        else:
            print("❌ Authentication failed")
            return
    except Exception as e:
        print(f"❌ Authentication error: {str(e)}")
        return
        
    # Step 4: Upload data to Google Sheets
    print("\nStep 4: Uploading data to Google Sheets...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    worksheet_name = f"Validation_Test_{timestamp}"
    
    # Convert complex columns to string format
    if 'validation_flags' in processed_data.columns:
        processed_data['validation_flags'] = processed_data['validation_flags'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else str(x))
    
    try:
        sheets.upload_data(processed_data, worksheet_name, clear_existing=True)
        print(f"✅ Successfully uploaded data to worksheet: {worksheet_name}")
    except Exception as e:
        print(f"❌ Error uploading data: {str(e)}")
        return
        
    # Step 5: Format worksheet
    print("\nStep 5: Formatting worksheet...")
    try:
        sheets.format_worksheet(worksheet_name, bold_header=True, freeze_header=True, autofit_columns=True)
        print("✅ Successfully formatted worksheet")
    except Exception as e:
        print(f"❌ Error formatting worksheet: {str(e)}")
        return
        
    # Success message with link
    print(f"\n✅ Integration test successful. View the results at:")
    print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=0")
    
def create_test_data():
    """Create test data for validation."""
    # Define test data with mix of valid and invalid emails/phones
    data = {
        'business_name': ['Alpha Technologies', 'Beta Services', 'Gamma Solutions', 'Invalid Data Company', 'Test Corp'],
        'email': ['contact@alpha-tech.com', 'info@betaserv.co', 'sales@gamma.xyz', 'not-an-email', 'test@example.com'],
        'phone': ['+5215512345678', '555-123-4567', '(123) 456-7890', '12', '+525587654321'],
        'address': [
            'Calle Principal 123, CDMX, México',
            '456 Main St, Santiago, Chile',
            'Av. Corrientes 789, Buenos Aires, Argentina',
            'Invalid Address',
            'Avenida Central 55, Lima, Perú'
        ],
        'source': ['Google Maps', 'Instagram', 'Directory', 'Test Data', 'Manual Entry']
    }
    
    return pd.DataFrame(data)

if __name__ == "__main__":
    main()
