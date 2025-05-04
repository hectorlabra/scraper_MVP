#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Scraper Demo

This script demonstrates the use of the Instagram Scraper.
"""

import os
import sys
import logging
import json
from datetime import datetime

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.instagram_scraper import InstagramScraper
from utils.helpers import setup_logger

def main():
    """Main function to demonstrate Instagram scraper."""
    # Set up logging
    logger = setup_logger('instagram_demo', level=logging.INFO)
    logger.info("Starting Instagram Scraper Demo")
    
    # Load Instagram credentials from environment variables
    username = os.environ.get('INSTAGRAM_USERNAME')
    password = os.environ.get('INSTAGRAM_PASSWORD')
    
    if not username or not password:
        logger.warning("Instagram credentials not found in environment variables.")
        logger.warning("Running in anonymous mode with limited capabilities.")
        logger.warning("Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD environment variables for full functionality.")
    
    # Example hashtags and location IDs relevant to LATAM businesses
    latam_hashtags = [
        'negociosmexicanos',
        'emprendedoreslatinos',
        'emprendimientocolombia',
        'negocioschile',
        'pymes',
        'emprendedores',
        'negociosargentina'
    ]
    
    # Sample location IDs (these would need to be updated with actual Instagram location IDs)
    # Finding location IDs requires using the Instagram API or third-party tools
    latam_locations = [
        '111462462',  # Mexico City
        '212999109',  # Buenos Aires
        '624484',     # Lima
        '103644147',  # Bogotá
    ]
    
    try:
        # Initialize Instagram scraper
        scraper = InstagramScraper(
            username=username,
            password=password,
            request_delay=3.0,
            max_results=20
        )
        
        # Try to login if credentials are available
        if username and password:
            login_success = scraper.login()
            if login_success:
                logger.info("Successfully logged in to Instagram")
            else:
                logger.warning("Failed to login to Instagram, continuing in anonymous mode")
        
        # Search by hashtag
        demo_hashtag = latam_hashtags[0]  # Using the first hashtag for demo
        logger.info(f"Searching Instagram for hashtag #{demo_hashtag}")
        
        # Perform the search
        results = scraper.search_by_hashtag(demo_hashtag, post_limit=20)
        
        # Save results to file
        if results:
            logger.info(f"Found {len(results)} business profiles from hashtag #{demo_hashtag}")
            
            # Create results directory if it doesn't exist
            os.makedirs('results', exist_ok=True)
            
            # Save to JSON file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"results/instagram_demo_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved results to {output_file}")
            
            # Print sample results
            logger.info("Sample results:")
            for i, result in enumerate(results[:3], 1):
                logger.info(f"Profile {i}: {result.get('name')} (@{result.get('username')})")
                logger.info(f"  - Category: {result.get('category', 'N/A')}")
                logger.info(f"  - Followers: {result.get('followers', 'N/A')}")
                logger.info(f"  - Website: {result.get('website', 'N/A')}")
                logger.info(f"  - Contact: {result.get('phone', 'N/A') or result.get('email', 'N/A')}")
        else:
            logger.warning(f"No business profiles found for hashtag #{demo_hashtag}")
        
        # If time permits and we're logged in, also demonstrate location search
        if scraper.is_logged_in() and latam_locations:
            demo_location = latam_locations[0]
            logger.info(f"Searching Instagram for posts from location ID {demo_location}")
            
            location_results = scraper.search_by_location(demo_location, post_limit=10)
            
            if location_results:
                logger.info(f"Found {len(location_results)} business profiles from location {demo_location}")
                # Sample results could be shown here
            else:
                logger.warning(f"No business profiles found for location ID {demo_location}")
        
        # Logout from Instagram
        scraper.logout()
        logger.info("Instagram Scraper Demo completed")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during Instagram scraping demo: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
