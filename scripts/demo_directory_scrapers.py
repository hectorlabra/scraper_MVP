#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Directory Scrapers Demo Script

This script demonstrates the use of the directory scrapers for Páginas Amarillas, Cylex, and GuiaLocal.
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the directory scrapers
from scrapers.paginas_amarillas_scraper import PaginasAmarillasScraper
from scrapers.cylex_scraper import CylexScraper
from scrapers.guialocal_scraper import GuiaLocalScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/directory_scrapers_demo.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def save_results(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Save scraped results to a JSON file.
    
    Args:
        data: List of dictionaries with scraped data
        filename: Name of the file to save to
    """
    # Create the output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    filepath = os.path.join('output', filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(data)} results to {filepath}")

def main():
    """Main function to run the demo."""
    parser = argparse.ArgumentParser(description='Directory Scrapers Demo')
    parser.add_argument('--query', '-q', type=str, required=True, help='Search query (e.g., "restaurantes")')
    parser.add_argument('--location', '-l', type=str, default='', help='Location filter (e.g., "CDMX")')
    parser.add_argument('--directory', '-d', type=str, choices=['all', 'paginas-amarillas', 'cylex', 'guialocal'], 
                        default='all', help='Directory to scrape (default: all)')
    parser.add_argument('--country', '-c', type=str, default='mx', help='Country code (default: mx)')
    parser.add_argument('--max-results', '-m', type=int, default=50, help='Maximum results to scrape (default: 50)')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    logger.info(f"Starting directory scrapers demo with query: {args.query}, location: {args.location}")
    
    all_results = []
    
    try:
        # Páginas Amarillas
        if args.directory in ['all', 'paginas-amarillas']:
            logger.info(f"Scraping Páginas Amarillas {args.country.upper()}...")
            paginas_amarillas_scraper = PaginasAmarillasScraper(
                max_results=args.max_results,
                headless=args.headless,
                country=args.country
            )
            paginas_results = paginas_amarillas_scraper.scrape(args.query, args.location)
            logger.info(f"Found {len(paginas_results)} results from Páginas Amarillas")
            
            if paginas_results:
                save_results(
                    paginas_results, 
                    f"paginas_amarillas_{args.country}_{args.query.replace(' ', '_')}.json"
                )
                all_results.extend(paginas_results)
        
        # Cylex
        if args.directory in ['all', 'cylex']:
            logger.info(f"Scraping Cylex {args.country.upper()}...")
            cylex_scraper = CylexScraper(
                max_results=args.max_results,
                headless=args.headless,
                country=args.country
            )
            cylex_results = cylex_scraper.scrape(args.query, args.location)
            logger.info(f"Found {len(cylex_results)} results from Cylex")
            
            if cylex_results:
                save_results(
                    cylex_results, 
                    f"cylex_{args.country}_{args.query.replace(' ', '_')}.json"
                )
                all_results.extend(cylex_results)
        
        # GuiaLocal
        if args.directory in ['all', 'guialocal']:
            logger.info(f"Scraping GuiaLocal {args.country.upper()}...")
            guialocal_scraper = GuiaLocalScraper(
                max_results=args.max_results,
                headless=args.headless,
                country=args.country
            )
            guialocal_results = guialocal_scraper.scrape(args.query, args.location)
            logger.info(f"Found {len(guialocal_results)} results from GuiaLocal")
            
            if guialocal_results:
                save_results(
                    guialocal_results, 
                    f"guialocal_{args.country}_{args.query.replace(' ', '_')}.json"
                )
                all_results.extend(guialocal_results)
        
        # Save combined results if we scraped multiple directories
        if args.directory == 'all' and all_results:
            save_results(
                all_results, 
                f"all_directories_{args.country}_{args.query.replace(' ', '_')}.json"
            )
            
        logger.info(f"Demo completed. Total results: {len(all_results)}")
        
    except Exception as e:
        logger.error(f"Error running demo: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
