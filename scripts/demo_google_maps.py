#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Demo for Google Maps Scraper

Este script ejecuta una demostración completa del Google Maps Scraper,
mostrando todas las características implementadas en la Tarea #3.
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scrapers.google_maps_scraper import GoogleMapsScraper
from utils.helpers import create_logger

# Configuración de logger
logger = create_logger('demo_gmaps', log_file='logs/demo_gmaps.log')

# Ejemplos de consultas para diferentes países de LATAM
DEMO_SEARCHES = [
    {"query": "restaurantes", "location": "Ciudad de México, México", "max_results": 5},
    {"query": "hoteles", "location": "Buenos Aires, Argentina", "max_results": 5},
    {"query": "cafeterías", "location": "Santiago, Chile", "max_results": 5},
    {"query": "gimnasios", "location": "Bogotá, Colombia", "max_results": 5},
    {"query": "supermercados", "location": "Lima, Perú", "max_results": 5}
]

def save_results(results, query, location):
    """Guardar resultados en un archivo JSON."""
    # Crear nombre de archivo con la consulta y ubicación
    safe_query = query.replace(" ", "_")
    safe_location = location.replace(" ", "_").replace(",", "")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    filename = f"results_{safe_query}_{safe_location}_{timestamp}.json"
    
    # Guardar en el directorio results
    results_dir = os.path.join(project_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    filepath = os.path.join(results_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Guardados {len(results)} resultados en {filepath}")
    return filepath

def print_business_summary(business):
    """Imprimir un resumen de un negocio."""
    print(f"\n{'=' * 50}")
    print(f"Nombre: {business.get('name', 'No disponible')}")
    print(f"Dirección: {business.get('address', 'No disponible')}")
    print(f"Teléfono: {business.get('phone', 'No disponible')}")
    print(f"Sitio web: {business.get('website', 'No disponible')}")
    print(f"Valoración: {business.get('rating', 'No disponible')} ({business.get('reviews_count', '0')} reseñas)")
    print(f"Categorías: {business.get('categories', 'No disponible')}")
    print(f"{'=' * 50}\n")

def run_demo():
    """Ejecutar la demostración del Google Maps Scraper."""
    print("\n" + "=" * 80)
    print("DEMO DEL GOOGLE MAPS SCRAPER PARA LATAM".center(80))
    print("=" * 80 + "\n")
    
    print("Este demo ejecutará búsquedas en diferentes países de LATAM")
    print("para demostrar las capacidades del scraper de Google Maps.\n")
    
    # Crear instancia del scraper
    scraper = GoogleMapsScraper(
        request_delay=3.0,
        random_delay_range=(2.0, 5.0),
        headless=False,  # Mostrar el navegador para la demostración
        use_undetected_driver=False  # Usar Selenium regular para mejor compatibilidad
    )
    
    try:
        total_found = 0
        
        for i, search in enumerate(DEMO_SEARCHES, 1):
            query = search["query"]
            location = search["location"]
            max_results = search["max_results"]
            
            print(f"\n[{i}/{len(DEMO_SEARCHES)}] Buscando: '{query}' en '{location}'")
            logger.info(f"Ejecutando búsqueda: {query} en {location}")
            
            # Ejecutar la búsqueda
            scraper.max_results = max_results  # Limitar resultados para demo
            results = scraper.scrape(query, location)
            
            # Mostrar resultados
            print(f"\nEncontrados {len(results)} negocios:")
            
            for j, business in enumerate(results[:3], 1):
                print_business_summary(business)
                
            if len(results) > 3:
                print(f"... y {len(results) - 3} negocios más")
                
            # Guardar resultados
            if results:
                filepath = save_results(results, query, location)
                print(f"\nResultados guardados en: {os.path.basename(filepath)}")
                
            total_found += len(results)
            
            # Pausa entre búsquedas
            if i < len(DEMO_SEARCHES):
                print("\nEsperando antes de la siguiente búsqueda...")
                time.sleep(5)
        
        print("\n" + "=" * 80)
        print(f"DEMO COMPLETADO: Se encontraron {total_found} negocios en total".center(80))
        print("=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrumpido por el usuario")
    except Exception as e:
        print(f"\n\nError durante la ejecución del demo: {str(e)}")
        logger.error(f"Error en demo: {str(e)}")
    finally:
        # Siempre cerrar el navegador al finalizar
        scraper.close()
        logger.info("Demo finalizado")

if __name__ == "__main__":
    # Crear directorio para resultados si no existe
    os.makedirs(os.path.join(project_root, "results"), exist_ok=True)
    
    # Ejecutar demo
    run_demo()
