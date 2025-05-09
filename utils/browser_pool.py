#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Browser Pool Manager

This module provides a browser pool manager to optimize Selenium usage by:
1. Reusing browser instances instead of creating new ones for each search
2. Managing browser resources efficiently
3. Ensuring proper cleanup of browser instances
4. Providing configurations for optimal performance
"""

import logging
import threading
import time
import os
import psutil
from typing import Dict, List, Any, Optional, Union, Callable
from queue import Queue, Empty
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException

# Try to import undetected_chromedriver, but don't fail if it's not available
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "undetected_chromedriver not installed; falling back to regular Selenium"
    )

# Create logger
logger = logging.getLogger(__name__)

class BrowserConfig:
    """Configuration options for browser instances in the pool."""
    
    def __init__(self, 
                 headless: bool = True,
                 use_undetected: bool = True,
                 page_load_strategy: str = "eager",
                 disable_images: bool = True,
                 proxy: Optional[str] = None,
                 user_agent: Optional[str] = None,
                 window_size: tuple = (1920, 1080),
                 additional_options: List[str] = None):
        """
        Initialize browser configuration.
        
        Args:
            headless: Whether to run the browser in headless mode
            use_undetected: Whether to use undetected_chromedriver (if available)
            page_load_strategy: Strategy for page loading ('normal', 'eager', or 'none')
            disable_images: Whether to disable images to save bandwidth and improve speed
            proxy: Optional proxy server to use (e.g., "socks5://127.0.0.1:9050")
            user_agent: Optional custom user agent string
            window_size: Tuple with (width, height) for browser window size
            additional_options: Additional Chrome options to add
        """
        self.headless = headless
        self.use_undetected = use_undetected and UNDETECTED_AVAILABLE
        self.page_load_strategy = page_load_strategy
        self.disable_images = disable_images
        self.proxy = proxy
        self.user_agent = user_agent
        self.window_size = window_size
        self.additional_options = additional_options or []
        
    def get_chrome_options(self) -> Union[ChromeOptions, 'uc.ChromeOptions']:
        """
        Get configured Chrome options based on this configuration.
        
        Returns:
            ChromeOptions object with all settings applied
        """
        # Use the appropriate options class
        if self.use_undetected:
            options = uc.ChromeOptions()
        else:
            options = ChromeOptions()
        
        # Basic anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Apply headless mode if requested
        if self.headless:
            options.add_argument("--headless=new")  # Use new headless mode for Chrome >= 109
        
        # Set window size
        if self.window_size:
            options.add_argument(f"--window-size={self.window_size[0]},{self.window_size[1]}")
        
        # Set user agent if provided
        if self.user_agent:
            options.add_argument(f"--user-agent={self.user_agent}")
        
        # Set proxy if provided
        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")
        
        # Disable images if requested
        if self.disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        # Set page load strategy
        options.page_load_strategy = self.page_load_strategy
        
        # Add any additional Chrome options
        for option in self.additional_options:
            options.add_argument(option)
        
        # Add experimental options for regular Selenium to make it less detectable
        if not self.use_undetected:
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
        
        return options


class ManagedBrowser:
    """
    Wrapper class for a managed browser instance in the pool.
    Tracks usage statistics and status of the browser.
    """
    
    def __init__(self, 
                 driver: Union[webdriver.Chrome, 'uc.Chrome'],
                 browser_id: str, 
                 config: BrowserConfig):
        """
        Initialize a managed browser instance.
        
        Args:
            driver: WebDriver instance
            browser_id: Unique identifier for this browser
            config: Configuration used to create this browser
        """
        self.driver = driver
        self.browser_id = browser_id
        self.config = config
        self.in_use = False
        self.last_used = time.time()
        self.total_uses = 0
        self.creation_time = time.time()
        self.errors = 0
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        
    def acquire(self) -> bool:
        """
        Mark the browser as in use.
        
        Returns:
            True if successfully acquired, False if already in use
        """
        with self.lock:
            if self.in_use:
                return False
            self.in_use = True
            self.last_used = time.time()
            self.total_uses += 1
            return True
    
    def release(self) -> None:
        """Mark the browser as no longer in use."""
        with self.lock:
            self.in_use = False
            self.last_used = time.time()
    
    def record_error(self) -> None:
        """Record that an error occurred while using this browser."""
        with self.lock:
            self.errors += 1
    
    def close(self) -> None:
        """Close and quit the browser properly."""
        with self.lock:
            if self.driver:
                try:
                    # First try regular close
                    self.driver.close()
                except Exception as e:
                    logger.debug(f"Error during driver.close() for {self.browser_id}: {str(e)}")
                
                try:
                    # Then quit the driver completely
                    self.driver.quit()
                except Exception as e:
                    logger.debug(f"Error during driver.quit() for {self.browser_id}: {str(e)}")
                
                self.driver = None
    
    def get_age(self) -> float:
        """
        Get the age of this browser instance in seconds.
        
        Returns:
            Age in seconds
        """
        return time.time() - self.creation_time
    
    def get_idle_time(self) -> float:
        """
        Get how long this browser has been idle in seconds.
        
        Returns:
            Idle time in seconds
        """
        if self.in_use:
            return 0
        return time.time() - self.last_used
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this browser.
        
        Returns:
            Dictionary with browser statistics
        """
        with self.lock:
            return {
                "browser_id": self.browser_id,
                "total_uses": self.total_uses,
                "errors": self.errors,
                "in_use": self.in_use,
                "age_seconds": self.get_age(),
                "idle_time_seconds": self.get_idle_time(),
                "headless": self.config.headless,
                "undetected": self.config.use_undetected
            }
    
    def reset(self) -> bool:
        """
        Try to reset the browser to a clean state.
        
        Returns:
            True if reset successful, False otherwise
        """
        with self.lock:
            try:
                # Clear cookies
                self.driver.delete_all_cookies()
                
                # Clear local storage if possible
                try:
                    self.driver.execute_script("window.localStorage.clear();")
                except:
                    pass
                
                # Clear session storage if possible
                try:
                    self.driver.execute_script("window.sessionStorage.clear();")
                except:
                    pass
                
                # Navigate to blank page
                self.driver.get("about:blank")
                
                return True
            except Exception as e:
                logger.warning(f"Error resetting browser {self.browser_id}: {str(e)}")
                self.record_error()
                return False


class BrowserPool:
    """
    Pool manager for browser instances to optimize resource usage.
    Maintains a pool of reusable browser instances for scraping tasks.
    """
    
    def __init__(self, 
                 max_browsers: int = 5,
                 browser_lifetime: int = 3600,  # 1 hour by default
                 browser_max_uses: int = 20,
                 browser_max_errors: int = 3,
                 default_config: Optional[BrowserConfig] = None,
                 cleanup_frequency: int = 300):  # 5 minutes by default
        """
        Initialize the browser pool.
        
        Args:
            max_browsers: Maximum number of browsers in the pool
            browser_lifetime: Maximum lifetime of a browser in seconds
            browser_max_uses: Maximum number of uses before recycling
            browser_max_errors: Maximum number of errors before recycling
            default_config: Default configuration for browsers
            cleanup_frequency: How often to check for browsers to clean up (seconds)
        """
        self.max_browsers = max_browsers
        self.browser_lifetime = browser_lifetime
        self.browser_max_uses = browser_max_uses
        self.browser_max_errors = browser_max_errors
        self.default_config = default_config or BrowserConfig()
        self.cleanup_frequency = cleanup_frequency
        
        self.browsers: List[ManagedBrowser] = []
        self.browser_counter = 0
        
        self.pool_lock = threading.RLock()
        self.last_cleanup = time.time()
        
        # Start cleanup thread
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"Browser pool initialized with max {max_browsers} browsers")
    
    def _create_browser(self, config: BrowserConfig = None) -> Optional[ManagedBrowser]:
        """
        Create a new browser instance with the given configuration.
        
        Args:
            config: Browser configuration to use (or default if None)
            
        Returns:
            ManagedBrowser instance or None if creation failed
        """
        with self.pool_lock:
            if len(self.browsers) >= self.max_browsers:
                logger.warning(f"Cannot create new browser: pool limit ({self.max_browsers}) reached")
                return None
            
            browser_config = config or self.default_config
            browser_id = f"browser_{self.browser_counter}"
            self.browser_counter += 1
            
            try:
                # Create options
                options = browser_config.get_chrome_options()
                
                # Create driver
                driver = None
                if browser_config.use_undetected:
                    logger.debug(f"Creating undetected Chrome browser {browser_id}")
                    try:
                        # First try with auto-detection
                        driver = uc.Chrome(options=options, use_subprocess=True)
                    except Exception as e:
                        logger.warning(f"Auto Chrome version detection failed: {str(e)}")
                        # Try with specific major versions of Chrome
                        versions_to_try = [136, 135, 130, 129, 128, 127, 126, 125, 124, 123, 122]
                        for version in versions_to_try:
                            try:
                                logger.debug(f"Trying with Chrome version: {version}")
                                driver = uc.Chrome(
                                    options=options,
                                    version_main=version,
                                    use_subprocess=True
                                )
                                logger.debug(f"Successfully created with Chrome version: {version}")
                                break
                            except Exception:
                                continue
                
                # Fall back to regular Selenium if undetected_chromedriver fails or is disabled
                if driver is None:
                    logger.debug(f"Creating regular Chrome browser {browser_id}")
                    driver = webdriver.Chrome(options=options)
                    
                    # Apply additional anti-detection measures via JavaScript
                    try:
                        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                            "source": """
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                            """
                        })
                    except Exception as e:
                        logger.debug(f"Failed to apply anti-detection script: {str(e)}")
                
                # Configure implicit wait
                driver.implicitly_wait(10)  # 10 seconds implicit wait
                
                # Create managed browser
                browser = ManagedBrowser(driver, browser_id, browser_config)
                self.browsers.append(browser)
                
                logger.info(f"Created new browser {browser_id} (pool size: {len(self.browsers)}/{self.max_browsers})")
                return browser
                
            except Exception as e:
                logger.error(f"Error creating browser {browser_id}: {str(e)}")
                return None
    
    def get_browser(self, config: BrowserConfig = None) -> Optional[ManagedBrowser]:
        """
        Get an available browser from the pool, or create a new one if needed.
        
        Args:
            config: Optional specific configuration for the browser
            
        Returns:
            ManagedBrowser instance or None if no browser could be obtained
        """
        with self.pool_lock:
            # First try to find an available browser
            for browser in self.browsers:
                # Skip browsers that are in use
                if browser.in_use:
                    continue
                
                # Skip browsers that should be recycled
                if (browser.get_age() > self.browser_lifetime or 
                    browser.total_uses >= self.browser_max_uses or 
                    browser.errors >= self.browser_max_errors):
                    continue
                
                # Try to acquire this browser
                if browser.acquire():
                    logger.debug(f"Reusing existing browser {browser.browser_id}")
                    
                    # Reset browser state before reuse
                    if not browser.reset():
                        logger.warning(f"Failed to reset browser {browser.browser_id}, creating a new one instead")
                        browser.release()  # Release this browser so it can be cleaned up
                        break  # Exit the loop to create a new browser
                    
                    return browser
            
            # Create a new browser if we couldn't find a suitable existing one
            browser = self._create_browser(config)
            if browser:
                browser.acquire()  # Immediately mark it as in use
                return browser
            
            # If we reach here, we couldn't get a browser
            logger.warning("Failed to get a browser from the pool")
            return None
    
    def release_browser(self, browser: ManagedBrowser) -> None:
        """
        Release a browser back to the pool.
        
        Args:
            browser: The browser to release
        """
        if not browser:
            return
        
        with self.pool_lock:
            if browser in self.browsers:
                browser.release()
                logger.debug(f"Released browser {browser.browser_id} back to pool")
            else:
                logger.warning(f"Attempted to release unknown browser {browser.browser_id}")
    
    def remove_browser(self, browser: ManagedBrowser) -> None:
        """
        Remove and close a browser from the pool.
        
        Args:
            browser: The browser to remove
        """
        if not browser:
            return
        
        with self.pool_lock:
            if browser in self.browsers:
                self.browsers.remove(browser)
                logger.debug(f"Removed browser {browser.browser_id} from pool")
            else:
                logger.warning(f"Attempted to remove unknown browser {browser.browser_id}")
            
            # Close the browser regardless of whether it was in our pool
            browser.close()
    
    def _cleanup_worker(self) -> None:
        """Background worker that periodically cleans up old browsers."""
        try:
            while self.running:
                time.sleep(5)  # Check frequently but only clean up based on cleanup_frequency
                
                current_time = time.time()
                if current_time - self.last_cleanup < self.cleanup_frequency:
                    continue
                
                self._cleanup_browsers()
                self.last_cleanup = current_time
                
        except Exception as e:
            logger.error(f"Error in cleanup worker: {str(e)}")
    
    def _cleanup_browsers(self) -> None:
        """Clean up old or problematic browser instances."""
        with self.pool_lock:
            browsers_to_remove = []
            
            # Check each browser
            for browser in self.browsers:
                # Skip browsers that are in use
                if browser.in_use:
                    continue
                
                # Check if browser should be recycled
                if (browser.get_age() > self.browser_lifetime or 
                    browser.total_uses >= self.browser_max_uses or 
                    browser.errors >= self.browser_max_errors or
                    browser.get_idle_time() > self.cleanup_frequency * 2):  # Remove if idle for too long
                    browsers_to_remove.append(browser)
            
            # Remove identified browsers
            for browser in browsers_to_remove:
                self.browsers.remove(browser)
                logger.info(f"Cleaning up browser {browser.browser_id} (age: {browser.get_age():.1f}s, uses: {browser.total_uses}, errors: {browser.errors})")
                browser.close()
            
            if browsers_to_remove:
                logger.info(f"Cleaned up {len(browsers_to_remove)} browsers. Pool size: {len(self.browsers)}/{self.max_browsers}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the browser pool.
        
        Returns:
            Dictionary with pool statistics
        """
        with self.pool_lock:
            in_use = sum(1 for browser in self.browsers if browser.in_use)
            
            browser_stats = [browser.get_stats() for browser in self.browsers]
            
            # Get system memory info
            memory_info = {}
            try:
                process = psutil.Process(os.getpid())
                memory_info = {
                    "rss_mb": process.memory_info().rss / (1024 * 1024),
                    "vms_mb": process.memory_info().vms / (1024 * 1024),
                    "percent": process.memory_percent()
                }
            except:
                pass
            
            return {
                "total_browsers": len(self.browsers),
                "in_use": in_use,
                "available": len(self.browsers) - in_use,
                "max_browsers": self.max_browsers,
                "browser_stats": browser_stats,
                "memory_info": memory_info
            }
    
    def shutdown(self) -> None:
        """Shutdown the pool and close all browsers."""
        logger.info("Shutting down browser pool...")
        
        # Stop the cleanup thread
        self.running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2)
        
        # Close all browsers
        with self.pool_lock:
            for browser in self.browsers:
                try:
                    logger.debug(f"Closing browser {browser.browser_id}")
                    browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser {browser.browser_id}: {str(e)}")
            
            self.browsers = []
        
        logger.info("Browser pool shutdown complete")


# Global browser pool instance to be used throughout the application
_global_browser_pool = None

def get_browser_pool(max_browsers: int = None) -> BrowserPool:
    """
    Get or create the global browser pool.
    
    Args:
        max_browsers: Maximum browsers to use if creating a new pool
        
    Returns:
        The global browser pool instance
    """
    global _global_browser_pool
    
    if _global_browser_pool is None:
        if max_browsers is None:
            # Default to (CPU count) or 3, whichever is smaller
            import os
            max_browsers = min(os.cpu_count() or 4, 3)
        
        # Create default configuration
        default_config = BrowserConfig(
            headless=os.environ.get("HEADLESS_BROWSER", "True").lower() == "true",
            use_undetected=os.environ.get("USE_UNDETECTED_DRIVER", "True").lower() == "true",
            page_load_strategy=os.environ.get("PAGE_LOAD_STRATEGY", "eager"),
            disable_images=os.environ.get("DISABLE_BROWSER_IMAGES", "True").lower() == "true"
        )
        
        # Create pool
        _global_browser_pool = BrowserPool(
            max_browsers=max_browsers,
            default_config=default_config,
            browser_lifetime=int(os.environ.get("BROWSER_LIFETIME_SECONDS", "3600")),
            browser_max_uses=int(os.environ.get("BROWSER_MAX_USES", "20")),
            browser_max_errors=int(os.environ.get("BROWSER_MAX_ERRORS", "3"))
        )
    
    return _global_browser_pool

def shutdown_browser_pool() -> None:
    """Shutdown the global browser pool if it exists."""
    global _global_browser_pool
    
    if _global_browser_pool:
        _global_browser_pool.shutdown()
        _global_browser_pool = None
