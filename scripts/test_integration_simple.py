#!/usr/bin/env python3

"""
Script para verificar la integración completa del flujo de trabajo
"""

import os
import sys
import pandas as pd
import json
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importaciones del proyecto
from processing.data_processor import ValidationProcessor
from integrations.google_sheets import GoogleSheetsIntegration

def main():
    print("=== Test de Integración Completa ===\n")
    
    # Crear directorio de resultados si no existe
    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Crear datos de prueba
    test_data = [
        {
            "business_name": "Alpha Technologies",
            "phone": "+52 55 1234 5678",
            "email": "info@alphatech.com",
            "location": "Mexico City, Mexico",
            "website": "https://www.alphatech.com",
            "industry": "Technology",
            "description": "Leading technology provider in LATAM",
            "source": "Google Maps"
        },
        {
            "business_name": "Beta Services",
            "phone": "+55 11 91234-5678",
            "email": "contact@betaservices.com.br",
            "location": "São Paulo, Brazil",
            "website": "https://betaservices.com.br",
            "industry": "Consulting",
            "description": "Business consulting services",
            "source": "Google Maps"
        },
        {
            "business_name": "Gamma Solutions",
            "phone": "123456",
            "email": "invalid.email",
            "location": "Buenos Aires, Argentina",
            "website": "",
            "industry": "IT Services",
            "description": "",
            "source": "Instagram"
        },
        {
            "business_name": "Delta Inc.",
            "phone": "+56 9 8765 4321",
            "email": "sales@delta-corp.com",
            "location": "Santiago, Chile",
            "website": "http://delta-inc.com",
            "industry": "Manufacturing",
            "description": "Manufacturing solutions for industry",
            "source": "Paginas Amarillas"
        },
        {
            "business_name": "Test Company",
            "phone": "not-a-phone",
            "email": "test@test.com",
            "location": "Test Location",
            "website": "test.com",
            "industry": "Testing",
            "description": "This is a test company",
            "source": "Cylex"
        }
    ]
    
    # Crear DataFrame
    df = pd.DataFrame(test_data)
    print(f"DataFrame original: {len(df)} registros")
    
    # 1. Deduplicación básica
    print("\n- Paso 1: Deduplicación básica")
    original_len = len(df)
    df = df.drop_duplicates(subset=["business_name", "email", "phone"], keep="first")
    print(f"  Registros después de deduplicación: {len(df)} (eliminados {original_len - len(df)})")
    
    # 2. Validación con ValidationProcessor
    print("\n- Paso 2: Validación con ValidationProcessor")
    validator = ValidationProcessor(df)
    
    # 2.1 Validar emails
    print("  Validando emails...")
    df_with_emails = validator.validate_emails()
    valid_emails = df_with_emails['email_valid'].sum() if 'email_valid' in df_with_emails.columns else 0
    print(f"  Emails válidos: {valid_emails} de {len(df_with_emails)}")
    
    # Actualizar data con resultados de validación
    validator.data = df_with_emails
    
    # 2.2 Validar teléfonos
    print("  Validando teléfonos...")
    df_with_phones = validator.validate_phone_numbers()
    valid_phones = df_with_phones['phone_valid'].sum() if 'phone_valid' in df_with_phones.columns else 0
    print(f"  Teléfonos válidos: {valid_phones} de {len(df_with_phones)}")
    
    # Actualizar data con resultados de validación
    validator.data = df_with_phones
    
    # 2.3 Procesar dataset completo
    print("  Procesando dataset completo...")
    processed_df = validator.process()
    valid_records = processed_df['is_valid'].sum() if 'is_valid' in processed_df.columns else 0
    print(f"  Registros válidos: {valid_records} de {len(processed_df)}")
    
    # 2.4 Filtrar por calidad
    threshold = 70
    print(f"  Filtrando por calidad (>={threshold}%)...")
    filtered_df = validator.filter_by_quality_score(min_score=threshold)
    print(f"  Registros de alta calidad: {len(filtered_df)} de {len(processed_df)}")
    
    # 3. Guardar resultados localmente
    print("\n- Paso 3: Guardando resultados localmente")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(results_dir, f"integration_test_results_{timestamp}.csv")
    filtered_df.to_csv(output_path, index=False)
    print(f"  Resultados guardados en: {output_path}")
    
    # 4. Mostrar algunos resultados
    print("\n- Resultados finales:")
    if len(filtered_df) > 0:
        print(filtered_df[["business_name", "email", "phone", "validation_score"]].head())
    else:
        print("  No hay registros que cumplan con los criterios de calidad.")
    
    print("\nPrueba de integración completada exitosamente!")

if __name__ == "__main__":
    main()
