#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Maps Scraper Module

This module provides a scraper class for extracting business data from Google Maps.
"""

import time
import random
import logging
import re
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementNotInteractableException,
    StaleElementReferenceException,
    WebDriverException
)
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium import webdriver
import undetected_chromedriver as uc
from dotenv import load_dotenv

# Local imports
from scrapers.base_scraper import BaseScraper
from utils.helpers import (
    get_random_user_agent,
    create_logger,
    detect_captcha,
    simulate_human_behavior,
    rate_limit,
    retry_on_failure,
    clean_text,
    extract_phone_numbers,
    extract_emails,
    extract_urls
)

# Load environment variables
load_dotenv()

# Create logger
logger = create_logger(__name__, log_file="logs/google_maps_scraper.log")


class GoogleMapsScraper(BaseScraper):
    """
    Scraper class for extracting business data from Google Maps
    using undetected-chromedriver to avoid detection.
    """
    
    def __init__(self, 
                 request_delay: float = 3.0,
                 random_delay_range: Optional[tuple] = (2.0, 5.0),
                 max_results: int = 100,
                 headless: bool = False,
                 max_retry_count: int = 3,
                 enable_proxies: bool = False,
                 use_undetected_driver: bool = True):
        """
        Initialize the Google Maps scraper with specific configuration.
        
        Args:
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
            headless: Whether to run Chrome in headless mode
            max_retry_count: Maximum number of retries for failed operations
            enable_proxies: Whether to use proxies from environment variables
            use_undetected_driver: Whether to use undetected-chromedriver (more evasive but may have compatibility issues)
        """
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results
        )
        
        self.headless = headless
        self.max_retry_count = max_retry_count
        self.enable_proxies = enable_proxies
        self.use_undetected_driver = use_undetected_driver
        self.driver = None
        self.base_url = "https://www.google.com/maps"
        
        # Track state
        self.is_initialized = False
        self.encountered_captcha = False
        self.processed_items = set()  # Track processed URLs to avoid duplicates
    
    def _initialize_driver(self) -> None:
        """Initialize the browser driver with anti-detection measures."""
        try:
            # For macOS, handle SSL certificate verification issues
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            
            # Get a random user agent
            user_agent = get_random_user_agent()
            
            if self.use_undetected_driver:
                logger.info("Initializing undetected-chromedriver...")
                # Configure Chrome options for undetected-chromedriver
                options = uc.ChromeOptions()
                
                # Add anti-detection measures
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-notifications")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument(f"--user-agent={user_agent}")
                
                # Optional headless mode
                if self.headless:
                    options.add_argument("--headless")
                    
                # Add additional preferences to appear more human-like
                options.add_experimental_option("prefs", {
                    "profile.default_content_setting_values.notifications": 2,
                    "credentials_enable_service": False,
                    "profile.password_manager_enabled": False,
                })
                
                # Try to initialize undetected-chromedriver
                try:
                    # First try with auto-detection
                    self.driver = uc.Chrome(options=options, use_subprocess=True)
                    logger.info("Successfully initialized undetected-chromedriver with auto-detection")
                except Exception as e:
                    logger.warning(f"Auto Chrome version detection failed: {str(e)}")
                    # Try with specific major versions of Chrome
                    versions_to_try = [136, 135, 130, 129, 128, 127, 126, 125, 124, 123, 122]
                    driver_initialized = False
                    
                    for version in versions_to_try:
                        try:
                            logger.info(f"Trying with Chrome version: {version}")
                            self.driver = uc.Chrome(
                                options=options,
                                version_main=version,
                                use_subprocess=True
                            )
                            logger.info(f"Successfully initialized with Chrome version: {version}")
                            driver_initialized = True
                            break
                        except Exception:
                            continue
                    
                    if not driver_initialized:
                        logger.warning("Could not initialize undetected-chromedriver, falling back to regular Selenium")
                        self.use_undetected_driver = False
            
            # Fall back to regular Selenium if undetected-chromedriver fails or is disabled
            if not self.use_undetected_driver:
                logger.info("Initializing regular Selenium ChromeDriver...")
                options = ChromeOptions()
                
                # Basic anti-detection measures for regular Selenium
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-notifications")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument(f"--user-agent={user_agent}")
                
                # Experimental flags to make regular Selenium less detectable
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                
                if self.headless:
                    options.add_argument("--headless")
                
                # Create regular Selenium ChromeDriver
                self.driver = webdriver.Chrome(options=options)
                
                # Apply additional anti-detection measures via JavaScript
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    """
                })
                
            # Set window size
            if self.driver:
                self.driver.set_window_size(1920, 1080)
                self.is_initialized = True
                logger.info("Browser driver initialized successfully")
            else:
                raise Exception("Failed to initialize browser driver")
                
        except Exception as e:
            logger.error(f"Failed to initialize browser driver: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.is_initialized = False
            raise
            
            # Set window size to typical desktop resolution
            self.driver.set_window_size(1920, 1080)
            
            # Add custom JavaScript to modify navigator properties
            # This helps avoid fingerprinting
            self.driver.execute_script("""
                // Override property getters to hide automation
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Modify navigator properties to appear more random
                const overridePlugins = () => {
                    return Array(Math.floor(Math.random() * 5) + 1)
                        .fill()
                        .map(() => ({
                            description: "PDF Viewer",
                            filename: "internal-pdf-viewer",
                            name: "Chrome PDF Viewer"
                        }));
                };
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => overridePlugins()
                });
                
                // Add random values for canvas fingerprinting protection
                const originalGetContext = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function(contextType, ...args) {
                    const context = originalGetContext.call(this, contextType, ...args);
                    if (contextType === '2d') {
                        const originalFillText = context.fillText;
                        context.fillText = function(...args) {
                            args[0] = args[0] + ' '; // Add a small random change
                            return originalFillText.call(this, ...args);
                        };
                    }
                    return context;
                };
            """)
            
            self.is_initialized = True
            logger.info("Initialized undetected-chromedriver successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize undetected-chromedriver: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.is_initialized = False
            raise
    
    def _ensure_driver(self) -> bool:
        """Ensure driver is initialized before operations."""
        if not self.is_initialized or not self.driver:
            try:
                self._initialize_driver()
                return True
            except Exception as e:
                logger.error(f"Could not initialize driver: {str(e)}")
                return False
        return True
    
    def _check_for_captcha(self) -> bool:
        """
        Check if current page contains a CAPTCHA challenge.
        
        Returns:
            True if CAPTCHA is detected, False otherwise
        """
        try:
            if not self.driver:
                return False
                
            # Get page source and check for CAPTCHA markers
            page_source = self.driver.page_source
            if detect_captcha(page_source):
                self.encountered_captcha = True
                logger.warning("CAPTCHA detected! Waiting for manual resolution...")
                
                # Alert user and wait for manual resolution
                if "robot" in page_source.lower() or "captcha" in page_source.lower():
                    print("\n" + "="*60)
                    print("CAPTCHA DETECTADO: Por favor resuelva el CAPTCHA manualmente en la ventana del navegador.")
                    print("Una vez resuelto, pulse ENTER en esta ventana para continuar.")
                    print("="*60 + "\n")
                    
                    # Wait for user to resolve CAPTCHA and press Enter
                    input("Presione ENTER para continuar después de resolver el CAPTCHA...")
                    
                    # Check if CAPTCHA is resolved
                    new_page_source = self.driver.page_source
                    if detect_captcha(new_page_source):
                        logger.warning("CAPTCHA aún no resuelto. Tomando un descanso...")
                        time.sleep(10)
                        return True
                    else:
                        logger.info("CAPTCHA resuelto correctamente. Continuando...")
                        return False
                else:
                    # Take a longer break to avoid getting blocked
                    time.sleep(random.uniform(20, 30))
                    return True
                
            return False
        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {str(e)}")
            return False
    
    def _navigate_to_maps(self) -> bool:
        """
        Navigate to Google Maps and check if the page loaded successfully.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_driver():
            return False
            
        try:
            # Navigate to Google Maps
            self.driver.get(self.base_url)
            
            # Add some random delays and movements to simulate human behavior
            simulate_human_behavior(self.driver, scroll_range=(-100, 100))
            
            # Wait for the search box to be available
            search_box = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            
            # Check for CAPTCHA
            if self._check_for_captcha():
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to Google Maps: {str(e)}")
            return False
    
    def _search(self, query: str, location: str = "") -> bool:
        """
        Perform a search in Google Maps.
        
        Args:
            query: Search term
            location: Optional location to search within
            
        Returns:
            True if search was successful, False otherwise
        """
        if not self._ensure_driver():
            return False
            
        try:
            # Make sure we're on the Maps page
            if self.base_url not in self.driver.current_url:
                if not self._navigate_to_maps():
                    return False
            
            # Construct search query
            search_query = f"{query} {location}".strip()
            logger.info(f"Searching for: {search_query}")
            
            # Simulate some initial page exploration (scroll around, move mouse)
            self._simulate_realistic_scrolling()
            time.sleep(random.uniform(0.5, 1.5))
            
            # Find the search box
            search_box = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, "searchboxinput"))
            )
            
            # Simulate mouse movement to the search box
            self._simulate_mouse_movement(search_box)
            
            # Use human-like typing
            self._simulate_human_typing(search_box, search_query)
            
            # Random pause before hitting enter or clicking search button
            time.sleep(random.uniform(0.5, 1.5))
            
            # Click search button or press Enter with human-like randomness
            if random.random() < 0.7:
                # Method 1: Press Enter key
                search_box.send_keys(Keys.ENTER)
            else:
                # Method 2: Click search button
                search_button = self.driver.find_element(By.ID, "searchbox-searchbutton")
                self._simulate_mouse_movement(search_button)
                time.sleep(random.uniform(0.1, 0.3))
                search_button.click()
            
            # Wait for results to load
            try:
                # Wait for the results list to appear
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
                )
                
                # Add some human-like behavior after results load
                time.sleep(random.uniform(1.0, 2.0))
                
                # Scroll results panel a bit with realistic behavior
                results_panel = self.driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
                self._simulate_realistic_scrolling(results_panel, 2, 4)
                
                # Check for CAPTCHA
                if self._check_for_captcha():
                    return False
                
                # Check if "No results found" appears
                if "No results found" in self.driver.page_source:
                    logger.warning(f"No results found for query: {search_query}")
                    return False
                
                return True
                
            except TimeoutException:
                logger.warning(f"Timeout waiting for search results: {search_query}")
                # Try to determine if any results are showing despite the timeout
                return "cards" in self.driver.page_source.lower()
                
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return False
    
    def _extract_business_data(self, element) -> Optional[Dict[str, Any]]:
        """
        Extract business data from a result element.
        
        Args:
            element: Selenium element representing a business listing
            
        Returns:
            Dictionary of business data or None if extraction failed
        """
        try:
            # Extract initial business data
            business_data = {
                "name": None,
                "address": None,
                "phone": None,
                "website": None,
                "rating": None,
                "reviews_count": None,
                "categories": None,
                "hours": None,
                "place_id": None,
                "location": None,
                "source": "google_maps"
            }
            
            # Get business name
            try:
                name_elem = element.find_element(By.CSS_SELECTOR, "div.fontHeadlineSmall")
                business_data["name"] = clean_text(name_elem.text)
            except (NoSuchElementException, StaleElementReferenceException):
                # Try alternative selectors for name
                try:
                    name_elem = element.find_element(By.CSS_SELECTOR, "h3")
                    business_data["name"] = clean_text(name_elem.text)
                except (NoSuchElementException, StaleElementReferenceException):
                    # If we can't find the name, this isn't a valid business listing
                    return None
            
            # Click on the business listing to get more details
            simulate_human_behavior(self.driver, element, click=True)
            
            # Wait for detailed information panel to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="dialog"]'))
                )
                
                time.sleep(random.uniform(1.0, 3.0))
                
                # Now extract detailed data from the panel
                panel = self.driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"]')
                
                # Extract address
                try:
                    # Look for the "Address" button/element
                    address_elements = panel.find_elements(
                        By.XPATH, 
                        './/button[contains(@data-item-id, "address")]'
                    )
                    if address_elements:
                        business_data["address"] = clean_text(address_elements[0].text)
                except (NoSuchElementException, StaleElementReferenceException):
                    pass
                
                # Extract phone number
                try:
                    # Look for the "Phone" button/element
                    phone_elements = panel.find_elements(
                        By.XPATH, 
                        './/button[contains(@data-item-id, "phone")]'
                    )
                    if phone_elements:
                        business_data["phone"] = clean_text(phone_elements[0].text)
                        # Remove "Phone: " prefix if present
                        if business_data["phone"] and business_data["phone"].lower().startswith("phone:"):
                            business_data["phone"] = business_data["phone"][6:].strip()
                except (NoSuchElementException, StaleElementReferenceException):
                    pass
                
                # Extract website
                try:
                    # Look for the "Website" button/element
                    website_elements = panel.find_elements(
                        By.XPATH, 
                        './/button[contains(@data-item-id, "authority")]'
                    )
                    if website_elements:
                        website_text = clean_text(website_elements[0].text)
                        if website_text and not website_text.lower().startswith('http'):
                            website_text = f"https://{website_text}"
                        business_data["website"] = website_text
                except (NoSuchElementException, StaleElementReferenceException):
                    pass
                
                # Extract rating and reviews count
                try:
                    rating_elements = panel.find_elements(By.CSS_SELECTOR, 'span[role="img"]')
                    if rating_elements:
                        rating_text = rating_elements[0].get_attribute('aria-label')
                        if rating_text:
                            # Extract rating value (e.g., "4.5 stars" -> 4.5)
                            rating_match = re.search(r'(\d+\.\d+)', rating_text)
                            if rating_match:
                                business_data["rating"] = float(rating_match.group(1))
                                
                            # Look for reviews count near the rating
                            reviews_elements = panel.find_elements(
                                By.XPATH,
                                './/span[contains(@aria-label, "stars")]/following-sibling::span'
                            )
                            if reviews_elements:
                                reviews_text = clean_text(reviews_elements[0].text)
                                # Extract number (e.g., "(123 reviews)" -> 123)
                                reviews_match = re.search(r'(\d+)', reviews_text)
                                if reviews_match:
                                    business_data["reviews_count"] = int(reviews_match.group(1))
                except (NoSuchElementException, StaleElementReferenceException):
                    pass
                
                # Extract categories
                try:
                    category_elements = panel.find_elements(
                        By.CSS_SELECTOR,
                        'button[jsaction="pane.rating.category"]'
                    )
                    if category_elements:
                        business_data["categories"] = clean_text(category_elements[0].text)
                except (NoSuchElementException, StaleElementReferenceException):
                    pass
                
                # Extract place ID from URL
                try:
                    current_url = self.driver.current_url
                    place_id_match = re.search(r'place/[^/]+/([^/]+)', current_url)
                    if place_id_match:
                        business_data["place_id"] = place_id_match.group(1)
                except Exception:
                    pass
                
                # Try to close the panel to go back to results
                try:
                    # Find and click the back button
                    back_button = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        'button[aria-label="Back"]'
                    )
                    simulate_human_behavior(self.driver, back_button, click=True)
                    time.sleep(random.uniform(1.0, 2.0))
                except (NoSuchElementException, StaleElementReferenceException):
                    # If we can't find the back button, try hitting escape
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(random.uniform(1.0, 2.0))
                    except Exception:
                        pass
                
                # Filter out None values
                business_data = {k: v for k, v in business_data.items() if v is not None}
                
                # Generate a unique identifier for this business to avoid duplicates
                unique_id = f"{business_data.get('name', '')}-{business_data.get('address', '')}"
                if unique_id in self.processed_items:
                    logger.debug(f"Skipping duplicate business: {business_data.get('name', 'Unknown')}")
                    return None
                
                self.processed_items.add(unique_id)
                return business_data
                
            except TimeoutException:
                logger.warning("Timeout waiting for business details panel")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting business data: {str(e)}")
            return None
    
    def _scroll_for_more_results(self, max_scrolls: int = 10) -> int:
        """
        Scroll through results to load more.
        
        Args:
            max_scrolls: Maximum number of scroll operations
            
        Returns:
            Number of new results found
        """
        try:
            if not self.driver:
                return 0
                
            # Find the results panel
            results_panel = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
            
            # Count initial results
            initial_count = len(self.driver.find_elements(
                By.CSS_SELECTOR, 
                'div[role="feed"] > div'
            ))
            
            # Scroll to load more results
            scroll_count = 0
            last_count = initial_count
            consecutive_no_change = 0
            
            while scroll_count < max_scrolls:
                # Scroll with human-like behavior
                self.driver.execute_script(
                    'arguments[0].scrollTop = arguments[0].scrollHeight', 
                    results_panel
                )
                
                # Add random pause between scrolls
                time.sleep(random.uniform(1.0, 3.0))
                
                # Check if new results loaded
                current_count = len(self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    'div[role="feed"] > div'
                ))
                
                # If no new results after multiple scrolls, stop
                if current_count == last_count:
                    consecutive_no_change += 1
                    if consecutive_no_change >= 3:
                        logger.info(f"No new results after {consecutive_no_change} scrolls. Stopping.")
                        break
                else:
                    consecutive_no_change = 0
                    
                last_count = current_count
                scroll_count += 1
                
                # Check for CAPTCHA after scrolling
                if self._check_for_captcha():
                    break
                    
            logger.info(f"Loaded {last_count - initial_count} additional results")
            return last_count - initial_count
            
        except Exception as e:
            logger.error(f"Error scrolling for more results: {str(e)}")
            return 0
    
    @retry_on_failure(max_retries=3, delay=2.0, backoff_factor=2.0, 
                      exceptions=(TimeoutException, WebDriverException))
    def scrape(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Scrape business data from Google Maps based on query and location.
        
        Args:
            query: Search term to scrape (e.g., "restaurants", "hotels")
            location: Location to search within (e.g., "Mexico City", "Buenos Aires")
            
        Returns:
            List of dictionaries containing scraped business data
        """
        self.results = []
        self.processed_items = set()
        
        try:
            # Initialize driver if needed
            if not self._ensure_driver():
                logger.error("Failed to initialize driver")
                return []
            
            # Navigate to Maps and perform search
            if not self._navigate_to_maps() or not self._search(query, location):
                logger.warning(f"Failed to search for '{query}' in '{location}'")
                return []
            
            # Wait for a moment to ensure results are loaded
            time.sleep(random.uniform(2.0, 4.0))
            
            # Scroll to load more results
            self._scroll_for_more_results(max_scrolls=5)
            
            # Now extract data from visible business listings
            business_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                'div[role="feed"] > div'
            )
            
            logger.info(f"Found {len(business_elements)} business listings to process")
            
            # Process each business listing
            for i, element in enumerate(business_elements):
                if i >= self.max_results:
                    logger.info(f"Reached maximum of {self.max_results} results")
                    break
                    
                # Check for CAPTCHA regularly
                if i > 0 and i % 5 == 0 and self._check_for_captcha():
                    break
                
                # Extract business data
                business_data = self._extract_business_data(element)
                if business_data:
                    self.results.append(business_data)
                    logger.info(f"Extracted data for: {business_data.get('name', 'Unknown Business')}")
                
                # Add delay between processing businesses
                rate_limit(min_delay=self.request_delay, 
                          max_delay=self.request_delay + (self.random_delay_range[1] if self.random_delay_range else 0))
                
                # Scroll more if we've processed most visible results
                if i > 0 and i % 10 == 0:
                    new_results = self._scroll_for_more_results(max_scrolls=2)
                    if new_results == 0:
                        logger.info("No more results available")
                        break
                    
                    # Re-fetch elements as the DOM might have changed
                    business_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, 
                        'div[role="feed"] > div'
                    )
            
            # Clean results
            self.clean_results()
            logger.info(f"Successfully scraped {len(self.results)} businesses")
            
            return self.results
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return []
            
        finally:
            # Don't automatically close the driver here to allow multiple searches
            pass
    
    def close(self) -> None:
        """Close the WebDriver and free resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
            finally:
                self.driver = None
                self.is_initialized = False
    
    def __del__(self) -> None:
        """Ensure resources are freed when the object is destroyed."""
        self.close()
    
    def _simulate_realistic_scrolling(self, scroll_element=None, min_scrolls=3, max_scrolls=7):
        """Simulate realistic human scrolling behavior in the page or element."""
        try:
            if not self.driver:
                return
                
            scroll_element = scroll_element or self.driver
            
            # Determine if we're scrolling the whole page or an element
            if scroll_element == self.driver:
                # Whole page scrolling
                scroll_script = "window.scrollBy(0, {});"
            else:
                # Element scrolling
                scroll_script = "arguments[0].scrollTop += {};"
                
            # Random number of scroll actions
            num_scrolls = random.randint(min_scrolls, max_scrolls)
            
            for _ in range(num_scrolls):
                # Determine scroll direction (mostly down but sometimes up)
                direction = 1 if random.random() < 0.85 else -1
                
                # Random scroll amount with human-like patterns
                if direction > 0:
                    # Scrolling down - larger distances
                    scroll_amount = random.randint(100, 400)
                else:
                    # Scrolling up - smaller distances
                    scroll_amount = random.randint(50, 200)
                    
                scroll_amount *= direction
                
                # Execute the scroll
                if scroll_element == self.driver:
                    self.driver.execute_script(scroll_script.format(scroll_amount))
                else:
                    self.driver.execute_script(scroll_script.format(scroll_amount), scroll_element)
                
                # Random pause between scrolls with a realistic rhythm
                # People slow down when reading interesting content
                scroll_pause = random.uniform(0.3, 1.5)
                time.sleep(scroll_pause)
                
            logger.debug(f"Completed {num_scrolls} realistic scroll actions")
            
        except Exception as e:
            logger.error(f"Error during realistic scrolling: {str(e)}")
    
    def _simulate_mouse_movement(self, element=None):
        """Simulate realistic mouse movement patterns using JavaScript."""
        try:
            if not self.driver:
                return
            
            # Define a mouse movement path with random control points
            # This creates a more natural, curved movement path
            move_script = """
                // Function to simulate realistic mouse movement
                function simulateRealisticMouseMovement(element) {
                    // Get current viewport dimensions
                    const viewportWidth = window.innerWidth;
                    const viewportHeight = window.innerHeight;
                    
                    // Generate random start position (usually from the center or edges)
                    const startX = Math.random() < 0.5 ? 
                        Math.random() * viewportWidth * 0.2 : 
                        viewportWidth * 0.8 + Math.random() * viewportWidth * 0.2;
                    const startY = Math.random() < 0.5 ? 
                        Math.random() * viewportHeight * 0.2 : 
                        viewportHeight * 0.8 + Math.random() * viewportHeight * 0.2;
                    
                    // Get target element position if provided
                    let targetX, targetY;
                    if (element) {
                        const rect = element.getBoundingClientRect();
                        // Target a random point within the element
                        targetX = rect.left + rect.width * (0.2 + Math.random() * 0.6);
                        targetY = rect.top + rect.height * (0.2 + Math.random() * 0.6);
                    } else {
                        // Random target position if no element
                        targetX = Math.random() * viewportWidth;
                        targetY = Math.random() * viewportHeight;
                    }
                    
                    // Generate random control points for Bezier curve (natural mouse movement)
                    const cp1x = startX + (targetX - startX) * (0.2 + Math.random() * 0.2);
                    const cp1y = startY + (targetY - startY) * (0.2 + Math.random() * 0.4) - 100 + Math.random() * 200;
                    const cp2x = startX + (targetX - startX) * (0.6 + Math.random() * 0.2);
                    const cp2y = startY + (targetY - startY) * (0.6 + Math.random() * 0.2) - 100 + Math.random() * 200;
                    
                    // Calculate total distance for timing
                    const distance = Math.sqrt(Math.pow(targetX - startX, 2) + Math.pow(targetY - startY, 2));
                    
                    // Number of steps (more steps = smoother movement)
                    const steps = Math.max(10, Math.min(30, Math.floor(distance / 10)));
                    
                    // Simulate the mouse movement along the path
                    for (let i = 0; i <= steps; i++) {
                        const t = i / steps;
                        
                        // Cubic Bezier curve formula
                        const x = Math.pow(1-t, 3) * startX + 
                                 3 * Math.pow(1-t, 2) * t * cp1x +
                                 3 * (1-t) * Math.pow(t, 2) * cp2x +
                                 Math.pow(t, 3) * targetX;
                                 
                        const y = Math.pow(1-t, 3) * startY + 
                                 3 * Math.pow(1-t, 2) * t * cp1y +
                                 3 * (1-t) * Math.pow(t, 2) * cp2y +
                                 Math.pow(t, 3) * targetY;
                        
                        // Add small random jitter (hand tremor simulation)
                        const jitterX = (Math.random() - 0.5) * 3;
                        const jitterY = (Math.random() - 0.5) * 3;
                        
                        const event = new MouseEvent('mousemove', {
                            bubbles: true,
                            cancelable: true,
                            view: window,
                            clientX: x + jitterX,
                            clientY: y + jitterY
                        });
                        
                        document.elementFromPoint(x + jitterX, y + jitterY)?.dispatchEvent(event);
                    }
                    
                    // Return whether we moved to an element or not
                    return !!element;
                }
                
                // Execute the function with the provided element
                return simulateRealisticMouseMovement(arguments[0]);
            """
            
            result = self.driver.execute_script(move_script, element)
            
            # Add a realistic pause after movement
            time.sleep(random.uniform(0.3, 1.0))
            
            logger.debug(f"Simulated realistic mouse movement {'to element' if result else 'in page'}")
            
        except Exception as e:
            logger.error(f"Error during mouse movement simulation: {str(e)}")
            
    def _simulate_human_typing(self, element, text, min_delay=0.05, max_delay=0.25):
        """Simulate human-like typing with variable delays between keystrokes."""
        try:
            if not element or not text:
                return
                
            # Click the element first
            element.click()
            time.sleep(random.uniform(0.3, 0.7))
            
            # Clear existing text with different methods
            if random.random() < 0.7:
                element.clear()
            else:
                # Use keyboard shortcuts
                if random.random() < 0.5:
                    element.send_keys(Keys.CONTROL + "a")
                else:
                    for _ in range(10):  # Arbitrary number of backspaces
                        element.send_keys(Keys.BACKSPACE)
                        
            time.sleep(random.uniform(0.2, 0.5))
            
            # Type with human-like rhythm
            for char in text:
                # Determine delay for this character
                # Common letters get typed faster than rare ones
                common_chars = "etaoinsrhldcumfpgwybvkxjqz"
                if char.lower() in common_chars:
                    # More common characters are typed faster
                    char_position = common_chars.find(char.lower())
                    char_delay = min_delay + (max_delay - min_delay) * (char_position / len(common_chars))
                else:
                    # Non-letter characters get slightly longer delays
                    char_delay = random.uniform(max_delay * 0.7, max_delay)
                
                # Occasionally add a longer pause (like thinking)
                if random.random() < 0.03:  # 3% chance
                    time.sleep(random.uniform(0.5, 1.2))
                
                # Type the character
                element.send_keys(char)
                time.sleep(char_delay)
            
            # Sometimes add a pause after typing (before submitting)
            if random.random() < 0.7:
                time.sleep(random.uniform(0.3, 0.8))
                
            logger.debug(f"Simulated human typing for text of length {len(text)}")
            
        except Exception as e:
            logger.error(f"Error during human typing simulation: {str(e)}")
