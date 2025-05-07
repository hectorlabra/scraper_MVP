#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para probar la escritura en Google Sheets usando el ID correcto
"""

import os
import sys
import pandas as pd
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import Google Sheets integration
from integrations.google_sheets import GoogleSheetsIntegration

# Load environment variables
load_dotenv()

def main():
    print("\n=== Test de escritura simple en Google Sheets ===\n")
    
    # Use explicit spreadsheet ID
    spreadsheet_id = "19VQZ6Ua5oBx55QkGw9B0WZyX7Z2ard9Gh8YQ4tUstIs"
    print(f"Using spreadsheet ID: {spreadsheet_id}")
    
    # Create a simple test DataFrame
    data = {
        'Nombre': ['Test 1', 'Test 2', 'Test 3'],
        'Valor': [100, 200, 300],
        'Fecha': ['2025-05-07', '2025-05-07', '2025-05-07']
    }
    df = pd.DataFrame(data)
    
    # Initialize GoogleSheetsIntegration with the correct spreadsheet ID
    print("\nIniciando integración con Google Sheets...")
    sheets = GoogleSheetsIntegration(spreadsheet_id=spreadsheet_id)
    
    # Authenticate
    print("Autenticando...")
    auth_result = sheets.authenticate()
    if not auth_result:
        print("❌ Error en la autenticación")
        return
    
    print("✅ Autenticación exitosa")
    
    # Upload data
    try:
        print("\nSubiendo datos de prueba...")
        worksheet_name = "Test_Simple"
        sheets.upload_data(df, worksheet_name, clear_existing=True)
        print(f"✅ Datos subidos correctamente a la hoja '{worksheet_name}'")
        
        # Format worksheet
        print("\nAplicando formato...")
        sheets.format_worksheet(worksheet_name, bold_header=True, freeze_header=True, autofit_columns=True)
        print("✅ Formato aplicado correctamente")
        
        print(f"\nPuedes ver los resultados en: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    except Exception as e:
        print(f"❌ Error al subir datos: {str(e)}")
        return

if __name__ == "__main__":
    main()
