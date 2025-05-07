#!/usr/bin/env python3

"""
Script para verificar la funcionalidad del ValidationProcessor
"""

import os
import sys
import pandas as pd

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importar ValidationProcessor
from processing.data_processor import ValidationProcessor

def main():
    # Crear datos de prueba
    data = [
        {
            "business_name": "Alpha Technologies",
            "phone": "+52 55 1234 5678",
            "email": "info@alphatech.com",
            "location": "Mexico City, Mexico",
            "source": "Google Maps"
        },
        {
            "business_name": "Beta Services",
            "phone": "+55 11 91234-5678",
            "email": "contact@betaservices.com.br",
            "location": "São Paulo, Brazil",
            "source": "Google Maps"
        },
        {
            "business_name": "Gamma Solutions",
            "phone": "123456",
            "email": "invalid.email",
            "location": "Buenos Aires, Argentina",
            "source": "Instagram"
        }
    ]
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    print(f"DataFrame original: {len(df)} registros")
    
    # Inicializar ValidationProcessor
    validator = ValidationProcessor(df)
    
    # Validar emails
    print("\nValidando emails...")
    df_with_emails = validator.validate_emails()
    validator.data = df_with_emails
    
    # Validar teléfonos
    print("\nValidando teléfonos...")
    df_with_phones = validator.validate_phone_numbers()
    validator.data = df_with_phones
    
    # Procesar el dataset completo
    print("\nProcesando dataset completo...")
    processed_df = validator.process()
    
    # Mostrar resultados
    print("\nResultados de la validación:")
    print(processed_df[["business_name", "email", "phone", "email_valid", "phone_valid", "is_valid", "validation_score"]])
    
    # Filtrar por calidad
    print("\nFiltrando por calidad (>=80%)...")
    high_quality = validator.filter_by_quality_score(min_score=80)
    print(f"Registros de alta calidad: {len(high_quality)}")
    print(high_quality[["business_name", "validation_score"]])

if __name__ == "__main__":
    main()
