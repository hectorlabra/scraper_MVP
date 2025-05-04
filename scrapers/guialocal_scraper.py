#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GuiaLocal Scraper Module

This module provides a scraper class for extracting business data from GuiaLocal directories
in Latin America.
"""

import time
import random
import logging
import re
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import quote_plus, urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException,
    WebDriverException
)
from selenium import webdriver

# Local imports
from scrapers.directory_scraper import DirectoryScraper
from utils.helpers import (
    get_random_user_agent,
    detect_captcha,
    simulate_human_behavior,
    clean_text,
    extract_phone_numbers,
    extract_emails,
    extract_urls
)

logger = logging.getLogger(__name__)

class GuiaLocalScraper(DirectoryScraper):
    """
    Scraper class for extracting business data from GuiaLocal directories
    across Latin America.
    """
    
    def __init__(self, 
                 request_delay: float = 2.0,
                 random_delay_range: Optional[Tuple[float, float]] = (1.0, 3.0),
                 max_results: int = 100,
                 headless: bool = False,
                 country: str = "mx"):  # Default to Mexico
        """
        Initialize the GuiaLocal scraper.
        
        Args:
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
            headless: Whether to run the browser in headless mode
            country: Country code for the specific GuiaLocal website (mx, ar, cl, co, etc.)
        """
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results
        )
        
        self.headless = headless
        self.country = country.lower()
        self._set_base_url()
        
    def _set_base_url(self) -> None:
        """Set the base URL based on the selected country."""
        country_urls = {
            "mx": "https://www.guialocal.com.mx",
            "ar": "https://www.guialocal.com.ar",
            "cl": "https://www.guialocal.com.cl",
            "co": "https://www.guialocal.com.co",
            "pe": "https://www.guialocal.com.pe",
            # Add more country URLs as needed
        }
        
        self.base_url = country_urls.get(self.country, country_urls["mx"])
        logger.info(f"Using GuiaLocal URL for {self.country.upper()}: {self.base_url}")
    
    def build_search_url(self, query: str, location: str = "") -> str:
        """
        Construct the URL for searching the directory.
        
        Args:
            query: Search term (e.g., "restaurantes")
            location: Location to filter results (e.g., "CDMX")
            
        Returns:
            Fully formed search URL
        """
        # Encode the query and location for URL
        encoded_query = quote_plus(query)
        
        # GuiaLocal uses a different URL structure
        if location:
            encoded_location = quote_plus(location)
            search_url = f"{self.base_url}/buscar?q={encoded_query}&qc={encoded_location}"
        else:
            search_url = f"{self.base_url}/buscar?q={encoded_query}"
        
        return search_url
    
    def _ensure_driver(self) -> bool:
        """Ensure the browser driver is initialized."""
        if self.driver is None:
            try:
                options = webdriver.ChromeOptions()
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-notifications")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument(f"--user-agent={get_random_user_agent()}")
                
                if self.headless:
                    options.add_argument("--headless")
                
                self.driver = webdriver.Chrome(options=options)
                self.driver.set_page_load_timeout(30)
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Chrome driver: {e}")
                return False
        return True
    
    def get_listings(self) -> List[Any]:
        """
        Retrieve the current page's listing elements.
        
        Returns:
            List of WebElement objects representing business listings
        """
        try:
            # Wait for listings container to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".search-results, .results-list, .companies"))
            )
            
            # Try different selectors for listing items
            listing_selectors = [
                ".company-item", 
                ".search-item",
                ".business-listing",
                ".result-item",
                "[data-testid='company-item']"
            ]
            
            for selector in listing_selectors:
                listings = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if listings:
                    logger.info(f"Found {len(listings)} listings using selector: {selector}")
                    return listings
            
            # If no listings found with the primary selectors, try more generic ones
            logger.warning("No listings found with primary selectors, trying alternatives")
            alternative_selector = "div[class*='company'], div[class*='business'], div[class*='result']"
            listings = self.driver.find_elements(By.CSS_SELECTOR, alternative_selector)
            
            return listings
        except Exception as e:
            logger.error(f"Error getting GuiaLocal listings: {e}")
            return []
    
    def parse_listing(self, html_element) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing element and extract business data.
        
        Args:
            html_element: Selenium WebElement representing a listing
            
        Returns:
            Dictionary with business data or None if parsing fails
        """
        try:
            business_data = {
                "source": f"guialocal_{self.country}",
                "scrape_date": time.strftime("%Y-%m-%d"),
                "name": None,
                "address": None,
                "phone": None,
                "website": None,
                "email": None,
                "category": None,
                "description": None,
                "rating": None,
                "review_count": None,
                "social_media": {}
            }
            
            # Extract business name
            name_selectors = [
                ".company-name", ".name", "h2", ".title",
                "[data-testid='company-name']", ".business-name"
            ]
            
            for selector in name_selectors:
                try:
                    name_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["name"] = clean_text(name_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract address
            address_selectors = [
                ".company-address", ".address", ".location",
                "[data-testid='company-address']", ".business-address"
            ]
            
            for selector in address_selectors:
                try:
                    address_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["address"] = clean_text(address_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract phone
            phone_selectors = [
                ".company-phone", ".phone", ".tel",
                "[data-testid='company-phone']", ".business-phone"
            ]
            
            # Try explicit selectors first
            for selector in phone_selectors:
                try:
                    phone_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["phone"] = clean_text(phone_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # If no explicit phone element, try to extract from all text
            if not business_data["phone"]:
                all_text = html_element.text
                phones = extract_phone_numbers(all_text)
                if phones:
                    business_data["phone"] = phones[0]  # Use the first extracted phone
            
            # Extract website
            website_selectors = [
                ".company-website", ".website", "a.web", 
                "[data-testid='company-website']", ".business-website",
                "a[target='_blank'][href^='http']"
            ]
            
            for selector in website_selectors:
                try:
                    website_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    website_url = website_elem.get_attribute("href")
                    
                    # Check if it's an external link and not an internal page
                    if website_url and not website_url.startswith(self.base_url):
                        business_data["website"] = website_url
                    # Check for redirect URLs
                    elif website_url and "/redirect/" in website_url:
                        business_data["website"] = website_url
                    break
                except NoSuchElementException:
                    continue
            
            # Extract email from text or elements
            email_selectors = [
                ".company-email", ".email", 
                "[data-testid='company-email']", ".business-email"
            ]
            
            for selector in email_selectors:
                try:
                    email_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    email_text = email_elem.text
                    emails = extract_emails(email_text)
                    if emails:
                        business_data["email"] = emails[0]
                    break
                except NoSuchElementException:
                    continue
            
            # If no explicit email element, try to extract from all text
            if not business_data["email"]:
                all_text = html_element.text
                emails = extract_emails(all_text)
                if emails:
                    business_data["email"] = emails[0]
            
            # Extract category
            category_selectors = [
                ".company-category", ".category", ".segment",
                "[data-testid='company-category']", ".business-category"
            ]
            
            for selector in category_selectors:
                try:
                    category_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["category"] = clean_text(category_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract description (if available)
            description_selectors = [
                ".company-description", ".description", ".snippet",
                "[data-testid='company-description']", ".business-description"
            ]
            
            for selector in description_selectors:
                try:
                    desc_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["description"] = clean_text(desc_elem.text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract rating (if available)
            rating_selectors = [
                ".company-rating", ".rating", ".stars",
                "[data-testid='company-rating']", ".rating-stars"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    
                    # Try to extract numeric rating
                    rating_text = rating_elem.text
                    if rating_text:
                        # Extract numeric values from rating text
                        rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                        if rating_match:
                            business_data["rating"] = float(rating_match.group(1))
                    
                    # Alternative: Try to extract from star class or attributes
                    if not business_data["rating"]:
                        # Some sites use class names or data attributes for ratings
                        rating_value = rating_elem.get_attribute("data-rating")
                        if rating_value:
                            try:
                                business_data["rating"] = float(rating_value)
                            except ValueError:
                                pass
                    
                    break
                except NoSuchElementException:
                    continue
            
            # Return only if we have at least a name or a phone
            if business_data["name"] or business_data["phone"]:
                return business_data
            else:
                logger.warning("Skipping GuiaLocal listing - could not extract name or phone")
                return None
            
        except Exception as e:
            logger.error(f"Error parsing GuiaLocal listing: {e}")
            return None
    
    def handle_pagination(self) -> bool:
        """
        Go to the next page of results if available.
        
        Returns:
            True if successfully navigated to next page, False otherwise
        """
        try:
            # Look for pagination controls
            pagination_selectors = [
                "a.next", ".pagination a[rel='next']", 
                ".next-page", "[data-testid='pagination-next']",
                "a[aria-label='Siguiente']", ".pagination a.next",
                "ul.pagination li.next a"
            ]
            
            for selector in pagination_selectors:
                try:
                    next_page = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_page.is_displayed() and next_page.is_enabled():
                        logger.info("Navigating to next page in GuiaLocal")
                        next_page.click()
                        # Wait for the new page to load
                        time.sleep(random.uniform(*self.random_delay_range))
                        return True
                except NoSuchElementException:
                    continue
                except ElementNotInteractableException:
                    logger.warning("Next page button is not interactive")
                    continue
            
            logger.info("No more GuiaLocal pages available or next button not found")
            return False
            
        except Exception as e:
            logger.error(f"Error handling GuiaLocal pagination: {e}")
            return False
    
    def scrape(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Core scraping method for GuiaLocal.
        Overrides the base method to add pagination handling.
        
        Args:
            query: Search term (e.g., "restaurantes")
            location: Location filter (e.g., "CDMX")
            
        Returns:
            List of dictionaries with scraped data
        """
        self.results = []
        try:
            url = self.build_search_url(query, location)
            logger.info(f"Navigating to GuiaLocal: {url}")
            if not self._ensure_driver():
                return []
            
            # Navigate to the search URL
            self.driver.get(url)
            time.sleep(random.uniform(*self.random_delay_range))
            
            # Check for CAPTCHA
            if detect_captcha(self.driver.page_source):
                logger.warning("CAPTCHA detected on initial GuiaLocal page load")
                # Here you could implement CAPTCHA handling or notify the user
                # For now, we'll just return an empty result
                return []
            
            # Process first page
            page = 1
            max_pages = 10  # Limit to prevent infinite loops
            
            while page <= max_pages and len(self.results) < self.max_results:
                logger.info(f"Processing GuiaLocal page {page}")
                
                # Get and process listings
                listings = self.get_listings()
                if not listings:
                    logger.warning(f"No listings found on GuiaLocal page {page}")
                    break
                
                # Process each listing on the current page
                for count, listing in enumerate(listings, 1):
                    if len(self.results) >= self.max_results:
                        logger.info(f"Reached maximum results limit ({self.max_results})")
                        break
                    
                    # Extract data from listing
                    data = self.parse_listing(listing)
                    if data:
                        self.results.append(data)
                    
                    # Add random delay between processing listings
                    time.sleep(random.uniform(0.5, 1.5))
                
                # Try to go to next page if we haven't reached the max results
                if len(self.results) < self.max_results:
                    if not self.handle_pagination():
                        logger.info("No more GuiaLocal pages available")
                        break
                    page += 1
                    # Add delay between pages
                    time.sleep(random.uniform(*self.random_delay_range))
            
            # Clean the results
            self.clean_results()
            logger.info(f"Scraped {len(self.results)} listings from GuiaLocal {self.country.upper()}")
            return self.results
            
        except Exception as e:
            logger.error(f"Error scraping GuiaLocal: {e}")
            return []
        finally:
            # Close the driver when done
            if self.driver:
                self.driver.quit()
                self.driver = None
