#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility Functions

This module provides utility functions used throughout the project.
"""

import logging
import os
import json
import random
import time
import re
import requests
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import urlparse
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

logger = logging.getLogger(__name__)

# Common user agents for rotation
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_5_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.62",
    # Mobile User Agents
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36"
]

# Common CAPTCHA detection strings
CAPTCHA_MARKERS = [
    "captcha", "CAPTCHA", 
    "robot", "Robot", "ROBOT",
    "human verification", "Human Verification",
    "security check", "Security Check", 
    "verify you're not a robot",
    "I'm not a robot", "challenge",
    "recaptcha", "reCAPTCHA", "RECAPTCHA"
]

# ANSI color codes for logging
ANSI_COLORS = {
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'white': '\033[97m',
    'reset': '\033[0m'
}

def get_random_user_agent() -> str:
    """
    Get a random user agent from the list.
    
    Returns:
        A random user agent string
    """
    return random.choice(USER_AGENTS)

def setup_selenium_options(user_agent: Optional[str] = None, headless: bool = True) -> Dict[str, Any]:
    """
    Set up Selenium options for browser automation.
    
    Args:
        user_agent: Optional user agent string (random if None)
        headless: Whether to run in headless mode
        
    Returns:
        Dictionary of Selenium options
    """
    if user_agent is None:
        user_agent = get_random_user_agent()
        
    options = {
        'arguments': [
            f'user-agent={user_agent}',
            'disable-blink-features=AutomationControlled',
            'disable-extensions',
            'disable-infobars',
            'disable-notifications',
            'ignore-certificate-errors',
            'no-sandbox',
            'disable-dev-shm-usage',
        ]
    }
    
    if headless:
        options['arguments'].append('headless')
        
    # Include browser preferences
    options['preferences'] = {
        'profile.default_content_setting_values.notifications': 2,
        'profile.managed_default_content_settings.images': 2,
        'disk-cache-size': 4096,
    }
    
    return options

def detect_captcha(html_content: str) -> bool:
    """
    Detect if a CAPTCHA is present in HTML content.
    
    Args:
        html_content: HTML content to check
        
    Returns:
        True if CAPTCHA is detected, False otherwise
    """
    html_lower = html_content.lower()
    
    # Look for known CAPTCHA markers
    for marker in CAPTCHA_MARKERS:
        if marker.lower() in html_lower:
            logger.warning(f"CAPTCHA detected: Found '{marker}' in response")
            return True
            
    # Look for known CAPTCHA image patterns
    captcha_image_patterns = [
        r'captcha\.jpg', r'captcha\.png', r'captcha\.gif',
        r'captcha\?', r'captcha\.php', r'captcha-image'
    ]
    
    for pattern in captcha_image_patterns:
        if re.search(pattern, html_lower):
            logger.warning(f"CAPTCHA detected: Found image pattern '{pattern}' in response")
            return True
            
    # Look for CAPTCHA form elements
    captcha_form_patterns = [
        r'<input[^>]*captcha[^>]*>', r'<div[^>]*captcha[^>]*>',
        r'<iframe[^>]*recaptcha[^>]*>'
    ]
    
    for pattern in captcha_form_patterns:
        if re.search(pattern, html_lower):
            logger.warning(f"CAPTCHA detected: Found form pattern '{pattern}' in response")
            return True
            
    return False

def get_proxy_settings(enabled: bool = False) -> Optional[Dict[str, str]]:
    """
    Get proxy settings from environment variables.
    
    Args:
        enabled: Whether to use proxies
        
    Returns:
        Dictionary of proxy settings or None if disabled
    """
    if not enabled:
        return None
        
    # Load proxy configuration from environment
    proxy_enabled = os.getenv('PROXY_ENABLED', 'False').lower() in ('true', 'yes', '1')
    if not proxy_enabled:
        return None
        
    proxy_list_str = os.getenv('PROXY_LIST', '')
    if not proxy_list_str:
        return None
        
    proxy_list = [p.strip() for p in proxy_list_str.split(',') if p.strip()]
    if not proxy_list:
        return None
        
    # Choose a random proxy from the list
    proxy = random.choice(proxy_list)
    
    # Format: protocol://user:pass@host:port or host:port
    if '://' not in proxy:
        proxy = f'http://{proxy}'
        
    proxy_settings = {
        'http': proxy,
        'https': proxy
    }
    
    logger.info(f"Using proxy: {proxy.split('@')[-1] if '@' in proxy else proxy}")
    return proxy_settings

def rate_limit(min_delay: float = 2.0, max_delay: float = 5.0, jitter: float = 0.5) -> None:
    """
    Sleep for a random time to avoid detection.
    
    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Random jitter factor to add to delay
    """
    delay = random.uniform(min_delay, max_delay)
    jitter_amount = random.uniform(-jitter, jitter)
    final_delay = max(0.1, delay + jitter_amount)
    
    logger.debug(f"Rate limiting: sleeping for {final_delay:.2f} seconds")
    time.sleep(final_delay)

def load_config_from_env(prefix: str = "") -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Args:
        prefix: Prefix for environment variables to filter by
        
    Returns:
        Dictionary of configuration values
    """
    config = {}
    for key, value in os.environ.items():
        if prefix and not key.startswith(prefix):
            continue
            
        # Remove prefix if it exists
        config_key = key[len(prefix):] if prefix and key.startswith(prefix) else key
        
        # Try to parse value as JSON if it looks like a JSON string
        if value.startswith('{') and value.endswith('}'):
            try:
                config[config_key] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
                
        # Try to convert value to appropriate type
        if value.lower() in ('true', 'yes', '1'):
            config[config_key] = True
        elif value.lower() in ('false', 'no', '0'):
            config[config_key] = False
        elif value.isdigit():
            config[config_key] = int(value)
        elif re.match(r'^-?\d+(\.\d+)?$', value):
            config[config_key] = float(value)
        elif ',' in value:
            # Treat as comma-separated list
            config[config_key] = [v.strip() for v in value.split(',')]
        else:
            config[config_key] = value
            
    return config

def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration settings from environment variables.
    
    Returns:
        Dictionary with configuration values
    """
    config = {
        "app_name": os.environ.get("APP_NAME", "LeadScraper LATAM"),
        "app_version": os.environ.get("APP_VERSION", "1.0.0"),
        "app_env": os.environ.get("APP_ENV", "development"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "log_file": os.environ.get("LOG_FILE", ""),
        "timeout": int(os.environ.get("TIMEOUT", "30")),
        "retry_count": int(os.environ.get("RETRY_COUNT", "3")),
        "use_proxy": os.environ.get("USE_PROXY", "False").lower() == "true",
        "proxy_url": os.environ.get("PROXY_URL", ""),
        "headless_browser": os.environ.get("HEADLESS_BROWSER", "True").lower() == "true"
    }
    
    return config

def retry_on_failure(max_retries: int = 3, 
                     delay: float = 1.0,
                     backoff_factor: float = 2.0,
                     exceptions: Tuple = (Exception,)) -> callable:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay for subsequent retries
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                        
                    logger.warning(f"Retry {retries}/{max_retries} for function {func.__name__} after error: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                    
        return wrapper
    return decorator

def clean_text(text: Optional[str]) -> Optional[str]:
    """
    Clean text by removing excess whitespace and normalizing line endings.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return text
        
    # Replace multiple whitespace with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def extract_phone_numbers(text: str, country_code: str = None) -> List[str]:
    """
    Extract phone numbers from text.
    
    Args:
        text: Text to extract phone numbers from
        country_code: Optional country code to prepend to numbers without one
        
    Returns:
        List of phone numbers found
    """
    if not text:
        return []
    
    # Basic phone number pattern
    # This handles various formats like:
    # +1 (123) 456-7890, (123) 456-7890, 123-456-7890, 123.456.7890, 123 456 7890
    phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?(?:\d{1,3})\)?[-.\s]?(?:\d{2,3})[-.\s]?(?:\d{2,5})'
    
    phones = re.findall(phone_pattern, text)
    
    # Clean up the phone numbers
    cleaned_phones = []
    for phone in phones:
        # Remove non-digit characters except for leading +
        cleaned = re.sub(r'(?<!^\+)\D', '', phone)
        
        # Add country code if specified and not already present
        if country_code and not cleaned.startswith('+') and not cleaned.startswith(country_code):
            cleaned = country_code + cleaned
        
        # Add to list if not already present (case-insensitive)
        if cleaned and cleaned not in cleaned_phones:
            cleaned_phones.append(cleaned)
    
    return cleaned_phones

def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Text to extract emails from
        
    Returns:
        List of email addresses found
    """
    if not text:
        return []
    
    # RFC 5322 compliant email regex
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    
    # Remove duplicates while preserving order
    unique_emails = []
    for email in emails:
        if email.lower() not in [e.lower() for e in unique_emails]:
            unique_emails.append(email)
    
    return unique_emails

def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        List of extracted URLs
    """
    if not text:
        return []
        
    pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)'
    
    matches = re.findall(pattern, text)
    return [match for match in matches if match]

def simulate_human_behavior(driver, element=None, scroll_range=None, click=False) -> None:
    """
    Simulate human-like behavior to avoid detection.
    
    Args:
        driver: Selenium WebDriver instance
        element: Optional element to interact with
        scroll_range: Optional tuple of (min_scroll, max_scroll) pixels
        click: Whether to click the element
    """
    # Add random pauses
    time.sleep(random.uniform(0.5, 2.0))
    
    # Random scrolling if requested
    if scroll_range:
        min_scroll, max_scroll = scroll_range
        scroll_amount = random.randint(min_scroll, max_scroll)
        scroll_script = f"window.scrollBy(0, {scroll_amount});"
        driver.execute_script(scroll_script)
        time.sleep(random.uniform(0.3, 1.0))
    
    # If element is provided, maybe move to it
    if element:
        try:
            # Use JavaScript to smoothly scroll element into view with randomness
            driver.execute_script("""
                const element = arguments[0];
                const rect = element.getBoundingClientRect();
                const targetX = rect.left + rect.width * Math.random();
                const targetY = rect.top + rect.height * Math.random();
                
                // Add some randomness to scroll position
                const randomOffset = Math.floor(Math.random() * 50) - 25;
                window.scrollTo({
                    left: window.scrollX + rect.left - window.innerWidth / 2 + randomOffset,
                    top: window.scrollY + rect.top - window.innerHeight / 2 + randomOffset,
                    behavior: 'smooth'
                });
            """, element)
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Click if requested
            if click:
                # Sometimes we do a direct click, sometimes a JavaScript click
                if random.random() < 0.7:
                    element.click()
                else:
                    driver.execute_script("arguments[0].click();", element)
                    
                time.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            logger.warning(f"Error in human behavior simulation: {str(e)}")

def create_logger(name: str, 
                 level: int = logging.INFO,
                 log_file: Optional[str] = None,
                 use_colors: bool = True) -> logging.Logger:
    """
    Create a logger with specific configuration.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional file to log to
        use_colors: Whether to use colors in console output
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Formatter
    if use_colors:
        formatter = logging.Formatter(
            f"{ANSI_COLORS['cyan']}%(asctime)s{ANSI_COLORS['reset']} | "
            f"{ANSI_COLORS['magenta']}%(name)s{ANSI_COLORS['reset']} | "
            f"{ANSI_COLORS['yellow']}%(levelname)s{ANSI_COLORS['reset']} | "
            f"%(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

def setup_logger(name, log_file=None, console=True, log_level="INFO"):
    """
    Set up logger with file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        console: Whether to log to console
        log_level: Logging level
    
    Returns:
        Configured logger
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    logger.handlers = []  # Clear existing handlers
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add console handler if specified
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def validate_email(email: str) -> bool:
    """
    Validate an email address using a more comprehensive regex.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
        
    # More comprehensive email validation pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(pattern, email))

def validate_url(url: str) -> bool:
    """
    Validate a URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
        
    try:
        result = urlparse(url)
        # Check if scheme and netloc are present
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def safe_request(url: str, 
                method: str = 'GET', 
                headers: Optional[Dict[str, str]] = None,
                proxy_enabled: bool = False,
                timeout: int = 30,
                verify_ssl: bool = True,
                **kwargs) -> Optional[requests.Response]:
    """
    Make a safe HTTP request with error handling and retries.
    
    Args:
        url: URL to request
        method: HTTP method (GET, POST, etc.)
        headers: Optional request headers
        proxy_enabled: Whether to use proxies
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        **kwargs: Additional arguments for requests
        
    Returns:
        Response object or None on failure
    """
    # Set up default headers if none provided
    if headers is None:
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    # Set up proxies if enabled
    proxies = get_proxy_settings(proxy_enabled)
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            proxies=proxies,
            timeout=timeout,
            verify=verify_ssl,
            **kwargs
        )
        
        # Check for CAPTCHA in response
        if detect_captcha(response.text):
            logger.warning(f"CAPTCHA detected at URL: {url}")
            return None
            
        # Check response status
        response.raise_for_status()
        return response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for URL {url}: {str(e)}")
        return None

def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name or None if invalid URL
    """
    if not url:
        return None
        
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except Exception:
        return None

def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing extra whitespace and normalizing special characters.
    
    Args:
        text: The input text to sanitize
        
    Returns:
        Sanitized text string
    """
    if not text:
        return ""
    
    # Replace newlines, tabs, and multiple spaces with a single space
    sanitized = re.sub(r'\s+', ' ', str(text))
    # Remove leading/trailing whitespace
    sanitized = sanitized.strip()
    
    return sanitized

def wait_for_element(driver, selector, by_type=None, timeout=10, condition='presence'):
    """
    Wait for an element to be available in the page with intelligent waiting.
    
    Args:
        driver: Selenium WebDriver instance
        selector: CSS selector or XPath expression
        by_type: Selenium By type (e.g., By.CSS_SELECTOR, By.XPATH)
        timeout: Maximum time to wait (in seconds)
        condition: Type of wait condition ('presence', 'visibility', 'clickable')
        
    Returns:
        The element if found, None otherwise
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    
    if by_type is None:
        # Default to CSS selector
        by_type = By.CSS_SELECTOR
    
    try:
        if condition == 'presence':
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
        elif condition == 'visibility':
            element = WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by_type, selector))
            )
        elif condition == 'clickable':
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by_type, selector))
            )
        else:
            logger.warning(f"Unknown wait condition: {condition}, defaulting to presence")
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
            
        return element
    except TimeoutException:
        logger.warning(f"Timed out waiting for element: {selector} with condition: {condition}")
        return None

def wait_for_elements(driver, selector, by_type=None, timeout=10, condition='presence'):
    """
    Wait for multiple elements to be available in the page.
    
    Args:
        driver: Selenium WebDriver instance
        selector: CSS selector or XPath expression
        by_type: Selenium By type (e.g., By.CSS_SELECTOR, By.XPATH)
        timeout: Maximum time to wait (in seconds)
        condition: Type of wait condition ('presence', 'visibility')
        
    Returns:
        List of elements if found, empty list otherwise
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    
    if by_type is None:
        # Default to CSS selector
        by_type = By.CSS_SELECTOR
    
    try:
        if condition == 'presence':
            # Wait for at least one element to be present
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
        elif condition == 'visibility':
            # Wait for at least one element to be visible
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by_type, selector))
            )
        else:
            logger.warning(f"Unknown wait condition: {condition}, defaulting to presence")
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by_type, selector))
            )
        
        # Now get all elements
        elements = driver.find_elements(by_type, selector)
        return elements
    except TimeoutException:
        logger.warning(f"Timed out waiting for elements: {selector}")
        return []

def wait_for_page_change(driver, timeout=10, reference_element=None, url_change=True):
    """
    Wait for a page to change after clicking on navigation elements.
    Uses multiple strategies to detect page changes intelligently.
    
    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum time to wait (in seconds)
        reference_element: Optional reference element that should become stale
        url_change: Whether to check for URL changes
        
    Returns:
        True if page change detected, False otherwise
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
    
    try:
        # Store initial state
        initial_url = driver.current_url
        initial_page_source_length = len(driver.page_source)
        
        # Multiple checks for page change detection
        start_time = time.time()
        detected_change = False
        
        while time.time() - start_time < timeout and not detected_change:
            # Check URL change if requested
            if url_change and driver.current_url != initial_url:
                logger.debug(f"Detected URL change: {initial_url} -> {driver.current_url}")
                detected_change = True
                break
                
            # Check if reference element is stale (good indicator of page reload)
            if reference_element:
                try:
                    # Attempt to check a property - will raise exception if stale
                    reference_element.is_enabled()
                except StaleElementReferenceException:
                    logger.debug("Detected page change: reference element is stale")
                    detected_change = True
                    break
            
            # Check if page source length has changed significantly
            current_page_source_length = len(driver.page_source)
            if abs(current_page_source_length - initial_page_source_length) > 100:  # threshold
                logger.debug(f"Detected page change: page source length changed {initial_page_source_length} -> {current_page_source_length}")
                detected_change = True
                break
                
            # Small wait to prevent CPU hammering
            time.sleep(0.2)
        
        # Final wait for page to stabilize if change detected
        if detected_change:
            time.sleep(0.5)
            return True
        else:
            logger.warning("No page change detected within timeout period")
            return False
            
    except Exception as e:
        logger.error(f"Error while waiting for page change: {e}")
        return False
