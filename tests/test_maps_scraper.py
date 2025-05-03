#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for Google Maps Scraper

This script demonstrates the basic usage of the GoogleMapsScraper.
"""

import json
import logging
import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Now import our modules
from scrapers.google_maps_scraper import GoogleMapsScraper
from utils.helpers import create_logger

# Create a logger for test
logger = create_logger("test_googlemaps", log_file="logs/test_maps_scraper.log")

# Test locations for Latin America
TEST_SEARCHES = [
    {"query": "restaurantes", "location": "Ciudad de México, México"},
    {"query": "hoteles", "location": "Buenos Aires, Argentina"},
    {"query": "cafeterías", "location": "Santiago, Chile"}
]

def save_results_to_json(results, filename):
    """Save scraping results to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(results)} results to {filename}")

def main():
    """Run a test scrape with the GoogleMapsScraper."""
    logger.info("Starting Google Maps Scraper test")
    
    # Create a scraper instance
    # Note: headless=False lets you see the browser in action
    # Set use_undetected_driver=False to use regular Selenium for better compatibility
    scraper = GoogleMapsScraper(
        max_results=5,          # Limit to 5 results for the test
        headless=False,         # Keep browser visible for demonstration
        request_delay=2.0,      # Use reasonable delays
        use_undetected_driver=False  # Use regular Selenium for better compatibility
    )
    
    try:
        # Choose one test search
        test_search = TEST_SEARCHES[0]  # Use the first test search
        query = test_search["query"]
        location = test_search["location"]
        
        logger.info(f"Testing search: {query} in {location}")
        print(f"\nBuscando: '{query}' en '{location}'")
        print("Si aparece un CAPTCHA, por favor resuélvalo manualmente en la ventana del navegador.")
        print("El script esperará a que lo resuelva antes de continuar.\n")
        
        # Run the scraper
        results = scraper.scrape(query, location)
        
        # Print results
        if results:
            logger.info(f"Scraped {len(results)} businesses")
            print(f"\nSe encontraron {len(results)} negocios:")
            
            # Print detailed information for each result
            for i, business in enumerate(results, 1):
                print(f"\n{'='*50}")
                print(f"Negocio {i}: {business.get('name', 'Desconocido')}")
                print(f"Dirección: {business.get('address', 'No disponible')}")
                print(f"Teléfono: {business.get('phone', 'No disponible')}")
                print(f"Sitio web: {business.get('website', 'No disponible')}")
                if business.get('rating'):
                    print(f"Valoración: {business.get('rating')} ({business.get('reviews_count', '0')} reseñas)")
                print(f"Categorías: {business.get('categories', 'No disponible')}")
                print(f"{'='*50}")
            
            # Save results to JSON for inspection
            save_results_to_json(results, "test_maps_results.json")
            print(f"\nResultados guardados en test_maps_results.json")
        else:
            print("No se encontraron resultados. Es posible que:")
            print("1. La búsqueda no produjo resultados")
            print("2. Se encontró un CAPTCHA que no se resolvió correctamente")
            print("3. Google bloqueó la solicitud por motivos de seguridad")
    
    except KeyboardInterrupt:
        print("\nPrueba interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        print(f"\nError durante la prueba: {str(e)}")
    
    finally:
        # Always close the scraper to free resources
        print("\nCerrando el navegador...")
        scraper.close()
        logger.info("Test completed")
        print("Prueba completada")

if __name__ == "__main__":
    main()
