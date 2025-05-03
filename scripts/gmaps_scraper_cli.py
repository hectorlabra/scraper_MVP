#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Maps Scraper CLI

This script provides a command-line interface for the Google Maps scraper.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scrapers.google_maps_scraper import GoogleMapsScraper
from utils.helpers import create_logger

# Setup logger
logger = create_logger('gmaps_cli', log_file='logs/gmaps_cli.log')

def save_results(results, output_file=None):
    """
    Save results to a JSON file.
    
    Args:
        results: List of scraped business data
        output_file: Output filename (default: generates one based on date/time)
    """
    if not output_file:
        # Generate a default filename based on date and time
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'results_gmaps_{timestamp}.json'
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(results)} results to {output_file}")
    return output_file

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Google Maps Scraper CLI')
    
    # Required arguments
    parser.add_argument('query', help='Search term to look for (e.g., "restaurants")')
    
    # Optional arguments
    parser.add_argument('--location', '-l', help='Location to search within (e.g., "Mexico City")', default='')
    parser.add_argument('--max-results', '-m', type=int, help='Maximum number of results to scrape', default=50)
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--delay', '-d', type=float, help='Delay between actions in seconds', default=3.0)
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--use-undetected', action='store_true', help='Use undetected-chromedriver (more evasive but may have compatibility issues)')
    
    args = parser.parse_args()
    
    # Set log level based on debug flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Starting Google Maps scraper with query: '{args.query}', location: '{args.location}'")
    
    # Create and configure the scraper
    scraper = GoogleMapsScraper(
        max_results=args.max_results,
        headless=args.headless,
        request_delay=args.delay,
        use_undetected_driver=args.use_undetected
    )
    
    try:
        # Run the scraper
        logger.info("Starting scraping process...")
        results = scraper.scrape(args.query, args.location)
        
        # Print summary
        logger.info(f"Scraped {len(results)} businesses")
        
        # Save results
        if results:
            output_file = save_results(results, args.output)
            print(f"\nResults saved to: {output_file}")
            print(f"Found {len(results)} businesses")
        else:
            print("No results found")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        logger.warning("Scraping interrupted by user")
    except Exception as e:
        print(f"\nError during scraping: {str(e)}")
        logger.error(f"Error during scraping: {str(e)}")
    finally:
        # Always clean up
        scraper.close()
        logger.info("Scraping process completed")

if __name__ == "__main__":
    main()
