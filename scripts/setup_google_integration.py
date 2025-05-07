#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar correctamente la integración con Google Sheets y Drive.

Este script:
1. Verifica las credenciales de la cuenta de servicio
2. Crea una nueva hoja de cálculo (propiedad de la cuenta de servicio)
3. Configura las variables de entorno necesarias
4. Comprueba que todas las APIs requeridas estén habilitadas

Uso: python setup_google_integration.py
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import required modules
from integrations.google_sheets import GoogleSheetsIntegration, PermissionType

# Load environment variables
load_dotenv()

def main():
    """Main function to setup Google Sheets integration."""
    print("\n===== Configuración de Google Sheets y Drive para ValidationProcessor =====\n")
    
    # Helper function to get timestamp
    def _get_timestamp():
        """Get formatted timestamp for sheet titles and data"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Step 1: Check for credentials file
    credentials_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if not credentials_file:
        print("No se encontró la variable de entorno GOOGLE_SERVICE_ACCOUNT_FILE.")
        default_path = os.path.join(project_root, "config", "scrapermvp-f254174c1385.json")
        
        if os.path.exists(default_path):
            print(f"✅ Se encontró el archivo de credenciales en la ubicación por defecto: {default_path}")
            credentials_file = default_path
        else:
            print("❌ No se encontró el archivo de credenciales en la ubicación por defecto.")
            credentials_file = input("Por favor, introduce la ruta completa al archivo de credenciales: ")
            
            if not os.path.exists(credentials_file):
                print(f"❌ No se encontró el archivo en la ruta: {credentials_file}")
                print_credentials_instructions()
                return
    
    # Step 2: Extract service account email from credentials
    try:
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
            service_account_email = creds_data.get('client_email')
            project_id = creds_data.get('project_id')
            
            if not service_account_email:
                print("❌ No se pudo encontrar el email de la cuenta de servicio en el archivo.")
                print_credentials_instructions()
                return
                
        print(f"✅ Cuenta de servicio identificada: {service_account_email}")
        print(f"✅ Proyecto de Google Cloud: {project_id}")
    except Exception as e:
        print(f"❌ Error al leer el archivo de credenciales: {str(e)}")
        print_credentials_instructions()
        return
    
    # Step 3: Initialize GoogleSheetsIntegration
    print("\nIniciando la autenticación con Google...")
    try:
        sheets = GoogleSheetsIntegration(credentials_file=credentials_file)
        auth_result = sheets.authenticate()
        
        if not auth_result:
            print("❌ La autenticación falló. Asegúrate de que las credenciales sean válidas.")
            print_api_instructions(project_id)
            return
            
        print("✅ Autenticación exitosa.")
    except Exception as e:
        print(f"❌ Error durante la autenticación: {str(e)}")
        print_api_instructions(project_id)
        return
    
    # Step 4: Check API access
    print("\nVerificando acceso a las APIs necesarias...")
    api_status = sheets.check_api_access()
    
    all_apis_enabled = True
    
    if api_status['sheets']:
        print("✅ Google Sheets API está habilitada y accesible.")
    else:
        print("❌ Google Sheets API no está habilitada o accesible.")
        all_apis_enabled = False
    
    if api_status['drive']:
        print("✅ Google Drive API está habilitada y accesible.")
    else:
        print("❌ Google Drive API no está habilitada o accesible.")
        all_apis_enabled = False
    
    if not all_apis_enabled:
        print_api_instructions(project_id)
    
    # Step 5: Create a new spreadsheet
    spreadsheet_id = os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID', '')
    
    if spreadsheet_id:
        print(f"\nYa existe un ID de hoja de cálculo configurado: {spreadsheet_id}")
        use_existing = input("¿Quieres usar esta hoja existente? (s/n): ").lower()
        
        if use_existing == 's':
            try:
                sheets.open_spreadsheet_by_id(spreadsheet_id)
                print(f"✅ Se pudo abrir la hoja con ID: {spreadsheet_id}")
            except Exception as e:
                print(f"❌ No se pudo abrir la hoja: {str(e)}")
                create_new = input("¿Crear una nueva hoja? (s/n): ").lower()
                if create_new != 's':
                    return
                spreadsheet_id = ""
        else:
            spreadsheet_id = ""
    
    if not spreadsheet_id:
        print("\nCreando una nueva hoja de cálculo...")
        try:
            sheet_title = f"LeadScraper ValidationProcessor {_get_timestamp()}"
            spreadsheet_id = sheets.create_spreadsheet(sheet_title)
            print(f"✅ Hoja de cálculo creada con éxito.")
            print(f"  ID: {spreadsheet_id}")
            print(f"  URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
            
            # Share with user
            share_email = input("\n¿Con qué correo electrónico quieres compartir esta hoja? (Deja vacío para omitir): ")
            if share_email:
                sheets.share_spreadsheet(
                    share_email, 
                    PermissionType.WRITER,
                    message="Hoja creada para la integración de ValidationProcessor con Google Sheets."
                )
                print(f"✅ Hoja compartida con {share_email}")
        except Exception as e:
            print(f"❌ Error al crear la hoja de cálculo: {str(e)}")
            print("Esto puede indicar un problema con los permisos de la cuenta de servicio.")
            print_api_instructions(project_id)
            return
    
    # Step 6: Update .env file
    if update_env_file(credentials_file, spreadsheet_id):
        print("\n✅ Archivo .env actualizado con la configuración de Google Sheets.")
    
    # Step 7: Verify setup with a test upload
    print("\nRealizando una prueba de escritura...")
    try:
        import pandas as pd
        test_data = pd.DataFrame({
            'Prueba': ['Configuración completada con éxito'],
            'Fecha': [_get_timestamp()]
        })
        
        sheets.upload_data(test_data, "Test", clear_existing=True)
        print("✅ Prueba de escritura exitosa. La integración está configurada correctamente.")
        
        # Format the worksheet
        sheets.format_worksheet("Test", bold_header=True, freeze_header=True, autofit_columns=True)
    except Exception as e:
        print(f"❌ Error en la prueba de escritura: {str(e)}")
        print("Revisa que todas las APIs necesarias estén habilitadas.")
        print_api_instructions(project_id)
        return
    
    # Final confirmation
    print("\n=== CONFIGURACIÓN COMPLETADA ===")
    print("\nLa integración de ValidationProcessor con Google Sheets está lista para usarse.")
    print(f"Puedes acceder a tu hoja de cálculo en: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    print("\nPuedes probar la integración completa con:")
    print("python scripts/demo_validation_sheets_integration.py")

def update_env_file(credentials_file, spreadsheet_id):
    """Update or create .env file with Google Sheets configuration."""
    env_path = os.path.join(project_root, ".env")
    
    # Read existing .env content if it exists
    env_content = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    
    # Update with new values
    env_content['GOOGLE_SERVICE_ACCOUNT_FILE'] = credentials_file
    env_content['GOOGLE_SHEETS_SPREADSHEET_ID'] = spreadsheet_id
    env_content['ENABLE_GOOGLE_SHEETS'] = 'true'
    
    # Write back to .env
    try:
        with open(env_path, 'w') as f:
            for key, value in env_content.items():
                f.write(f"{key}={value}\n")
        return True
    except Exception as e:
        print(f"❌ Error al actualizar el archivo .env: {str(e)}")
        print(f"Asegúrate de que el archivo {env_path} sea editable.")
        print("\nPuedes configurar manualmente las siguientes variables de entorno:")
        print(f"GOOGLE_SERVICE_ACCOUNT_FILE={credentials_file}")
        print(f"GOOGLE_SHEETS_SPREADSHEET_ID={spreadsheet_id}")
        print("ENABLE_GOOGLE_SHEETS=true")
        return False

def print_credentials_instructions():
    """Print instructions for setting up Google Cloud credentials."""
    print("\n=== INSTRUCCIONES PARA CONFIGURAR CREDENCIALES ===")
    print("\n1. Ve a la Consola de Google Cloud (https://console.cloud.google.com/)")
    print("2. Crea un nuevo proyecto o selecciona uno existente")
    print("3. Habilita las siguientes APIs:")
    print("   - Google Sheets API")
    print("   - Google Drive API")
    print("4. Crea una cuenta de servicio:")
    print("   - Ve a 'IAM y Administración' > 'Cuentas de servicio'")
    print("   - Haz clic en 'Crear cuenta de servicio'")
    print("   - Nombra tu cuenta de servicio (ej. 'scrapermpv')")
    print("   - Asigna el rol 'Editor' (o un rol personalizado con permisos adecuados)")
    print("5. Crea una clave para la cuenta de servicio:")
    print("   - Haz clic en la cuenta de servicio")
    print("   - Ve a la pestaña 'Claves'")
    print("   - Haz clic en 'Agregar clave' > 'Crear nueva clave'")
    print("   - Selecciona formato JSON y haz clic en 'Crear'")
    print("   - Guarda el archivo descargado en una ubicación segura")
    print("6. Coloca el archivo de credenciales en la carpeta 'config' del proyecto")
    print("   O establece la ruta completa en la variable de entorno GOOGLE_SERVICE_ACCOUNT_FILE")

def print_api_instructions(project_id):
    """Print instructions for enabling required APIs."""
    console_url = f"https://console.cloud.google.com/apis/library?project={project_id}" if project_id else "https://console.cloud.google.com/apis/library"
    
    print("\n=== HABILITAR APIS REQUERIDAS ===")
    print(f"\nVe a la Biblioteca de APIs en la Consola de Google Cloud: {console_url}")
    print("\nBusca y habilita las siguientes APIs:")
    print("1. Google Sheets API")
    print("2. Google Drive API")
    print("\nPasos:")
    print("- Busca cada API por nombre")
    print("- Haz clic en la API")
    print("- Haz clic en el botón 'Habilitar'")
    print("- Espera unos minutos para que se activen los cambios")
    print("\nUna vez habilitadas las APIs, vuelve a ejecutar este script.")

if __name__ == "__main__":
    main()
