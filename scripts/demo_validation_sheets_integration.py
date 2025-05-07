#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script showing the complete ValidationProcessor integration with Google Sheets.

This script demonstrates:
1. Carga de datos de prueba
2. Validación de emails con ValidationProcessor
3. Validación de teléfonos con ValidationProcessor
4. Puntuación y filtrado de calidad con ValidationProcessor
5. Autenticación con Google Sheets
6. Carga de los datos procesados a Google Sheets
"""

import os
import sys
import pandas as pd
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path to allow imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import required modules
from processing.data_processor import ValidationProcessor
from integrations.google_sheets import GoogleSheetsIntegration
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main function demonstrating ValidationProcessor integration with Google Sheets"""
    print("\n=== ValidationProcessor + Google Sheets Integration Demo ===\n")
    
    # Step 1: Load test data
    results_dir = os.path.join(project_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    test_data_path = os.path.join(results_dir, "test_data.json")
    if not os.path.exists(test_data_path):
        print(f"Test data not found at: {test_data_path}")
        print("Creating synthetic data...")
        create_synthetic_data(test_data_path)
    
    with open(test_data_path, "r") as f:
        data = json.load(f)
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} records from test data")
    print(df.head())
    
    # Step 2: Initialize ValidationProcessor
    print("\nInitializing ValidationProcessor...")
    validator = ValidationProcessor(df)
    
    # Step 3: Validate emails
    print("\nValidating email addresses...")
    df = validator.validate_emails()
    print(f"After email validation: {len(df)} records")
    
    # Step 4: Validate phone numbers
    print("\nValidating phone numbers...")
    df = validator.validate_phone_numbers()
    print(f"After phone validation: {len(df)} records")
    
    # Step 5: Filter by quality score
    min_quality = 0.5  # 50% minimum quality
    print(f"\nFiltering records with quality score >= {min_quality}...")
    df = validator.filter_by_quality_score(min_score=min_quality)
    print(f"After quality filtering: {len(df)} records")
    
    # Save processed results locally
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(results_dir, f"validated_data_{timestamp}.csv")
    df.to_csv(output_file, index=False)
    print(f"\nSaved validated data to: {output_file}")
    
    # Step 6: Initialize Google Sheets integration
    print("\nInitializing Google Sheets integration...")
    
    # Get credentials file path (from env var or default location)
    credentials_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if not credentials_file:
        credentials_file = os.path.join(project_root, "config", "scrapermvp-f254174c1385.json")
    
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID', '')
    
    if not os.path.exists(credentials_file):
        print(f"Error: Credentials file not found at {credentials_file}")
        print("Please set GOOGLE_SERVICE_ACCOUNT_FILE environment variable to a valid credentials file.")
        print("\nUse scripts/share_spreadsheet.py to setup Google Sheets authentication.")
        return
    
    try:
        # Initialize Google Sheets integration
        sheets = GoogleSheetsIntegration(
            credentials_file=credentials_file,
            spreadsheet_id=spreadsheet_id
        )
        
        # Authenticate
        print("Authenticating with Google Sheets API...")
        auth_result = sheets.authenticate()
        if not auth_result:
            print("Authentication failed!")
            return
        
        print("Authentication successful!")
        
        # Check API access
        print("\nChecking API access...")
        api_status = sheets.check_api_access()
        print(f"Google Sheets API: {'✓ Accessible' if api_status['sheets'] else '✗ Not accessible'}")
        print(f"Google Drive API: {'✓ Accessible' if api_status['drive'] else '✗ Not accessible'}")
        
        if not api_status['sheets'] or not api_status['drive']:
            print("\nAPI access issue detected. Please enable required APIs in Google Cloud Console.")
            return
        
        # Step 7: Upload data to Google Sheets
        print("\nUploading validated data to Google Sheets...")
        
        # Create new spreadsheet if we don't have an ID
        if not spreadsheet_id:
            try:
                print("Creating new spreadsheet...")
                spreadsheet_id = sheets.create_spreadsheet(f"LeadScraper Validated Data {timestamp}")
                print(f"Created new spreadsheet with ID: {spreadsheet_id}")
                sheets.open_spreadsheet_by_id(spreadsheet_id)
            except Exception as e:
                print(f"Error creating spreadsheet: {str(e)}")
                return
        
        # Upload the data
        sheet_title = "Validated Data"
        sheets.upload_data(df, sheet_title, clear_existing=True)
        print(f"✓ Data uploaded successfully to sheet '{sheet_title}'")
        
        # Format the worksheet
        print("\nFormatting worksheet...")
        sheets.format_worksheet(
            sheet_title,
            bold_header=True,
            freeze_header=True,
            autofit_columns=True
        )
        print("✓ Worksheet formatted successfully")
        
        # Share the spreadsheet
        print("\nWould you like to share this spreadsheet? (y/n): ", end="")
        share = input().lower()
        if share == 'y':
            email = input("Enter the email address to share with: ")
            if email:
                sheets.share_spreadsheet(email)
                print(f"✓ Spreadsheet shared with {email}")
        
        print("\nGoogle Sheets URL:")
        print(f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    
    except Exception as e:
        print(f"Error with Google Sheets integration: {str(e)}")
        import traceback
        traceback.print_exc()

def create_synthetic_data(output_path, num_records=50):
    """Create synthetic test data for demonstration"""
    import random
    
    # Example business names
    businesses = [
        "Café El Dorado", "Restaurante La Paloma", "Hotel Estrella", 
        "Pastelería Dulce", "Ferretería Martínez", "Farmacia San Juan",
        "Librería El Saber", "Gimnasio Fitness", "Peluquería Bella",
        "Carnicería Don Pedro"
    ]
    
    # Email templates
    email_templates = [
        "info@{domain}.com", "contacto@{domain}.com", "reservas@{domain}.com",
        "ventas@{domain}.{tld}", "admin@{domain}.{tld}", "soporte@{domain}.com",
        "{name}@gmail.com", "{name}@hotmail.com", "{name}@outlook.com",
        "invalid-email", "missing@", "@example.com", "no-domain@.com"
    ]
    
    # Phone templates for different countries
    phone_templates = [
        "+52 {area} {local}",  # México
        "+56 9 {local2}",      # Chile
        "+54 11 {local2}",     # Argentina
        "+55 11 {local2}",     # Brasil
        "+57 {area} {local}",  # Colombia
        "invalid-phone",       # Invalid
        "{local3}",            # Missing country code
        "+999 123 456"         # Invalid country code
    ]
    
    # TLDs for Latin America
    tlds = ["com", "mx", "cl", "ar", "br", "co", "pe"]
    
    # Generate random data
    data = []
    for i in range(num_records):
        business_name = random.choice(businesses) + " " + str(random.randint(1, 100))
        domain = business_name.lower().replace(" ", "").replace("í", "i").replace("é", "e").replace("á", "a").replace("ó", "o").replace("ú", "u")
        
        name = domain.split("el")[-1] if "el" in domain else domain
        
        # Format the email using a template
        email_template = random.choice(email_templates)
        email = email_template.format(
            domain=domain, 
            tld=random.choice(tlds),
            name=name
        )
        
        # Format the phone number
        phone_template = random.choice(phone_templates)
        phone = phone_template.format(
            area=random.randint(100, 999),
            local=f"{random.randint(100, 999)} {random.randint(1000, 9999)}",
            local2=f"{random.randint(1000, 9999)} {random.randint(1000, 9999)}",
            local3=random.randint(10000000, 99999999)
        )
        
        # Address
        cities = ["Ciudad de México", "Santiago", "Buenos Aires", "São Paulo", "Bogotá", "Lima"]
        streets = ["Av. Principal", "Calle Central", "Paseo de la Reforma", "Av. Libertador", "Calle San Martín"]
        
        address = f"{random.choice(streets)} #{random.randint(100, 9999)}, {random.choice(cities)}"
        
        # Create record
        record = {
            "business_name": business_name,
            "email": email,
            "phone": phone,
            "address": address,
            "website": f"http://www.{domain}.com" if random.random() > 0.3 else "",
            "category": random.choice(["Restaurante", "Hotel", "Tienda", "Servicio", "Otro"]),
            "source": random.choice(["google_maps", "paginas_amarillas", "guialocal", "instagram"])
        }
        
        data.append(record)
    
    # Save to file
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Created {num_records} synthetic records at {output_path}")

if __name__ == "__main__":
    main()
