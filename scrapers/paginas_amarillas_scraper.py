#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PaginasAmarillasScraper - Scraper para sitios de Páginas Amarillas.

Este módulo implementa un scraper para los sitios de Páginas Amarillas de Argentina y Chile.
Debido a la fuerte protección CAPTCHA en estos sitios, el scraper incluye un modo de
datos simulados que se activa automáticamente cuando:

1. Se detecta un CAPTCHA en la respuesta
2. No se puede obtener respuesta del servidor
3. No se encuentran resultados en la página
4. Ocurre cualquier error durante el scraping

Los datos simulados son generados para mantener la consistencia con el formato esperado
y permitir el desarrollo y pruebas del sistema incluso cuando el scraping real no es posible.

Características:
- Soporte para Argentina (ar) y Chile (cl)
- Detección automática de CAPTCHA
- Generación de datos simulados realistas
- Marcador 'is_simulated' en los resultados simulados
- Opción para forzar el uso de datos simulados

Ejemplo de uso:
    scraper = PaginasAmarillasScraper()
    # Búsqueda normal (usará datos simulados si encuentra CAPTCHA)
    results = scraper.scrape("restaurantes", "Buenos Aires")
    
    # Forzar uso de datos simulados
    results = scraper.scrape("hoteles", "Santiago", use_simulated=True)
"""

import time
import random
import logging
import re
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import quote_plus
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
from collections import Counter

# Local imports
from scrapers.directory_scraper import DirectoryScraper
from utils.helpers import (
    get_random_user_agent,
    detect_captcha,
    simulate_human_behavior,
    clean_text,
    extract_phone_numbers,
    extract_emails,
    extract_urls,
    wait_for_element, # Added for get_listings
    wait_for_elements # Added for get_listings
)
import logging # Assuming logging is configured elsewhere, ensure it's imported

logger = logging.getLogger(__name__)

# Helper functions for dynamic block finding (module-level)
def _get_element_signature(element: Any) -> Optional[Tuple[str, Tuple[str, ...], int]]:
    """Generates a basic structural signature for a WebElement."""
    try:
        tag = element.tag_name
        classes_attr = element.get_attribute("class")
        classes = tuple(sorted(classes_attr.split())) if classes_attr else tuple()
        num_children = len(element.find_elements(By.XPATH, "./*"))
        return (tag, classes, num_children)
    except (StaleElementReferenceException, NoSuchElementException, WebDriverException) as e_sig_known:
        logger.debug(f"Known Selenium error in _get_element_signature for element {element.tag_name if hasattr(element, 'tag_name') else 'N/A'}: {e_sig_known}", exc_info=False)
        return None
    except Exception as e_sig_unknown: # Catch any other unexpected error
        logger.debug(f"Unexpected error in _get_element_signature: {e_sig_unknown}", exc_info=True) # Log with traceback
        return None

def _find_repeated_blocks(driver: Any, min_repeats: int = 2,
                         target_container_tags: Optional[List[str]] = None,
                         min_children_for_container: int = 3,
                         check_visibility_for_listing: bool = True) -> List[Any]:
    """
    Tries to find blocks of repeated structures in the DOM.
    Focuses on children of specified container tags.
    """
    if target_container_tags is None:
        target_container_tags = ['div', 'ul', 'ol', 'section', 'article', 'tbody', 'li']

    logger.debug(f"Starting dynamic block search. Min repeats: {min_repeats}")
    best_candidate_list: List[Any] = []
    
    potential_containers = []
    for tag_name in target_container_tags:
        try:
            logger.debug(f"Searching for container elements with tag: {tag_name}")
            # Limit the number of containers to check for performance
            elements_of_tag = driver.find_elements(By.TAG_NAME, tag_name)[:30] # Reduced from [:50]
            potential_containers.extend(elements_of_tag)
            logger.debug(f"Found {len(elements_of_tag)} elements for tag '{tag_name}'. Total potential containers: {len(potential_containers)}")
        except (WebDriverException, NoSuchElementException) as e_find_tags:
            logger.debug(f"Could not find or access elements with tag: {tag_name}. Error: {e_find_tags}")
            continue
        except Exception as e_generic_find_tags:
            logger.error(f"Generic error finding elements for tag {tag_name}: {e_generic_find_tags}", exc_info=True)
            continue


    logger.debug(f"Found {len(potential_containers)} potential containers for analysis.")
    # Limit total analysis time to avoid long delays
    import time as _time
    _start_time = _time.time()
    _max_duration = 10  # seconds
    highest_score = 0

    for i, container in enumerate(potential_containers):
        # abort if exceeding allowed dynamic analysis time
        if _time.time() - _start_time > _max_duration:
            logger.warning(f"Dynamic block search exceeded {_max_duration}s, aborting early.")
            break
        try:
            container_tag_name = container.tag_name
            container_id = container.get_attribute('id') or 'N/A'
            container_class = container.get_attribute('class') or 'N/A'
            logger.debug(f"Processing container {i+1}/{len(potential_containers)}: <{container_tag_name} id='{container_id}' class='{container_class}'>")

            if not container.is_displayed():
                logger.debug(f"Container <{container_tag_name} id='{container_id}'> is not displayed, skipping.")
                continue
            
            children = container.find_elements(By.XPATH, "./*")
            logger.debug(f"Container <{container_tag_name} id='{container_id}'> has {len(children)} children.")
            if len(children) < min_children_for_container or len(children) < min_repeats:
                logger.debug(f"Skipping container <{container_tag_name} id='{container_id}'> due to insufficient children ({len(children)}).")
                continue

            signatures = Counter()
            children_by_signature: Dict[tuple, List[Any]] = {}

            for child_idx, child in enumerate(children):
                logger.debug(f"Processing child {child_idx+1}/{len(children)} of container <{container_tag_name} id='{container_id}' class='{container_class}'>")
                if check_visibility_for_listing and not child.is_displayed():
                    logger.debug(f"Child {child_idx+1} is not visible, skipping.")
                    continue
                sig = _get_element_signature(child)
                if sig:
                    logger.debug(f"Child {child_idx+1} signature: {sig}")
                    signatures[sig] += 1
                    if sig not in children_by_signature:
                        children_by_signature[sig] = []
                    children_by_signature[sig].append(child)
                else:
                    logger.debug(f"Child {child_idx+1} could not get signature.")
            
            if not signatures:
                logger.debug(f"No valid signatures found for children of container <{container_tag_name} id='{container_id}' class='{container_class}'>.")
                continue

            logger.debug(f"Signatures for container <{container_tag_name} id='{container_id}' class='{container_class}'>: {signatures}")

            for sig, count in signatures.items():
                if count >= min_repeats:
                    current_elements = children_by_signature[sig]
                    # Filter for substantial, visible elements
                    substantial_elements = []
                    for el_check in current_elements:
                        try:
                            if el_check.is_displayed() and (el_check.text.strip() or el_check.get_attribute('innerHTML').strip()):
                                substantial_elements.append(el_check)
                        except StaleElementReferenceException:
                            logger.debug("Stale element encountered while checking substantiality, skipping.")
                            continue
                    
                    if substantial_elements and len(substantial_elements) < min_repeats:
                        logger.debug(f"Found {len(substantial_elements)} substantial elements for sig {sig} in <{container_tag_name} id='{container_id}' class='{container_class}'>, but this is less than min_repeats ({min_repeats}).")

                    if len(substantial_elements) >= min_repeats:
                        # Score: prioritize more items, and more complex items (more children in signature)
                        current_score = len(substantial_elements) + sig[2] # sig[2] is num_children
                        logger.debug(f"Found {len(substantial_elements)} substantial elements with signature {sig} (count: {count}), score: {current_score}")
                        if current_score > highest_score:
                            logger.info(f"New best candidate list: {len(substantial_elements)} items, score {current_score}, signature {sig} in <{container_tag_name} id='{container_id}'>")
                            best_candidate_list = substantial_elements
                            highest_score = current_score
                        elif current_score == highest_score and len(substantial_elements) > len(best_candidate_list):
                            logger.info(f"Updating (same score, more items): {len(substantial_elements)} items, sig {sig} in <{container_tag_name} id='{container_id}' class='{container_class}'>")
                            best_candidate_list = substantial_elements
                else: # count < min_repeats
                    logger.debug(f"Signature {sig} in <{container_tag_name} id='{container_id}' class='{container_class}'> repeated {count} times (less than min_repeats {min_repeats}).")
        
        except (StaleElementReferenceException, NoSuchElementException, WebDriverException) as e_container_proc:
            logger.warning(f"Selenium error processing container <{container.tag_name if hasattr(container, 'tag_name') else 'N/A'} id='{container.get_attribute('id') if hasattr(container, 'get_attribute') else 'N/A'}'>, skipping. Error: {e_container_proc}", exc_info=False)
            continue
        except Exception as e_generic_container_proc:
            logger.error(f"Generic error processing container, skipping. Error: {e_generic_container_proc}", exc_info=True) # Log with traceback
            continue

    if best_candidate_list:
        logger.info(f"Dynamic analysis selected best list with {len(best_candidate_list)} blocks (score: {highest_score}).")
    else:
        logger.warning(f"Dynamic analysis could not find strongly repeated blocks (min_repeats={min_repeats}).")
            
    return best_candidate_list

class PaginasAmarillasScraper(DirectoryScraper):
    """
    Scraper class for extracting business data from Páginas Amarillas (Yellow Pages)
    across Latin America.
    """
    
    def __init__(self, 
                 request_delay: float = 2.0,
                 random_delay_range: Optional[Tuple[float, float]] = (1.0, 3.0),
                 max_results: int = 100,
                 headless: bool = True,
                 use_browser_pool: bool = True,
                 use_cache: bool = True,
                 country: str = "ar",  # Default to Argentina as it's one of the most established sites
                 skip_dynamic: bool = False,
                 **kwargs):
        """
        Initialize the Páginas Amarillas scraper.
        
        Args:
            request_delay: Base delay between requests in seconds
            random_delay_range: Tuple of (min, max) additional random delay
            max_results: Maximum number of results to scrape
            headless: Whether to run the browser in headless mode
            use_browser_pool: Whether to use the browser pool for better resource management
            country: Country code for the specific Páginas Amarillas website (ar, cl, co, pe)
            skip_dynamic: If True, skips the dynamic block analysis.
        """
        super().__init__(
            request_delay=request_delay,
            random_delay_range=random_delay_range,
            max_results=max_results,
            headless=headless,
            use_browser_pool=use_browser_pool,
            use_cache=use_cache,
            **kwargs
        )
        # Fast mode: skip dynamic block analysis
        self.skip_dynamic = skip_dynamic
        self.current_query_for_debug: Optional[str] = None
        self.current_location_for_debug: Optional[str] = None
        
        self.country = country.lower()
        self._set_base_url()
        
    def _set_base_url(self) -> None:
        """Set the base URL based on the selected country."""
        country_urls = {
            "cl": "https://www.amarillas.cl",
            "ar": "https://www.paginasamarillas.com.ar",
            "co": "https://www.paginasamarillas.com.co",
            "pe": "https://www.paginasamarillas.com.pe",
            # México ya no tiene servicio de Páginas Amarillas
        }
        
        self.base_url = country_urls.get(self.country, country_urls["cl"])  # Default a Chile si el país no existe
        logger.info(f"Using Páginas Amarillas URL for {self.country.upper()}: {self.base_url}")
    
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
        encoded_location = quote_plus(location) if location else ""
        
        # Different countries might have slightly different URL structures
        if self.country == "mx":
            if location:
                search_url = f"{self.base_url}/buscar/{encoded_query}/{encoded_location}"
            else:
                search_url = f"{self.base_url}/buscar/{encoded_query}"
        elif self.country == "ar":
            if location:
                search_url = f"{self.base_url}/buscar/{encoded_query}/{encoded_location}"
            else:
                search_url = f"{self.base_url}/buscar/{encoded_query}"
        # Add more country-specific URL formats as needed
        else:
            # Default format
            if location:
                search_url = f"{self.base_url}/buscar/{encoded_query}/{encoded_location}"
            else:
                search_url = f"{self.base_url}/buscar/{encoded_query}"
        
        return search_url
    
    def get_listings(self) -> List[Any]:
        """
        Retrieve the current page's listing elements using a new strategy with fallbacks.
        1. New Strategy: Detect main container, then items within it.
        2. Fallback: Dynamic block finding.
        3. Fallback: Original CSS selectors.
        Includes saving HTML/screenshot for debugging if issues occur.
        Attempts to switch to an iframe if present.
        """
        logger.info("Attempting to find listings with new multi-stage strategy...")

        if not self.driver:
            logger.error("Browser driver is not initialized. Cannot get listings.")
            return []

        try:
            WebDriverWait(self.driver, 10).until(
                lambda drv: drv.execute_script("return document.readyState") == 'complete'
            )
            logger.debug("Main document reported 'document.readyState' as 'complete'.")
            time.sleep(0.5) # Short pause for main doc JS
        except TimeoutException:
            logger.warning("Timeout waiting for main document.readyState to be 'complete'.")
        except Exception as e_rs:
            logger.error(f"Error during main document.readyState check: {e_rs}", exc_info=True)

        switched_to_iframe = False
        original_html_for_debug = ""
        try:
            logger.info("Attempting to switch to iframe with id='iframe'")
            iframe_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "iframe"))
            )
            self.driver.switch_to.frame(iframe_element)
            switched_to_iframe = True
            logger.info("Successfully switched to iframe.")
            
            WebDriverWait(self.driver, 10).until(
                lambda drv: drv.execute_script("return document.readyState") == 'complete'
            )
            logger.debug("Iframe content reported 'document.readyState' as 'complete'.")
            time.sleep(1) # Pausa adicional para JavaScript asíncrono en iframe
        except TimeoutException:
            logger.warning("Timeout waiting for iframe with id='iframe'. Proceeding with main document context.")
            original_html_for_debug = self.driver.page_source # Save main page if iframe not found
        except Exception as e_iframe:
            logger.error(f"Error switching to iframe: {e_iframe}", exc_info=True)
            original_html_for_debug = self.driver.page_source # Save main page on error

        # Guardar página para análisis (contenido del iframe si se cambió, o principal si no)
        debug_dir = "debug_html"
        html_filename = ""
        try:
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            safe_query = "".join(c if c.isalnum() else "_" for c in (self.current_query_for_debug or "unknown_query"))
            safe_location = "".join(c if c.isalnum() else "_" for c in (self.current_location_for_debug or "unknown_location"))
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            context_marker = "iframe" if switched_to_iframe else "main";
            
            base_filename = f"pa_{self.country}_{safe_query}_{safe_location}_{timestamp}_{context_marker}"
            html_filename = os.path.join(debug_dir, f"{base_filename}.html")
            screenshot_filename = os.path.join(debug_dir, f"{base_filename}.png")

            current_page_source = self.driver.page_source
            # If we failed to switch to iframe and saved main page source earlier, use that
            # This is to ensure we save the correct context if iframe switch fails early
            if not switched_to_iframe and original_html_for_debug:
                 current_page_source = original_html_for_debug

            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(current_page_source)
            logger.info(f"Saved HTML source ({context_marker}) for debugging to {html_filename}")
            
            # Screenshot is always of the current view
            self.driver.save_screenshot(screenshot_filename)
            logger.info(f"Saved screenshot ({context_marker}) for debugging to {screenshot_filename}")
            
        except Exception as e_debug_save:
            logger.error(f"Could not save debug HTML/screenshot: {e_debug_save}", exc_info=True)

        # Nueva estrategia: Detectar contenedor principal y luego items (operando en el contexto actual)
        logger.debug("Starting new strategy: container + items.")
        container_selectors = [
            "#resultados", ".listado", ".resultados-lista", ".lista-empresas",
            ".results-list", ".search-results-list", "div[role='main'] ul", "main ul",
            "div[role='main'] section", "main section", ".resultados-container",
            "main .results", "#search-results", ".search-results-container",
            # Selectors observed in parked pages (less likely to contain listings but for completeness)
            "body", "#content", 
        ]
        item_selectors_within_container = [
            "li[data-listing-id]", "article.listing", "div.listing",
            "li.result-item", "div.result-item", ".business-card", ".search-card",
            "li", "article", ".item", "div[class*='item']", "div[class*='listing']",
             "div" # Very generic, last resort
        ]
        
        found_listings: List[Any] = []

        for container_selector in container_selectors:
            try:
                logger.debug(f"Attempting to find container with selector: {container_selector}")
                container = wait_for_element(self.driver, container_selector, timeout=2, condition='presence') # Reduced timeout
                if container:
                    logger.info(f"Found potential container with selector: {container_selector}")
                    for item_selector in item_selectors_within_container:
                        try:
                            logger.debug(f"Looking for items with selector '{item_selector}' within '{container_selector}'")
                            items = container.find_elements(By.CSS_SELECTOR, item_selector)
                            if items:
                                valid_items = [
                                    item for item in items if item.is_displayed() and (item.text.strip() or 
                                    item.get_attribute('data-listing-id') or 
                                    len(item.find_elements(By.CSS_SELECTOR, '*')) > 1) # Ensure item has some children or text
                                ]
                                if valid_items:
                                    logger.info(f"Found {len(valid_items)} valid listing items using container '{container_selector}' and item selector '{item_selector}'.")
                                    found_listings = valid_items
                                    break # Found items with this item_selector
                                else:
                                    logger.debug(f"Item selector '{item_selector}' found {len(items)} items, but none deemed valid within '{container_selector}'.")
                        except Exception as e_item:
                            logger.debug(f"Error finding items with selector '{item_selector}' in container '{container_selector}': {e_item}", exc_info=False)
                    if found_listings:
                        break # Found items with this container_selector
                    logger.debug(f"No suitable items found within container '{container_selector}' using any item selectors.")
            except TimeoutException:
                logger.debug(f"Timeout waiting for container with selector: {container_selector}")
            except Exception as e_container:
                logger.error(f"Error processing container selector '{container_selector}': {e_container}", exc_info=False)
        
        if found_listings:
            if switched_to_iframe:
                logger.debug("Switching back to default content from iframe before returning listings.")
                self.driver.switch_to.default_content()
            return found_listings

        logger.warning("New container-item strategy failed to find listings. Falling back to dynamic analysis.")

        # Fallback 1: Dynamic analysis
        if not self.skip_dynamic:
            try:
                logger.debug("Attempting dynamic block analysis as fallback...")
                dynamic_listings = _find_repeated_blocks(
                    self.driver, # Operates on current context (iframe or main)
                    min_repeats=2,
                    target_container_tags=['div', 'ul', 'ol', 'section', 'main', 'article', 'table'],
                    min_children_for_container=3
                )
                if dynamic_listings:
                    logger.info(f"Dynamically found {len(dynamic_listings)} potential listing elements (fallback).")
                    if switched_to_iframe:
                        logger.debug("Switching back to default content from iframe before returning dynamic listings.")
                        self.driver.switch_to.default_content()
                    return dynamic_listings
            except Exception as e_dynamic:
                logger.error(f"Error during dynamic block analysis (fallback): {e_dynamic}", exc_info=True)
        else:
            logger.info("Dynamic analysis skipped as per configuration.")

        # Fallback 2: Original CSS selector lookup
        logger.warning("Dynamic analysis failed or skipped. Falling back to original CSS selector lookup (final fallback).")
        try:
            fallback_selectors = [
                ".listing", ".search-results__item", "article", ".business-card",
                ".search-card", "li[data-listing-id]", ".item",
                "div[class*='result']", "div[class*='card']", "div[class*='entry']"
            ]
            for selector in fallback_selectors:
                try:
                    listings = wait_for_elements(
                        self.driver, # Operates on current context
                        selector,
                        timeout=1, # Reduced timeout
                        condition='presence'
                    )
                    if listings:
                        valid_listings = [l for l in listings if l.is_displayed() and (l.text.strip() or l.get_attribute('innerHTML').strip())]
                        if valid_listings:
                            logger.info(f"Found {len(valid_listings)} listings using final fallback selector: {selector}")
                            if switched_to_iframe:
                                logger.debug("Switching back to default content from iframe before returning final fallback listings.")
                                self.driver.switch_to.default_content()
                            return valid_listings
                        else:
                            logger.debug(f"Final fallback selector {selector} found {len(listings)} items, but all were empty or not displayed.")
                except Exception as e_sel:
                    logger.debug(f"Final fallback selector {selector} failed: {e_sel}", exc_info=False)
            
            logger.error("All attempts to find listings failed, including all fallbacks.")
        except Exception as e_final_fallback:
            logger.error(f"Critical error in final CSS fallback listing search: {e_final_fallback}", exc_info=True)
        
        if switched_to_iframe:
            logger.debug("Switching back to default content from iframe as no listings were found.")
            self.driver.switch_to.default_content()
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
                "source": f"paginas_amarillas_{self.country}",
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
            # Try different possible selectors
            name_selectors = [
                ".business-name", ".listing-title", ".title", "h2", 
                "[data-testid='listing-name']", ".empresa-nombre"
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
                ".address", ".location", ".direccion",
                "[data-testid='listing-address']", ".empresa-direccion"
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
                ".phone", ".telefono", "[data-testid='listing-phone']",
                ".empresa-telefono"
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
                ".website", ".web", "a.web-link", "[data-testid='listing-website']",
                ".empresa-web", "a[href^='http']"
            ]
            
            for selector in website_selectors:
                try:
                    website_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["website"] = website_elem.get_attribute("href")
                    break
                except NoSuchElementException:
                    continue
            
            # Extract email from text or elements
            email_selectors = [
                ".email", "[data-testid='listing-email']", ".empresa-email"
            ]
            
            for selector in email_selectors:
                try:
                    email_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    email_text = email_elem.text
                    emails = extract_emails(email_text)
                    if emails:
                        business_data["email"] = emails[0]
                    break
                except Exception:
                    # Treat any exception as missing element
                    continue
            
            # If no explicit email element, try to extract from all text
            if not business_data["email"]:
                all_text = html_element.text
                emails = extract_emails(all_text)
                if emails:
                    business_data["email"] = emails[0]
            
            # Extract category
            category_selectors = [
                ".category", ".categoria", "[data-testid='listing-category']",
                ".empresa-categoria"
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
                ".description", ".descripcion", "[data-testid='listing-description']",
                ".empresa-descripcion"
            ]
            
            for selector in description_selectors:
                try:
                    desc_elem = html_element.find_element(By.CSS_SELECTOR, selector)
                    business_data["description"] = clean_text(desc_elem.text)
                    break
                except Exception:
                    # Treat any exception as missing element
                    continue
            
            # Return only if we have at least a name or a phone
            if business_data["name"] or business_data["phone"]:
                return business_data
            else:
                logger.warning("Skipping listing - could not extract name or phone")
                return None
            
        except Exception as e:
            logger.error(f"Error parsing listing: {e}")
            return None
            
    def handle_pagination(self) -> bool:
        """
        Go to the next page of results if available.
        Uses intelligent waiting to detect page changes.
        
        Returns:
            True if successfully navigated to next page, False otherwise
        """
        from utils.helpers import wait_for_element, wait_for_page_change
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException
        
        try:
            # Store a reference element for stale checking
            reference_elements = self.driver.find_elements(By.CSS_SELECTOR, 'body')
            reference_element = reference_elements[0] if reference_elements else None
            
            # Store current URL for change detection
            initial_url = self.driver.current_url
            
            # Look for pagination controls with intelligent waiting
            pagination_selectors = [
                "a.next", ".pagination a[rel='next']", 
                ".pagination-next", "[data-testid='pagination-next']",
                "a[aria-label='Next page']", ".siguiente",
                "a[aria-label='Siguiente']", 
                ".pagination-container .next",
                ".paginator .next"
            ]
            
            for selector in pagination_selectors:
                try:
                    # Use intelligent waiting to find the element
                    next_page = wait_for_element(
                        self.driver,
                        selector,
                        timeout=5,
                        condition='clickable'
                    )
                    
                    if next_page and next_page.is_displayed() and next_page.is_enabled():
                        logger.info(f"Found next page button with selector: {selector}")
                        
                        # Scroll into view for better click reliability
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", 
                            next_page
                        )
                        
                        # Small wait after scrolling
                        time.sleep(0.5)
                        
                        # Click the button
                        next_page.click()
                        
                        # Use intelligent waiting to detect page change
                        if wait_for_page_change(
                            self.driver, 
                            timeout=10, 
                            reference_element=reference_element,
                            url_change=(initial_url != self.driver.current_url)
                        ):
                            logger.info("Successfully navigated to next page")
                            
                            # Apply rate limiting to be polite to the server
                            self.rate_limit()
                            
                            return True
                except NoSuchElementException:
                    continue
                except ElementNotInteractableException:
                    logger.warning(f"Next page button with selector '{selector}' is not interactive")
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.info("No more pages available or next button not found")
            return False
            
        except Exception as e:
            logger.error(f"Error handling pagination: {e}")
            return False
    
    def scrape(self, query: str, location: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape business listings from Páginas Amarillas.
        
        Args:
            query: Search term (e.g., "restaurantes")
            location: City or area to search in
            **kwargs: Additional arguments:
                - max_results: Maximum number of results to return
                - use_simulated: Force using simulated data instead of scraping
                
        Returns:
            List of dictionaries containing business information
        """
        logger.info(f"Iniciando búsqueda en Páginas Amarillas {self.country.upper()}")
        logger.info(f"Query: {query}, Location: {location}")
        
        # Si se solicita específicamente usar datos simulados
        if kwargs.get('use_simulated', False):
            return self._generate_simulated_results(query, location, kwargs.get('max_results', 10))
        
        try:
            url = self.build_search_url(query, location)
            response = self._make_request(url)
            
            if not response:
                logger.error("No se pudo obtener respuesta del servidor")
                return self._generate_simulated_results(query, location, kwargs.get('max_results', 10))
            
            # Verificar si hay CAPTCHA en la respuesta
            if "captcha" in response.lower() or "robot" in response.lower():
                logger.warning("CAPTCHA detectado, usando datos simulados")
                return self._generate_simulated_results(query, location, kwargs.get('max_results', 10))
                
            # Parsear resultados si no hay CAPTCHA
            listings = self._parse_listings(response)
            
            if not listings:
                logger.warning("No se encontraron resultados, usando datos simulados")
                return self._generate_simulated_results(query, location, kwargs.get('max_results', 10))
                
            return listings[:kwargs.get('max_results', None)]
            
        except Exception as e:
            logger.error(f"Error durante el scraping: {str(e)}")
            return self._generate_simulated_results(query, location, kwargs.get('max_results', 10))
    
    def _generate_simulated_results(self, query: str, location: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Generate simulated business results when CAPTCHA is detected.
        
        Args:
            query: Search term used (e.g., "restaurantes")
            location: Location filter (e.g., "Buenos Aires")
            num_results: Number of simulated results to generate
            
        Returns:
            List of dictionaries with simulated business data
        """
        import random
        
        logger.warning("Generating simulated results due to CAPTCHA detection")
        
        # Common business types and their associated words for name generation
        business_types = {
            "restaurantes": ["Restaurante", "Comedor", "Parrilla", "Bar", "Cafetería"],
            "hoteles": ["Hotel", "Posada", "Hospedaje", "Hostería"],
            "abogados": ["Abogados", "Estudio Jurídico", "Asesoría Legal", "Bufete"],
            "medicos": ["Consultorio", "Centro Médico", "Clínica", "Sanatorio"],
            "gimnasios": ["Gimnasio", "Centro Fitness", "Club Deportivo", "Sport Center"],
        }
        
        # Default to generic business if query doesn't match known types
        business_prefixes = business_types.get(query.lower(), ["Negocio", "Empresa", "Comercio"])
        
        results = []
        for i in range(num_results):
            # Generate a realistic looking business name
            name = f"{random.choice(business_prefixes)} {chr(65 + i)}"
            
            # Generate a plausible address based on location
            address = f"Calle {random.randint(1, 100)} #{random.randint(100,9999)}, {location}"
            
            # Generate a realistic looking phone number based on country
            if self.country == "ar":
                phone = f"+54 11 {random.randint(4000,6000)}-{random.randint(1000,9999)}"
            elif self.country == "cl":
                phone = f"+56 2 {random.randint(2000,3000)} {random.randint(1000,9999)}"
            else:
                phone = f"+{random.randint(50,60)} {random.randint(100,999)} {random.randint(1000,9999)}"
            
            result = {
                "source": f"paginas_amarillas_{self.country}",
                "scrape_date": time.strftime("%Y-%m-%d"),
                "name": name,
                "address": address,
                "phone": phone,
                "website": None,  # No generamos sitios web simulados
                "email": None,    # No generamos emails simulados
                "category": query,
                "description": None,
                "rating": None,
                "review_count": None,
                "social_media": {},
                "is_simulated": True  # Marcador para identificar datos simulados
            }
            
            results.append(result)
        
        return results
