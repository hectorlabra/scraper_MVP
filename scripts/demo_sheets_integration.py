#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets Integration Demo

This script demonstrates the functionality of the GoogleSheetsIntegration class,
including authentication, spreadsheet creation, data upload, and permission management.

Usage:
    python demo_sheets_integration.py

Notes:
    Before running this script, ensure you have:
    1. A Google Cloud Platform project with Google Sheets API enabled
    2. A service account with appropriate permissions
    3. Service account credentials in a JSON file or in an environment variable
    4. Either set GOOGLE_SERVICE_ACCOUNT_FILE environment variable or pass the file path
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrations.google_sheets import GoogleSheetsIntegration, PermissionType

# Load environment variables from .env file (if present)
load_dotenv()

# ID de la hoja de cálculo específica que queremos usar
SPECIFIC_SPREADSHEET_ID = "1ZccoO_Z7rEMG5MJq48o7eARFvvFIsmXdakAOBtgkPYE"  

def main():
    """Run the Google Sheets integration demo."""
    print("===== Google Sheets Integration Demo =====")
    
    # Get credentials file path from environment or use default
    creds_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    if not creds_file:
        print("Warning: GOOGLE_SERVICE_ACCOUNT_FILE environment variable not set.")
        creds_file = input("Enter path to service account credentials file: ")
    
    # Usar la ID de hoja específica en lugar de buscarla en las variables de entorno
    spreadsheet_id = SPECIFIC_SPREADSHEET_ID
    print(f"Using specific spreadsheet ID: {spreadsheet_id}")
    
    # Initialize the Google Sheets integration
    print(f"\n1. Initializing Google Sheets integration with credentials: {creds_file}")
    sheets = GoogleSheetsIntegration(
        credentials_file=creds_file, 
        spreadsheet_id=spreadsheet_id
    )
    
    # Authenticate
    print("\n2. Authenticating with Google Sheets API...")
    try:
        sheets.authenticate()
        print("✓ Authentication successful!")
    except Exception as e:
        print(f"✗ Authentication failed: {str(e)}")
        # Print more detailed exception information
        import traceback
        print("\nDetailed error traceback:")
        traceback.print_exc()
        return
    
    # Open existing spreadsheet or create one if not found
    if not sheets.spreadsheet:
        print(f"\n3. Could not access spreadsheet with ID: {spreadsheet_id}")
        print("Possible causes:")
        print("  - The spreadsheet does not exist")
        print("  - The service account does not have access to the spreadsheet")
        print("\nPlease run scripts/share_spreadsheet.py to share your spreadsheet with the service account.")
        create_new = input("Would you like to create a new spreadsheet instead? (y/n): ")
        if create_new.lower() == 'y':
            print("Creating a new spreadsheet...")
            try:
                spreadsheet_id = sheets.create_spreadsheet("Scraper MVP Demo")
                print(f"✓ Created spreadsheet with ID: {spreadsheet_id}")
            except Exception as e:
                print(f"✗ Failed to create spreadsheet: {str(e)}")
                return
        else:
            print("Demo canceled. Please share your spreadsheet with the service account.")
            return
    else:
        print(f"\n3. Successfully opened spreadsheet with ID: {spreadsheet_id}")
    
    # Create demo data
    print("\n4. Preparing demo data...")
    data = pd.DataFrame({
        'Nombre': ['Juan Pérez', 'Ana García', 'Carlos Rodríguez'],
        'Email': ['juan@ejemplo.com', 'ana@ejemplo.com', 'carlos@ejemplo.com'],
        'Puntuación': [85, 92, 78],
        'Ubicación': ['Madrid', 'Barcelona', 'Valencia']
    })
    print(data)
    
    
    # Upload data to a worksheet
    print("\n5. Uploading data to a worksheet...")
    try:
        # Preguntar al usuario qué hoja (worksheet) usar
        worksheet_name = input("Nombre de la hoja donde subir los datos (por defecto: 'DatosPrueba'): ") or "DatosPrueba"
        
        # Preguntar si usar carga optimizada
        optimized = input("¿Usar carga optimizada? (s/n, default: s): ").lower() != 'n'
        
        if optimized:
            print("⚡ Usando carga optimizada (detecta cambios y actualiza solo celdas modificadas)")
            stats = sheets.upload_data_optimized(data, worksheet_name, detect_changes=True)
            print(f"✓ Datos subidos correctamente a la hoja '{worksheet_name}'!")
            print(f"  - Celdas actualizadas: {stats.get('updated', 0)}")
            print(f"  - Celdas sin cambios: {stats.get('unchanged', 0)}")
            print(f"  - Celdas añadidas: {stats.get('added', 0)}")
        else:
            print("📝 Usando carga estándar")
            sheets.upload_data(data, worksheet_name)
            print(f"✓ Datos subidos correctamente a la hoja '{worksheet_name}'!")
    except Exception as e:
        print(f"✗ Error al subir datos: {str(e)}")
    
    # Share the spreadsheet (if email provided)
    share_with = input("\n6. Escribe un email para compartir la hoja (o presiona Enter para omitir): ")
    if share_with:
        try:
            print(f"Compartiendo hoja con {share_with}...")
            sheets.share_spreadsheet(
                share_with, 
                PermissionType.WRITER,
                message="Esta es una hoja de demostración del proyecto Scraper MVP."
            )
            print("✓ Hoja compartida correctamente!")
        except Exception as e:
            print(f"✗ Error al compartir la hoja: {str(e)}")
    
    # Get and display permissions
    print("\n7. Obteniendo permisos actuales...")
    try:
        permissions = sheets.get_spreadsheet_permissions()
        print("Permisos actuales:")
        for perm in permissions:
            email = perm.get('emailAddress', 'N/A')
            role = perm.get('role', 'N/A')
            type_ = perm.get('type', 'N/A')
            print(f"  - {email} ({role}, {type_})")
    except Exception as e:
        print(f"✗ Error al obtener permisos: {str(e)}")
    
    # Make the spreadsheet public
    make_public = input("\n8. ¿Hacer la hoja pública? (s/n): ")
    if make_public.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        try:
            sheets.make_public(PermissionType.READER)
            print("✓ La hoja es ahora accesible públicamente (sólo lectura)!")
        except Exception as e:
            print(f"✗ Error al hacer la hoja pública: {str(e)}")
    
    # Final message with spreadsheet URL
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"\n¡Demostración completada! Puedes acceder a tu hoja en:\n{spreadsheet_url}")

if __name__ == "__main__":
    main()
