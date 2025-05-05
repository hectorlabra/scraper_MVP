#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Este script comparte una hoja de cálculo de Google con la cuenta de servicio para que pueda acceder.
Esto es necesario porque las cuentas de servicio no tienen acceso a las hojas de cálculo
a menos que se les otorgue explícitamente.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Añadir el directorio raíz al path de Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrations.google_sheets import GoogleSheetsIntegration, PermissionType

# ID de la hoja de cálculo específica que queremos usar
SPREADSHEET_ID = "1ZccoO_Z7rEMG5MJq48o7eARFvvFIsmXdakAOBtgkPYE"

def main():
    """Comparte la hoja de cálculo con la cuenta de servicio."""
    # Cargar variables de entorno
    load_dotenv()
    
    print("===== Compartir Hoja de Google Sheets con Cuenta de Servicio =====")
    
    # Obtener path del archivo de credenciales
    creds_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    if not creds_file:
        print("Error: GOOGLE_SERVICE_ACCOUNT_FILE no está definido en el entorno.")
        creds_file = input("Introduce la ruta al archivo de credenciales de la cuenta de servicio: ")
    
    # Extraer el email de la cuenta de servicio del archivo de credenciales
    try:
        with open(creds_file, 'r') as f:
            creds_data = json.load(f)
            service_account_email = creds_data.get('client_email')
            if not service_account_email:
                print("Error: No se pudo encontrar el email de la cuenta de servicio en el archivo.")
                return
    except Exception as e:
        print(f"Error al leer el archivo de credenciales: {str(e)}")
        return
    
    print(f"\nEmail de la cuenta de servicio: {service_account_email}")
    print(f"ID de la hoja de cálculo: {SPREADSHEET_ID}")
    
    # Preguntar al usuario si quiere compartir la hoja
    share = input("\n¿Quieres compartir la hoja con esta cuenta de servicio? (s/n): ")
    if share.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
        print("Operación cancelada.")
        return
    
    print("\nCompartiendo hoja de cálculo...")
    
    # Para compartir la hoja, necesitamos usar tus credenciales personales, no las de servicio
    print("\nIMPORTANTE: Necesitas estar autenticado en el navegador con tu cuenta de Google")
    print("y tener permisos de propietario en la hoja de cálculo para compartirla.")
    print("1. Abre este enlace en tu navegador:")
    print(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
    print("2. Haz clic en el botón 'Compartir' en la esquina superior derecha")
    print(f"3. Añade esta dirección: {service_account_email}")
    print("4. Selecciona 'Editor' en el menú desplegable")
    print("5. Haz clic en 'Listo'")
    
    confirmation = input("\n¿Has compartido la hoja manualmente? (s/n): ")
    if confirmation.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        print("\n✓ ¡Perfecto! Ahora la cuenta de servicio tiene acceso a la hoja.")
        print("Puedes ejecutar el script demo_sheets_integration.py para probar la conexión.")
    else:
        print("\n⚠️ Recuerda que la cuenta de servicio necesita acceso a la hoja para poder utilizarla.")

if __name__ == "__main__":
    main()
