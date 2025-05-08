#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for data quality monitoring.
"""

import os
import sys
import pandas as pd
import logging
import json
from datetime import datetime

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import data quality functions
from utils.data_quality import create_data_quality_monitor, DataQualityConfig
from utils.monitoring import MetricsRegistry

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("data_quality_test")

def main():
    """Test the data quality monitoring functionality."""
    try:
        print("============================================")
        print("INICIANDO PRUEBA DE MONITOREO DE CALIDAD DE DATOS")
        print("============================================")
        logger.info("Testing data quality monitoring")
        
        # Create test data
        test_data = [
            {"business_name": "Good Company", "email": "contact@goodcompany.com", "phone": "+1 555-123-4567", "website": "https://goodcompany.com"},
            {"business_name": "Test Company", "email": "test@example.com", "phone": "12345", "website": "test.com"},
            {"business_name": "Missing Data Corp", "email": "", "phone": "", "website": ""},
            {"business_name": "S", "email": "a@b.c", "phone": "123", "website": "invalid-url"},
            {"business_name": "Duplicate Corp", "email": "info@duplicatecorp.com", "phone": "+1 555-999-8888", "website": "https://duplicatecorp.com"},
            {"business_name": "Duplicate Corp", "email": "info@duplicatecorp.com", "phone": "+1 555-999-8888", "website": "https://duplicatecorp.com"},
        ]
        
        # Convert to DataFrame
        df = pd.DataFrame(test_data)
        
        logger.info(f"Created test dataset with {len(df)} records")
        print("Dataset para prueba:")
        print(df)
        print()
        
        # Initialize metrics registry
        metrics_registry = MetricsRegistry()
        print("Inicializado MetricsRegistry...")
        
        # Check for config file
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "data_quality_config.json")
        if os.path.exists(config_path):
            logger.info(f"Using configuration from {config_path}")
            print(f"Usando archivo de configuración: {config_path}")
        else:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            print(f"¡ADVERTENCIA! Archivo de configuración no encontrado, usando valores predeterminados")
            config_path = None
        
        # Create data quality monitor
        print("Creando monitor de calidad de datos...")
        data_quality_monitor = create_data_quality_monitor(
            metrics_registry=metrics_registry,
            config_path=config_path,
            notification_manager=None  # No notifications for testing
        )
        print("Monitor de calidad de datos creado exitosamente.")
        
        # Process the dataset
        print("Procesando dataset con el monitor de calidad de datos...")
        logger.info("Processing dataset with data quality monitor")
        quality_results = data_quality_monitor.process_dataset(
            df, 
            source_name="test_data", 
            timestamp=datetime.now(),
            export_report=True
        )
        
        # Print results
        print("\nRESULTADOS DE LA EVALUACIÓN DE CALIDAD DE DATOS:")
        logger.info("Data quality assessment results:")
        print(json.dumps(quality_results, indent=2, default=str))
        
        # Print quality score
        if "overall_score" in quality_results:
            score_msg = f"Calificación general de calidad de datos: {quality_results['overall_score']:.2f}/100"
            logger.info(score_msg)
            print("\n" + "="*len(score_msg))
            print(score_msg)
            print("="*len(score_msg))
        
        # Check if any suspicious records were found
        if "suspicious_records" in quality_results and quality_results["suspicious_records"]:
            msg = f"Se encontraron {len(quality_results['suspicious_records'])} registros sospechosos:"
            logger.info(msg)
            print("\n" + msg)
            for idx, record in enumerate(quality_results["suspicious_records"]):
                print(f"Registro sospechoso #{idx+1}: {record}")
        
        print("\nPrueba de calidad de datos completada con éxito!")
        logger.info("Data quality test completed")
        
        return 0
    except Exception as e:
        import traceback
        print(f"ERROR durante la prueba: {str(e)}")
        print(traceback.format_exc())
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
