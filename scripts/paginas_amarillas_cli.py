#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Páginas Amarillas Scraper CLI

This script provides a command-line interface for the Páginas Amarillas scraper.
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Páginas Amarillas scraper
from scrapers.paginas_amarillas_scraper import PaginasAmarillasScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/paginas_amarillas_cli.log'),
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
    """Main function for the CLI."""
    parser = argparse.ArgumentParser(description='Páginas Amarillas Scraper CLI')
    parser.add_argument('--query', '-q', type=str, required=True, help='Search query (e.g., "restaurantes")')
    parser.add_argument('--location', '-l', type=str, default='', help='Location filter (e.g., "CDMX")')
    parser.add_argument('--country', '-c', type=str, default='mx', help='Country code (default: mx)')
    parser.add_argument('--max-results', '-m', type=int, default=50, help='Maximum results to scrape (default: 50)')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--output', '-o', type=str, help='Output filename (default: paginas_amarillas_[country]_[query].json)')
    
    args = parser.parse_args()
    
    # Determine output filename
    if args.output:
        output_filename = args.output
    else:
        output_filename = f"paginas_amarillas_{args.country}_{args.query.replace(' ', '_')}.json"
    
    logger.info(f"Starting Páginas Amarillas scraper with query: {args.query}, location: {args.location}")
    
    try:
        # Create and run the scraper
        scraper = PaginasAmarillasScraper(
            max_results=args.max_results,
            headless=args.headless,
            country=args.country
        )
        
        results = scraper.scrape(args.query, args.location)
        
        logger.info(f"Found {len(results)} results from Páginas Amarillas")
        
        if results:
            save_results(results, output_filename)
            
        logger.info("Scraping completed successfully")
        
    except Exception as e:
        logger.error(f"Error running Páginas Amarillas scraper: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
