#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets Optimized Demo

Este script demuestra las nuevas funcionalidades de optimización y caché
agregadas a la clase GoogleSheetsIntegration.
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
import time

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrations.google_sheets import GoogleSheetsIntegration, PermissionType


def main():
    """Run the demo script."""
    # Load environment variables from .env file
    load_dotenv()
    
    print("===== Google Sheets Optimized Features Demo =====\n")
    
    # Initialize the integration with caching enabled
    print("1. Inicializando GoogleSheetsIntegration con caché activado...")
    sheets = GoogleSheetsIntegration(enable_caching=True)
    
    # Authenticate with Google Sheets API
    print("\n2. Autenticando con Google Sheets API...")
    try:
        success = sheets.authenticate()
        if success:
            print("✓ Autenticación exitosa")
        else:
            print("✗ Autenticación fallida")
            return
    except Exception as e:
        print(f"✗ Error de autenticación: {str(e)}")
        return
    
    # Create a new spreadsheet (para evitar problemas de permisos)
    print("\n3. Creando una nueva hoja de cálculo...")
    try:
        spreadsheet_id = sheets.create_spreadsheet("Optimized Demo")
        print(f"✓ Hoja de cálculo creada con ID: {spreadsheet_id}")
    except Exception as e:
        print(f"✗ Error al crear la hoja de cálculo: {str(e)}")
        return
    
    # Prepare demo data
    print("\n4. Preparando datos de ejemplo...")
    data1 = pd.DataFrame({
        'Nombre': ['Juan Pérez', 'Ana García', 'Carlos Rodríguez'],
        'Email': ['juan@ejemplo.com', 'ana@ejemplo.com', 'carlos@ejemplo.com'],
        'Puntuación': [85, 92, 78],
        'Ubicación': ['Madrid', 'Barcelona', 'Valencia']
    })
    print(data1)
    
    # Upload data using standard method
    print("\n5. Subiendo datos con método estándar...")
    start_time = time.time()
    try:
        sheets.upload_data(data1, "Estándar")
        elapsed_time = time.time() - start_time
        print(f"✓ Datos subidos correctamente en {elapsed_time:.2f} segundos")
    except Exception as e:
        print(f"✗ Error al subir datos: {str(e)}")
    
    # Upload data using optimized method
    print("\n6. Subiendo los mismos datos con método optimizado...")
    start_time = time.time()
    try:
        stats = sheets.upload_data_optimized(data1, "Optimizado")
        elapsed_time = time.time() - start_time
        print(f"✓ Datos subidos correctamente en {elapsed_time:.2f} segundos")
        print(f"  - Celdas añadidas: {stats.get('added', 0)}")
        print(f"  - Celdas actualizadas: {stats.get('updated', 0)}")
        print(f"  - Celdas sin cambios: {stats.get('unchanged', 0)}")
    except Exception as e:
        print(f"✗ Error al subir datos: {str(e)}")
    
    # Demonstrate caching
    print("\n7. Demostrando el caché de worksheets...")
    print("  - Primera llamada a get_worksheet (debe acceder a la API):")
    start_time = time.time()
    sheets.get_worksheet("Optimizado")
    elapsed_time = time.time() - start_time
    print(f"    Tiempo: {elapsed_time:.4f} segundos")
    
    print("  - Segunda llamada a get_worksheet (debe usar caché):")
    start_time = time.time()
    sheets.get_worksheet("Optimizado")
    elapsed_time = time.time() - start_time
    print(f"    Tiempo: {elapsed_time:.4f} segundos")
    
    # Modify some data and demonstrate change detection
    print("\n8. Modificando solo un dato y demostrando detección de cambios...")
    data2 = data1.copy()
    data2.loc[1, 'Puntuación'] = 95  # Cambiar puntuación de Ana
    print(data2)
    
    print("\n9. Subiendo datos modificados con método optimizado:")
    try:
        stats = sheets.upload_data_optimized(data2, "Optimizado", detect_changes=True)
        print(f"✓ Datos actualizados correctamente")
        print(f"  - Celdas añadidas: {stats.get('added', 0)}")
        print(f"  - Celdas actualizadas: {stats.get('updated', 0)}")
        print(f"  - Celdas sin cambios: {stats.get('unchanged', 0)}")
    except Exception as e:
        print(f"✗ Error al actualizar datos: {str(e)}")
    
    # Clear cache and verify
    print("\n10. Limpiando caché y verificando diferencia de tiempo...")
    sheets.clear_cache()
    print("  - Caché borrado. Primera llamada después de borrar:")
    start_time = time.time()
    sheets.get_worksheet("Optimizado")
    elapsed_time = time.time() - start_time
    print(f"    Tiempo: {elapsed_time:.4f} segundos")
    
    # Verify API access
    print("\n11. Verificando acceso a APIs...")
    api_status = sheets.check_api_access()
    print(f"  - Google Sheets API: {'✓ Accesible' if api_status['sheets'] else '✗ No accesible'}")
    print(f"  - Google Drive API: {'✓ Accesible' if api_status['drive'] else '✗ No accesible'}")
    
    # Share with a user
    print("\n12. ¿Quieres compartir esta hoja de cálculo?")
    share = input("  - Escribe un email para compartir (Enter para omitir): ")
    if share:
        try:
            sheets.share_spreadsheet(share, PermissionType.WRITER)
            print(f"✓ Hoja compartida con {share}")
        except Exception as e:
            print(f"✗ Error al compartir: {str(e)}")
    
    # Done
    print("\n===== Demostración completada =====")
    print(f"Puedes acceder a la hoja en: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")


if __name__ == '__main__':
    main()
