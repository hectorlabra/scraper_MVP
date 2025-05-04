#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Scraper CLI

Command line interface for the Instagram Scraper.
"""

import os
import sys
import argparse
import logging
import json
import csv
from datetime import datetime
from typing import List, Dict, Any

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.instagram_scraper import InstagramScraper
from utils.helpers import setup_logger

def save_results(results: List[Dict[str, Any]], output_file: str, format: str = 'json') -> None:
    """
    Save the scraping results to a file.
    
    Args:
        results: List of business data dictionaries
        output_file: Path to output file
        format: Output format ('json' or 'csv')
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if format.lower() == 'json':
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif format.lower() == 'csv':
        if not results:
            print(f"No results to save to {output_file}")
            return
            
        # Get all possible field names across all results
        fieldnames = set()
        for result in results:
            fieldnames.update(result.keys())
            
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
            writer.writeheader()
            writer.writerows(results)
    else:
        raise ValueError(f"Unsupported output format: {format}")
    
    print(f"Saved {len(results)} results to {output_file}")

def main():
    """Main entry point for Instagram scraper CLI."""
    parser = argparse.ArgumentParser(description='Scrape business profiles from Instagram.')
    
    # Required arguments
    parser.add_argument('-u', '--username', help='Instagram username')
    parser.add_argument('-p', '--password', help='Instagram password')
    
    # Search options (at least one is required)
    search_group = parser.add_argument_group('search options (at least one required)')
    search_group.add_argument('--hashtag', help='Hashtag to search (without # symbol)')
    search_group.add_argument('--location', help='Location ID to search')
    
    # Optional arguments
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of results (default: 50)')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds (default: 2.0)')
    parser.add_argument('--output', help='Output file path (default: results/instagram_YYYYMMDD.json)')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format (default: json)')
    parser.add_argument('--session-path', help='Path to save/load session cookies')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger('instagram_scraper', level=log_level)
    
    # Validate arguments
    if not args.hashtag and not args.location:
        parser.error("At least one search option (--hashtag or --location) is required")
    
    # Set default output file if not specified
    if not args.output:
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        search_type = 'hashtag_' + args.hashtag if args.hashtag else 'location_' + args.location
        args.output = f"results/instagram_{search_type}_{date_str}.{args.format}"
    
    try:
        # Initialize Instagram scraper
        scraper = InstagramScraper(
            username=args.username,
            password=args.password,
            session_path=args.session_path if args.session_path else None,
            request_delay=args.delay,
            max_results=args.limit
        )
        
        # Login if credentials provided
        if args.username and args.password:
            if not scraper.login():
                logger.error("Failed to login to Instagram")
                sys.exit(1)
        else:
            logger.warning("No login credentials provided, running in anonymous mode with limited capabilities")
        
        # Perform search based on provided options
        results = []
        if args.hashtag:
            logger.info(f"Searching Instagram for posts with hashtag #{args.hashtag}")
            results = scraper.search_by_hashtag(args.hashtag, args.limit)
        elif args.location:
            logger.info(f"Searching Instagram for posts from location ID {args.location}")
            results = scraper.search_by_location(args.location, args.limit)
        
        # Display results summary
        if results:
            logger.info(f"Found {len(results)} business profiles")
            
            # Print first 3 results as a preview
            for i, result in enumerate(results[:3], 1):
                print(f"\nResult {i}:")
                print(f"- Name: {result.get('name', 'N/A')}")
                print(f"- Username: {result.get('username', 'N/A')}")
                print(f"- Category: {result.get('category', 'N/A')}")
                print(f"- Followers: {result.get('followers', 'N/A')}")
                print(f"- Website: {result.get('website', 'N/A')}")
                print(f"- Phone: {result.get('phone', 'N/A')}")
                print(f"- Email: {result.get('email', 'N/A')}")
            
            # Save results to file
            save_results(results, args.output, args.format)
        else:
            logger.warning("No business profiles found")
        
        # Logout from Instagram
        scraper.logout()
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during Instagram scraping: {e}", exc_info=args.verbose)
        sys.exit(1)

if __name__ == '__main__':
    main()
