#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeadScraper LATAM - Main Application

This is the main entry point for the LeadScraper LATAM application.
It orchestrates the scraping process from multiple sources (Google Maps, Instagram,
public directories), processes the collected data, and uploads it to Google Sheets.
"""

import os
import sys
import json
import logging
import argparse
import time
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from scrapers.google_maps_scraper import GoogleMapsScraper
from scrapers.instagram_scraper import InstagramScraper
from scrapers.paginas_amarillas_scraper import PaginasAmarillasScraper
from scrapers.guialocal_scraper import GuiaLocalScraper
from scrapers.cylex_scraper import CylexScraper
from processing.data_processor import ValidationProcessor
from integrations.google_sheets import GoogleSheetsIntegration
from utils.helpers import load_config_from_env, setup_logger

# Import advanced error handling and monitoring modules
from utils.logging_utils import setup_advanced_logger
from utils.monitoring import initialize_monitoring, shutdown_monitoring, metrics_registry, scraper_metrics
from utils.notification import configure_notifications_from_env, notify, NotificationLevel
from utils.retry import configure_retry_from_env, retry_manager
from utils.dashboard import BasicDashboard, AdvancedDashboard, MetricsManager
from utils.data_quality import create_data_quality_monitor, DataQualityConfig

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"leadscraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Use advanced logger if available, otherwise fall back to basic logger
try:
    logger = setup_advanced_logger(
        name="leadscraper_main",
        log_dir=log_dir,
        log_file=log_file,
        console=True,
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        json_format=os.environ.get("LOG_JSON_FORMAT", "False").lower() == "true",
        rotate_logs=True,
        filter_sensitive=True,
        context={"app_version": "1.0.0", "environment": os.environ.get("ENVIRONMENT", "production")}
    )
    logger.info("Advanced logging initialized successfully")
except (ImportError, NameError):
    # Fall back to basic logger
    logger = setup_logger(
        "leadscraper_main",
        log_file=log_file,
        console=True,
        log_level=os.environ.get("LOG_LEVEL", "INFO")
    )
    logger.info("Basic logging initialized (advanced logging not available)")

# Load environment variables
load_dotenv()

class ConfigManager:
    """
    Configuration manager for the LeadScraper application.
    Handles loading and validating configuration from environment variables and files.
    """
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config = {}
        self.scraper_configs = {}
        self.google_sheets_config = {}
        self.processing_config = {}
        self.loaded = False
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables and config files.
        
        Returns:
            Dict with configuration values
        """
        if self.loaded:
            return self.config
        
        # Load main configuration from environment
        self.config = load_config_from_env()
        
        # Load scraper configurations
        self._load_scraper_configs()
        
        # Load Google Sheets configuration
        self._load_google_sheets_config()
        
        # Load processing configuration
        self._load_processing_config()
        
        self.loaded = True
        logger.info("Configuration loaded successfully")
        return self.config
    
    def _load_scraper_configs(self) -> None:
        """Load scraper-specific configurations."""
        # Google Maps configuration
        self.scraper_configs["google_maps"] = {
            "search_queries": self._parse_search_queries(os.environ.get("GOOGLE_MAPS_QUERIES", "[]")),
            "max_results": int(os.environ.get("GOOGLE_MAPS_MAX_RESULTS", "100")),
            "headless": os.environ.get("HEADLESS_BROWSER", "False").lower() == "true",  # Changed default to "False"
            "request_delay": float(os.environ.get("GOOGLE_MAPS_WAIT_TIME", "2.0")),  # Changed from wait_time
            "enabled": os.environ.get("ENABLE_GOOGLE_MAPS", "True").lower() == "true"
        }
        
        # Instagram configuration
        self.scraper_configs["instagram"] = {
            "username": os.environ.get("INSTAGRAM_USERNAME", ""),
            "password": os.environ.get("INSTAGRAM_PASSWORD", ""),
            "hashtags": os.environ.get("INSTAGRAM_HASHTAGS", "").split(",") if os.environ.get("INSTAGRAM_HASHTAGS") else [],
            "locations": os.environ.get("INSTAGRAM_LOCATIONS", "").split(",") if os.environ.get("INSTAGRAM_LOCATIONS") else [],
            "max_results": int(os.environ.get("INSTAGRAM_MAX_RESULTS", "100")),  # Changed from max_posts and INSTAGRAM_MAX_POSTS
            "enabled": os.environ.get("ENABLE_INSTAGRAM", "True").lower() == "true"
        }
        
        # Directory scrapers configuration
        self.scraper_configs["directories"] = {
            "enabled_directories": os.environ.get("DIRECTORIES_TO_SCRAPE", "").split(",") if os.environ.get("DIRECTORIES_TO_SCRAPE") else ["paginas_amarillas", "guialocal", "cylex"],
            "search_queries": self._parse_search_queries(os.environ.get("DIRECTORY_QUERIES", "[]")),
            "max_results": int(os.environ.get("DIRECTORY_MAX_RESULTS", "50")),
            "wait_time": float(os.environ.get("DIRECTORY_WAIT_TIME", "3.0")),
            "enabled": os.environ.get("ENABLE_DIRECTORIES", "True").lower() == "true"
        }
        
    def _load_google_sheets_config(self) -> None:
        """Load Google Sheets integration configuration."""
        self.google_sheets_config = {
            "service_account_file": os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", ""),
            "spreadsheet_id": os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", ""),
            "sheet_title": os.environ.get("GOOGLE_SHEETS_TITLE", f"LeadScraper Results {datetime.now().strftime('%Y-%m-%d')}"),
            "append_mode": os.environ.get("GOOGLE_SHEETS_APPEND", "True").lower() == "true",
            "enabled": os.environ.get("ENABLE_GOOGLE_SHEETS", "True").lower() == "true",
            "batch_size": int(os.environ.get("GOOGLE_SHEETS_BATCH_SIZE", "1000"))
        }
    
    def _load_processing_config(self) -> None:
        """Load data processing configuration."""
        self.processing_config = {
            "deduplication": {
                "exact_match": os.environ.get("DEDUPLICATION_EXACT", "True").lower() == "true",
                "fuzzy_match": os.environ.get("DEDUPLICATION_FUZZY", "True").lower() == "true",
                "fuzzy_threshold": float(os.environ.get("FUZZY_THRESHOLD", "80")),
                "match_fields": os.environ.get("MATCH_FIELDS", "business_name,phone,email").split(","),
                "use_parallel_processing": os.environ.get("USE_PARALLEL_PROCESSING", "True").lower() == "true",
                "batch_size": int(os.environ.get("BATCH_SIZE", "5000"))
            },
            "validation": {
                "enable_email_validation": os.environ.get("VALIDATE_EMAILS", "True").lower() == "true",
                "enable_phone_validation": os.environ.get("VALIDATE_PHONES", "True").lower() == "true",
                "min_data_quality": float(os.environ.get("MIN_DATA_QUALITY", "0.5"))
            }
        }
    
    def _parse_search_queries(self, query_json: str) -> List[Dict[str, str]]:
        """
        Parse search queries from JSON string.
        
        Args:
            query_json: JSON string with search queries
            
        Returns:
            List of dictionaries with query and location
        """
        try:
            queries = json.loads(query_json)
            if not isinstance(queries, list):
                logger.warning(f"Invalid search query format: {query_json}. Using default.")
                return []
            return queries
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse search queries: {query_json}. Using default.")
            return []
    
    def get_scraper_config(self, scraper_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific scraper.
        
        Args:
            scraper_name: Name of the scraper (google_maps, instagram, directories)
            
        Returns:
            Configuration dictionary for the requested scraper
        """
        return self.scraper_configs.get(scraper_name, {})
    
    def get_google_sheets_config(self) -> Dict[str, Any]:
        """
        Get Google Sheets integration configuration.
        
        Returns:
            Configuration dictionary for Google Sheets
        """
        return self.google_sheets_config
    
    def get_processing_config(self) -> Dict[str, Any]:
        """
        Get data processing configuration.
        
        Returns:
            Configuration dictionary for data processing
        """
        return self.processing_config

def initialize_error_handling_and_monitoring():
    """
    Initialize error handling, monitoring, and notification systems.
    """
    try:
        # Initialize retry system
        retry_config = configure_retry_from_env()
        logger.info("Retry system initialized successfully")
        
        # Initialize notification system
        notification_config = configure_notifications_from_env()
        logger.info("Notification system initialized successfully")
        
        # Initialize monitoring system
        metrics_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metrics")
        os.makedirs(metrics_dir, exist_ok=True)
        metrics_path = os.path.join(metrics_dir, "scraper_metrics.json")
        
        metrics, system, scraper = initialize_monitoring(
            metrics_export_path=metrics_path,
            metrics_export_interval=int(os.environ.get("METRICS_EXPORT_INTERVAL", "300")),
            enable_system_monitoring=os.environ.get("ENABLE_SYSTEM_MONITORING", "True").lower() == "true",
            system_monitoring_interval=int(os.environ.get("SYSTEM_MONITORING_INTERVAL", "60"))
        )
        logger.info("Monitoring system initialized successfully")
        
        # Initialize data quality monitoring
        data_quality_config_path = os.environ.get("DATA_QUALITY_CONFIG_PATH", None)
        if not data_quality_config_path:
            # Check for default config file
            default_config = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "data_quality.json")
            if os.path.exists(default_config):
                data_quality_config_path = default_config
        
        # Create data quality monitor
        global data_quality_monitor
        data_quality_monitor = create_data_quality_monitor(
            metrics_registry=metrics_registry,
            config_path=data_quality_config_path,
            notification_manager=notification_config if os.environ.get("NOTIFY_ON_DATA_QUALITY_ISSUES", "True").lower() == "true" else None
        )
        logger.info("Data quality monitoring initialized successfully")
        
        # Initialize dashboard if enabled
        dashboard_enabled = os.environ.get("ENABLE_DASHBOARD", "False").lower() == "true"
        if dashboard_enabled:
            # Create dashboard directories
            dashboard_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")
            os.makedirs(dashboard_dir, exist_ok=True)
            
            # Try to use advanced dashboard if dependencies are available
            try:
                import dash
                import plotly
                
                # Start dashboard in a separate thread
                from threading import Thread
                
                metrics_manager = MetricsManager(metrics_dir)
                dashboard = AdvancedDashboard(metrics_manager)
                dashboard_app = dashboard.create_app()
                
                # Get port from environment or use default
                dashboard_port = int(os.environ.get("DASHBOARD_PORT", "8050"))
                
                dashboard_thread = Thread(
                    target=dashboard.start_dashboard,
                    kwargs={"port": dashboard_port, "debug": False},
                    daemon=True
                )
                dashboard_thread.start()
                
                logger.info(f"Advanced dashboard initialized on port {dashboard_port}")
                
                # Open browser if requested
                if os.environ.get("OPEN_DASHBOARD_ON_STARTUP", "False").lower() == "true":
                    dashboard.open_dashboard(dashboard_port)
            
            except ImportError:
                # Fall back to basic dashboard
                logger.info("Advanced dashboard dependencies not available, using basic dashboard")
                
                metrics_manager = MetricsManager(metrics_dir)
                dashboard = BasicDashboard(metrics_manager, dashboard_dir)
                
                # Generate initial dashboard
                dashboard_path = dashboard.generate_dashboard()
                logger.info(f"Basic dashboard generated at {dashboard_path}")
                
                # Open in browser if requested
                if os.environ.get("OPEN_DASHBOARD_ON_STARTUP", "False").lower() == "true":
                    import webbrowser
                    webbrowser.open(f"file://{dashboard_path}")
        
        # Register shutdown handler
        import atexit
        atexit.register(shutdown_monitoring)
        
        # Send startup notification if enabled
        startup_notification = os.environ.get("NOTIFY_ON_STARTUP", "False").lower() == "true"
        if startup_notification:
            notify(
                subject="ScraperMVP Started",
                message=f"ScraperMVP started at {datetime.now().isoformat()}",
                level="INFO"
            )
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize error handling and monitoring: {str(e)}", exc_info=True)
        # Attempt to send a notification about this critical initialization failure
        try:
            notify(
                subject="Critical Initialization Failure: Error Handling & Monitoring",
                message=f"The application failed to initialize its error handling and monitoring systems. Error: {str(e)}",
                level="CRITICAL",
                additional_data={"error_type": type(e).__name__, "component": "initialization"}
            )
            logger.info("Attempted to send notification for initialization failure.")
        except Exception as notify_exc:
            logger.error(f"Could not send notification for initialization failure: {notify_exc}", exc_info=True)
        # Continue with basic functionality
        return False


def main(args=None):
    """
    Main function to orchestrate the scraping, processing and uploading workflow.
    
    Args:
        args: Command line arguments
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("Starting LeadScraper LATAM")
    start_time = time.time()
    
    try:
        # Initialize error handling and monitoring systems
        initialize_error_handling_and_monitoring()
        
        # Start metrics collection
        metrics_registry.inc_counter("app.starts")
        scrape_timer_id = scraper_metrics.record_scrape_start("main", "all_sources")
        
        # Parse command line arguments if provided
        if args is None:
            parser = argparse.ArgumentParser(description="LeadScraper LATAM - Business lead generation tool")
            parser.add_argument("--config", help="Path to configuration file (optional)")
            parser.add_argument("--output", help="Path to output directory for results (optional)")
            parser.add_argument("--no-sheets", action="store_true", help="Disable Google Sheets upload")
            parser.add_argument("--no-gmaps", action="store_true", help="Disable Google Maps scraping")
            parser.add_argument("--no-insta", action="store_true", help="Disable Instagram scraping")
            parser.add_argument("--no-directories", action="store_true", help="Disable Directory scraping")
            parser.add_argument("--monitor", action="store_true", help="Enable enhanced monitoring")
            args = parser.parse_args()
        
        # Create results directory if needed
        results_dir = args.output if args and args.output else os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(results_dir, exist_ok=True)
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Override configuration with command line arguments if provided
        if args:
            if args.no_sheets:
                config_manager.google_sheets_config["enabled"] = False
            if args.no_gmaps:
                config_manager.scraper_configs["google_maps"]["enabled"] = False
            if args.no_insta:
                config_manager.scraper_configs["instagram"]["enabled"] = False
            if args.no_directories:
                config_manager.scraper_configs["directories"]["enabled"] = False
    
        # Track errors and results for summary reporting
        run_stats = {
            "start_time": datetime.now(),
            "scrapers_run": 0,
            "total_leads_found": 0,
            "leads_after_processing": 0,
            "errors": [],
            "scraper_stats": {}
        }
        
        all_results = []
        
        # Run scrapers and process data
        # [implementations continue here...]
        
        # Generate run summary
        run_stats["end_time"] = datetime.now()
        run_stats["duration_seconds"] = (run_stats["end_time"] - run_stats["start_time"]).total_seconds()
        
        logger.info("Generating run summary...")
        summary = generate_run_summary(run_stats)
        
        # Save the summary to a file
        summary_file = os.path.join(results_dir, f"run_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, default=str, indent=2)
        
        logger.info(f"Run summary saved to {summary_file}")
        
        if run_stats["errors"]:
            logger.warning(f"LeadScraper LATAM completed with {len(run_stats['errors'])} errors.")
            for error in run_stats["errors"]:
                logger.warning(f"- {error['component']}: {error['error']}")
        else:
            logger.info("LeadScraper LATAM completed successfully with no errors.")
        
        print("\n" + "-"*50)
        print_summary(summary)
        print("-"*50 + "\n")
        
        # Return appropriate exit code based on errors
        return 1 if run_stats["errors"] else 0
    
    except Exception as e:
        logger.error(f"Unexpected error in main(): {str(e)}", exc_info=True)
        
        # Try to send critical error notification
        try:
            notify(
                subject="Critical Scraper Failure",
                message=f"The scraper encountered a critical error: {str(e)}",
                level="CRITICAL",
                additional_data={"error_type": type(e).__name__, "component": "main"}
            )
        except:
            pass  # Don't let notification failure cause more issues
        
        return 1
        
        # Initialize and run scrapers
        if config_manager.scraper_configs["google_maps"]["enabled"]:
            try:
                logger.info("Starting Google Maps scraping...")
                
                # Track metrics
                gmaps_timer_id = scraper_metrics.record_scrape_start("google_maps", str(config_manager.scraper_configs["google_maps"]["search_queries"]))
                
                # Run scraper with retry logic
                google_maps_results = run_google_maps_scraper(config_manager.scraper_configs["google_maps"])
                all_results.extend(google_maps_results)
                
                # Save raw results
                save_results(google_maps_results, os.path.join(results_dir, f"google_maps_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"))
                
                # Track stats and metrics
                run_stats["scraper_stats"]["google_maps"] = {
                    "success": True,
                    "results_count": len(google_maps_results),
                    "queries_processed": len(config_manager.scraper_configs["google_maps"]["search_queries"])
                }
                run_stats["scrapers_run"] += 1
                run_stats["total_leads_found"] += len(google_maps_results)
                
                # Record success in metrics
                scraper_metrics.record_scrape_success("google_maps", gmaps_timer_id, len(google_maps_results))
                metrics_registry.inc_counter("scraper.google_maps.success")
                
                logger.info(f"Google Maps scraping completed. Found {len(google_maps_results)} leads.")
                # Data Quality Monitoring
                try:
                    df = pd.DataFrame(google_maps_results)
                    dq = data_quality_monitor.process_dataset(df, source_name="google_maps")
                    logger.info(f"Data quality for Google Maps: {dq['quality_score']:.1f}/100")
                except Exception as e:
                    logger.error(f"Data quality monitoring failed for Google Maps: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error in Google Maps scraping: {str(e)}", exc_info=True)
                run_stats["errors"].append({
                    "component": "google_maps_scraper",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                run_stats["scraper_stats"]["google_maps"] = {"success": False, "error": str(e)}
                
                # Record failure in metrics
                if 'gmaps_timer_id' in locals():
                    scraper_metrics.record_scrape_failure("google_maps", gmaps_timer_id, str(e))
                metrics_registry.inc_counter("scraper.google_maps.failure")
                
                # Send notification for critical failure
                notify(
                    subject="Google Maps Scraper Failure",
                    message=f"Google Maps scraping failed: {str(e)}",
                    level="ERROR",
                    additional_data={"error_type": type(e).__name__, "component": "google_maps_scraper"}
                )
            
        if config_manager.scraper_configs["instagram"]["enabled"]:
            try:
                logger.info("Starting Instagram scraping...")
                
                # Track metrics
                insta_timer_id = scraper_metrics.record_scrape_start("instagram", 
                                                                    f"hashtags:{config_manager.scraper_configs['instagram']['hashtags']}, locations:{config_manager.scraper_configs['instagram']['locations']}")
                
                # Run scraper with retry logic
                instagram_results = run_instagram_scraper(config_manager.scraper_configs["instagram"])
                all_results.extend(instagram_results)
                
                # Save raw results
                save_results(instagram_results, os.path.join(results_dir, f"instagram_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"))
                
                # Track stats and metrics
                run_stats["scraper_stats"]["instagram"] = {
                    "success": True,
                    "results_count": len(instagram_results),
                    "hashtags_processed": len(config_manager.scraper_configs["instagram"]["hashtags"]),
                    "locations_processed": len(config_manager.scraper_configs["instagram"]["locations"])
                }
                run_stats["scrapers_run"] += 1
                run_stats["total_leads_found"] += len(instagram_results)
                
                # Record success in metrics
                scraper_metrics.record_scrape_success("instagram", insta_timer_id, len(instagram_results))
                metrics_registry.inc_counter("scraper.instagram.success")
                
                logger.info(f"Instagram scraping completed. Found {len(instagram_results)} leads.")
                # Data Quality Monitoring for Instagram results
                try:
                    df_insta = pd.DataFrame(instagram_results)
                    dq_insta = data_quality_monitor.process_dataset(df_insta, source_name="instagram")
                    logger.info(f"Data quality for Instagram: {dq_insta['quality_score']:.1f}/100")
                except Exception as e:
                    logger.error(f"Data quality monitoring failed for Instagram: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error in Instagram scraping: {str(e)}", exc_info=True)
                run_stats["errors"].append({
                    "component": "instagram_scraper",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                run_stats["scraper_stats"]["instagram"] = {"success": False, "error": str(e)}
                
                # Record failure in metrics
                if 'insta_timer_id' in locals():
                    scraper_metrics.record_scrape_failure("instagram", insta_timer_id, str(e))
                metrics_registry.inc_counter("scraper.instagram.failure")
                
                # Send notification for critical failure
                notify(
                    subject="Instagram Scraper Failure",
                    message=f"Instagram scraping failed: {str(e)}",
                    level="ERROR",
                    additional_data={"error_type": type(e).__name__, "component": "instagram_scraper"}
                )
            
        if config_manager.scraper_configs["directories"]["enabled"]:
            try:
                logger.info("Starting directory scraping...")
                
                # Track metrics for directories
                dir_timer_id = scraper_metrics.record_scrape_start("directories", 
                                                                  f"queries:{config_manager.scraper_configs['directories']['search_queries']}")
                
                directory_results = run_directory_scrapers(config_manager.scraper_configs["directories"])
                all_results.extend(directory_results)
                
                # Save raw results
                save_results(directory_results, os.path.join(results_dir, f"directories_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"))
                
                run_stats["scraper_stats"]["directories"] = {
                    "success": True,
                    "results_count": len(directory_results),
                    "directories_processed": len(config_manager.scraper_configs["directories"]["enabled_directories"])
                }
                run_stats["scrapers_run"] += 1
                run_stats["total_leads_found"] += len(directory_results)
                
                # Record success in metrics
                scraper_metrics.record_scrape_success("directories", dir_timer_id, len(directory_results))
                metrics_registry.inc_counter("scraper.directories.success")
                
                logger.info(f"Directory scraping completed. Found {len(directory_results)} leads.")
                # Data Quality Monitoring for Directory results
                try:
                    df_dir = pd.DataFrame(directory_results)
                    dq_dir = data_quality_monitor.process_dataset(df_dir, source_name="directories")
                    logger.info(f"Data quality for Directories: {dq_dir['quality_score']:.1f}/100")
                except Exception as e:
                    logger.error(f"Data quality monitoring failed for Directories: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error in directory scraping: {str(e)}", exc_info=True)
                run_stats["errors"].append({
                    "component": "directory_scrapers",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                run_stats["scraper_stats"]["directories"] = {"success": False, "error": str(e)}
                
                # Record failure in metrics
                if 'dir_timer_id' in locals():
                    scraper_metrics.record_scrape_failure("directories", dir_timer_id, str(e))
                metrics_registry.inc_counter("scraper.directories.failure")
                
                # Send notification for critical failure
                notify(
                    subject="Directory Scrapers Failure",
                    message=f"Directory scraping failed: {str(e)}",
                    level="ERROR",
                    additional_data={"error_type": type(e).__name__, "component": "directory_scrapers"}
                )
            
        # Process and validate data
        if all_results:
            try:
                logger.info(f"Processing {len(all_results)} leads...")
                
                # Create a DataFrame from all collected results
                all_results_df = pd.DataFrame(all_results)
                
                # Process and upload data using our integrated function
                merged_config = {
                    "processing": config_manager.get_processing_config(),
                    "google_sheets": config_manager.get_google_sheets_config()
                }
                
                processed_data, sheets_upload_results = process_and_upload_data(all_results_df, merged_config)
                
                # Save processed results
                processed_file_path = os.path.join(results_dir, f"processed_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                processed_data.to_csv(processed_file_path, index=False)
                logger.info(f"Processed data saved to {processed_file_path}")
                
                # Update run_stats with the processed data info
                run_stats["leads_after_processing"] = len(processed_data)
                logger.info(f"Data processing completed. {len(processed_data)} leads after deduplication and validation.")
                
                # Add Google Sheets status to run stats if applicable
                if config_manager.google_sheets_config["enabled"] and sheets_upload_results:
                    try:
                        if sheets_upload_results.get("error"):
                            sheets_info = {
                                "success": False,
                                "error": sheets_upload_results.get("error"),
                                "spreadsheet_id": sheets_upload_results.get("spreadsheet_id", ""),
                                "spreadsheet_url": sheets_upload_results.get("spreadsheet_url", "")
                            }
                            logger.error(f"Google Sheets operation failed: {sheets_info.get('error')}")
                        else:
                            sheets_info = {
                                "success": True,
                                "rows_uploaded": sheets_upload_results.get("rows_uploaded", 0),
                                "spreadsheet_id": sheets_upload_results.get("spreadsheet_id", ""),
                                "spreadsheet_url": sheets_upload_results.get("spreadsheet_url", "")
                            }
                            logger.info(f"Upload to Google Sheets completed successfully. Spreadsheet URL: {sheets_info.get('spreadsheet_url', 'N/A')}")
                        
                        run_stats["google_sheets"] = sheets_info
                    except Exception as e:
                        logger.error(f"Error recording Google Sheets information: {str(e)}", exc_info=True)
                        run_stats["errors"].append({
                            "component": "google_sheets_info",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        })
                        run_stats["google_sheets"] = {"success": False, "error": str(e)}
            except Exception as e:
                logger.error(f"Error processing data: {str(e)}", exc_info=True)
                run_stats["errors"].append({
                    "component": "data_processing",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                run_stats["leads_after_processing"] = 0  # Ensure this value exists for summary
        else:
            logger.warning("No results found from any scraper. Nothing to process.")
            run_stats["leads_after_processing"] = 0
            
        # Generate run summary
        run_stats["end_time"] = datetime.now()
        run_stats["duration_seconds"] = (run_stats["end_time"] - run_stats["start_time"]).total_seconds()
        
        logger.info("Generating run summary...")
        summary = generate_run_summary(run_stats)
        
        # Save the summary to a file
        summary_file = os.path.join(results_dir, f"run_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, default=str, indent=2)
        
        logger.info(f"Run summary saved to {summary_file}")
        
        if run_stats["errors"]:
            logger.warning(f"LeadScraper LATAM completed with {len(run_stats['errors'])} errors.")
            for error in run_stats["errors"]:
                logger.warning(f"- {error['component']}: {error['error']}")
        else:
            logger.info("LeadScraper LATAM completed successfully with no errors.")
        
        print("\n" + "-"*50)
        print_summary(summary)
        print("-"*50 + "\n")
        
        # Return appropriate exit code based on errors
        return 1 if run_stats["errors"] else 0
    except Exception as e:
        logger.error(f"Unexpected error in main(): {str(e)}", exc_info=True)
        return 1

@retry_manager.retry()
def run_google_maps_scraper(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Initialize and run Google Maps scraper.
    
    Args:
        config: Configuration for Google Maps scraper
        
    Returns:
        List of dictionaries with results
    """
    results = []
    search_queries = config.get("search_queries", [])
    
    # If no specific queries provided, use some defaults for LATAM
    if not search_queries:
        search_queries = [
            {"query": "restaurantes", "location": "Ciudad de México, México"},
            {"query": "hoteles", "location": "Buenos Aires, Argentina"},
            {"query": "cafeterías", "location": "Santiago, Chile"}
        ]
    
    # Initialize the scraper
    scraper = GoogleMapsScraper(
        headless=config.get("headless", True),
        max_results=config.get("max_results", 100),
        request_delay=config.get("request_delay", 2.0)
    )
    
    try:
        for search_item in search_queries: # Renamed 'search' to 'search_item' to avoid conflict
            query = search_item.get("query", "")
            location = search_item.get("location", "")
            
            if not query or not location:
                logger.warning(f"Skipping invalid search: {search_item}")
                continue
            
            logger.info(f"Searching Google Maps for '{query}' in '{location}'")
            # Corrected method name from scraper.search to scraper.scrape
            search_results = scraper.scrape(
                query=query, 
                location=location
            )
            
            if search_results:
                # Add source and query info to results
                for result in search_results:
                    result["source"] = "google_maps"
                    result["query"] = query
                    result["location"] = location
                
                results.extend(search_results)
                logger.info(f"Found {len(search_results)} results for '{query}' in '{location}'")
            else:
                logger.warning(f"No results found for '{query}' in '{location}'")
    finally:
        # Ensure the scraper is properly closed
        scraper.close()
    
    return results

@retry_manager.retry()
def run_instagram_scraper(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Initialize and run Instagram scraper.
    
    Args:
        config: Configuration for Instagram scraper
        
    Returns:
        List of dictionaries with results
    """
    results = []
    
    # Initialize the scraper
    scraper = InstagramScraper(
        username=config.get("username", ""),
        password=config.get("password", ""),
        max_results=config.get("max_results", 100)  # Ensures "max_results" is fetched from config
    )
    
    try:
        # Scrape by hashtags
        hashtags = config.get("hashtags", [])
        if hashtags:
            for hashtag in hashtags:
                hashtag = hashtag.strip().lstrip('#')
                if not hashtag:
                    continue
                
                logger.info(f"Searching Instagram for hashtag '#{hashtag}'")
                hashtag_results = scraper.search_by_hashtag(hashtag)
                
                if hashtag_results:
                    # Add source and query info to results
                    for result in hashtag_results:
                        result["source"] = "instagram"
                        result["query_type"] = "hashtag"
                        result["query"] = hashtag
                    
                    results.extend(hashtag_results)
                    logger.info(f"Found {len(hashtag_results)} profiles for hashtag '#{hashtag}'")
                else:
                    logger.warning(f"No results found for hashtag '#{hashtag}'")
        
        # Scrape by locations
        locations = config.get("locations", [])
        if locations:
            for location_id in locations:
                if not location_id:
                    continue
                
                logger.info(f"Searching Instagram for location ID '{location_id}'")
                location_results = scraper.search_by_location(location_id)
                
                if location_results:
                    # Add source and query info to results
                    for result in location_results:
                        result["source"] = "instagram"
                        result["query_type"] = "location"
                        result["query"] = location_id
                    
                    results.extend(location_results)
                    logger.info(f"Found {len(location_results)} profiles for location ID '{location_id}'")
                else:
                    logger.warning(f"No results found for location ID '{location_id}'")
    finally:
        # No close() method for InstagramScraper; nothing to do here
        pass
    
    return results

@retry_manager.retry()
def run_directory_scrapers(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Initialize and run directory scrapers.
    
    Args:
        config: Configuration for directory scrapers
        
    Returns:
        List of dictionaries with results
    """
    results = []
    enabled_directories = config.get("enabled_directories", [])
    search_queries = config.get("search_queries", [])
    max_results = config.get("max_results", 50)
    
    # If no specific queries provided, use some defaults for LATAM
    if not search_queries:
        search_queries = [
            {"query": "restaurantes", "location": "Ciudad de México"},
            {"query": "hoteles", "location": "Buenos Aires"},
            {"query": "cafeterías", "location": "Santiago"}
        ]
    
    # Process each enabled directory
    for directory in enabled_directories:
        dir_results = []
        
        try:
            if directory.lower() == "paginas_amarillas":
                logger.info("Initializing Páginas Amarillas scraper...")
                scraper = PaginasAmarillasScraper(max_results=max_results)
            elif directory.lower() == "guialocal":
                logger.info("Initializing GuiaLocal scraper...")
                scraper = GuiaLocalScraper(max_results=max_results)
            elif directory.lower() == "cylex":
                logger.info("Initializing Cylex scraper...")
                scraper = CylexScraper(max_results=max_results)
            else:
                logger.warning(f"Unknown directory: {directory}. Skipping.")
                continue
            
            # Run searches for this directory
            for search in search_queries:
                query = search.get("query", "")
                location = search.get("location", "")
                
                if not query or not location:
                    logger.warning(f"Skipping invalid search: {search}")
                    continue
                
                logger.info(f"Searching {directory} for '{query}' in '{location}'")
                search_results = scraper.scrape(query=query, location=location)
                
                if search_results:
                    # Add source and query info to results
                    for result in search_results:
                        result["source"] = directory.lower()
                        result["query"] = query
                        result["location"] = location
                    
                    dir_results.extend(search_results)
                    logger.info(f"Found {len(search_results)} results in {directory} for '{query}' in '{location}'")
                else:
                    logger.warning(f"No results found in {directory} for '{query}' in '{location}'")
            
            # Close the scraper
            scraper.close()
            
            # Add directory results to overall results
            results.extend(dir_results)
            logger.info(f"Completed {directory} scraping with {len(dir_results)} total results")
            
        except Exception as e:
            logger.error(f"Error running {directory} scraper: {str(e)}", exc_info=True)
    
    return results

# Esta función ha sido reemplazada por process_and_upload_data
# que implementa el flujo completo de ValidationProcessor

def upload_to_google_sheets(data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Upload processed data to Google Sheets.
    
    Args:
        data: DataFrame with processed data
        config: Configuration for Google Sheets integration
        
    Returns:
        Dictionary with upload results (can include an 'error' key if failed)
    """
    # Initialize Google Sheets integration
    gs_integration = GoogleSheetsIntegration(
        credentials_file=config.get("service_account_file", "")
    )
    
    # Get spreadsheet
    spreadsheet_id = config.get("spreadsheet_id", "")
    sheet_title = config.get("sheet_title", f"LeadScraper Results {datetime.now().strftime('%Y-%m-%d')}")
    
    if not spreadsheet_id:
        # Create new spreadsheet if ID not provided
        logger.info("Creating new spreadsheet...")
        try:
            spreadsheet_id = gs_integration.create_spreadsheet(sheet_title) # Returns ID string
            logger.info(f"Created new spreadsheet with ID: {spreadsheet_id}")
            # After creating, the gs_integration object has self.spreadsheet set.
        except Exception as e:
            logger.error(f"Failed to create new spreadsheet: {str(e)}", exc_info=True)
            return {
                "spreadsheet_id": None,
                "spreadsheet_url": None,
                "sheet_title": sheet_title,
                "rows_uploaded": 0,
                "error": f"Failed to create spreadsheet: {str(e)}"
            }
    else:
        # Use existing spreadsheet
        logger.info(f"Using existing spreadsheet with ID: {spreadsheet_id}")
        try:
            opened_successfully = gs_integration.open_spreadsheet_by_id(spreadsheet_id)
            if not opened_successfully:
                logger.error(f"Failed to open spreadsheet with ID: {spreadsheet_id}. It might not exist or there could be a permission issue.")
                return {
                    "spreadsheet_id": spreadsheet_id,
                    "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                    "sheet_title": sheet_title,
                    "rows_uploaded": 0,
                    "error": f"Failed to open spreadsheet {spreadsheet_id}"
                }
            # gs_integration.spreadsheet is now set if opened_successfully was True
        except Exception as e:
            logger.error(f"Error opening spreadsheet {spreadsheet_id}: {str(e)}", exc_info=True)
            return {
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                "sheet_title": sheet_title,
                "rows_uploaded": 0,
                "error": f"Error opening spreadsheet {spreadsheet_id}: {str(e)}"
            }
            
    # Prepare data for upload
    logger.info("Converting data for Google Sheets format...")
    sheet_data = gs_integration.convert_dataframe_to_sheets_format(data, include_headers=True)
    
    # Upload data to sheet
    logger.info(f"Uploading {len(data)} rows to Google Sheets...")
    if config.get("append_mode", True):
        # Append data to existing sheet or create new one
        worksheet = gs_integration.get_or_create_worksheet(spreadsheet_id, sheet_title)
        result = gs_integration.batch_append_values(
            spreadsheet_id=spreadsheet_id,
            range_name=sheet_title,
            values=sheet_data,
            batch_size=config.get("batch_size", 1000)
        )
    else:
        # Overwrite existing sheet
        worksheet = gs_integration.get_or_create_worksheet(spreadsheet_id, sheet_title)
        result = gs_integration.batch_update_values(
            spreadsheet_id=spreadsheet_id,
            range_name=sheet_title,
            values=sheet_data,
            batch_size=config.get("batch_size", 1000)
        )
    
    # Format sheet
    logger.info("Formatting spreadsheet...")
    gs_integration.format_sheet_header(
        spreadsheet_id=spreadsheet_id,
        sheet_id=worksheet.id,
        freeze_rows=1,
        bold_header=True,
        resize_columns=True
    )
    
    # Get spreadsheet URL
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    
    return {
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_url": spreadsheet_url,
        "sheet_title": sheet_title,
        "rows_uploaded": len(data)
    }

def save_results(results: List[Dict[str, Any]], filepath: str) -> None:
    """
    Save results to a JSON file.
    
    Args:
        results: List of dictionaries with results
        filepath: Path to save the file
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"Results saved to {filepath}")

def generate_run_summary(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a summary report for the run.
    
    Args:
        stats: Dictionary with run statistics
        
    Returns:
        Dictionary with formatted summary
    """
    summary = {
        "run_date": stats["start_time"].strftime('%Y-%m-%d %H:%M:%S'),
        "duration": f"{stats['duration_seconds']:.2f} seconds",
        "success": len(stats["errors"]) == 0,
        "error_count": len(stats["errors"]),
        "scrapers_stats": {
            "total_scrapers_run": stats["scrapers_run"],
            "total_leads_found": stats["total_leads_found"],
            "individual_scrapers": stats.get("scraper_stats", {})
        },
        "processing_stats": {
            "leads_after_processing": stats["leads_after_processing"],
            "reduction_percentage": 0 if stats["total_leads_found"] == 0 else 
                                   (1 - stats["leads_after_processing"] / stats["total_leads_found"]) * 100
        },
        "google_sheets": stats.get("google_sheets", {"success": False, "message": "Upload not performed"})
    }
    
    if stats["errors"]:
        summary["errors"] = [
            {"component": e["component"], "message": e["error"]} 
            for e in stats["errors"]
        ]
    
    return summary

def print_summary(summary: Dict[str, Any]) -> None:
    """
    Print a summary report to the console.
    
    Args:
        summary: Dictionary with run summary
    """
    print(f"LeadScraper LATAM - Run Summary ({summary['run_date']})")
    print(f"Duration: {summary['duration']}")
    print(f"Status: {'SUCCESS' if summary['success'] else 'FAILED'}")
    print(f"Total scrapers run: {summary['scrapers_stats']['total_scrapers_run']}")
    print(f"Total leads found: {summary['scrapers_stats']['total_leads_found']}")
    print(f"Leads after processing: {summary['processing_stats']['leads_after_processing']}")
    
    if summary['processing_stats']['leads_after_processing'] > 0:
        print(f"Reduction: {summary['processing_stats']['reduction_percentage']:.1f}%")
    
    # Print individual scraper stats
    print("\nScraper Statistics:")
    for scraper, stats in summary['scrapers_stats'].get('individual_scrapers', {}).items():
        if isinstance(stats, dict):
            status = "✓" if stats.get('success', False) else "✗"
            results = stats.get('results_count', 0) if stats.get('success', False) else 0
            print(f"  {scraper}: {status} ({results} leads)")
    
    # Print Google Sheets info
    if 'google_sheets' in summary and summary['google_sheets'].get('success', False):
        print("\nGoogle Sheets:")
        print(f"  Status: ✓")
        print(f"  Rows uploaded: {summary['google_sheets'].get('rows_uploaded', 0)}")
        print(f"  URL: {summary['google_sheets'].get('spreadsheet_url', 'N/A')}")
    
    # Print errors if any
    if not summary['success']:
        print("\nErrors:")
        for error in summary.get('errors', []):
            print(f"  {error['component']}: {error['message']}")

def process_and_upload_data(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
    """
    Process data through validation and upload it to Google Sheets.
    
    Args:
        df: DataFrame with data to process
        config: Configuration dictionary with validation and Google Sheets settings
        
    Returns:
        Tuple containing (processed DataFrame, upload results dictionary or None)
    """
    # Get processing configuration
    processing_config = config.get("processing", {})
    validation_config = processing_config.get("validation", {})
    dedup_config = processing_config.get("deduplication", {})
    google_sheets_config = config.get("google_sheets", {})
    
    logger.info(f"Starting data processing pipeline with {len(df)} records...")
    
    # Initial cleaning - remove rows with no business name
    if 'business_name' in df.columns:
        df = df[df['business_name'].notna()]
        logger.info(f"After removing records with no business name: {len(df)} records")
    
    # Deduplication functionality is now handled by ValidationProcessor
    if dedup_config.get("exact_match", True) or dedup_config.get("fuzzy_match", False):
        try:
            logger.info("Deduplication will be handled by ValidationProcessor's process method.")
            # The pandas drop_duplicates block that was here has been removed.
            # Deduplication parameters will be passed to validator.process().
            
        except Exception as e:
            logger.error(f"Error during deduplication setup (this block should ideally be empty now): {str(e)}", exc_info=True) # Modified log
            logger.warning("Continuing with original data if error occurs before ValidationProcessor")
    
    # Run validation process if configured
    if validation_config.get("enable_email_validation", True) or validation_config.get("enable_phone_validation", True):
        try:
            # Initialize validation processor
            logger.info("Initializing ValidationProcessor...")
            validator = ValidationProcessor(df) # df here is before any deduplication by ValidationProcessor
            
            # Run email validation if enabled
            if validation_config.get("enable_email_validation", True):
                logger.info("Validating email addresses...")
                df_with_emails = validator.validate_emails()
                valid_emails_count = df_with_emails['email_valid'].sum() if 'email_valid' in df_with_emails.columns else 0
                logger.info(f"Email validation complete. Valid emails: {valid_emails_count} ({ (valid_emails_count/len(df_with_emails)*100 if len(df_with_emails) > 0 else 0.0):.1f}%)")
                
                # Update validator data with email validation results
                validator.data = df_with_emails
                # df = df_with_emails # Not strictly needed here as validator.process uses validator.data
            
            # Run phone validation if enabled
            if validation_config.get("enable_phone_validation", True):
                logger.info("Validating phone numbers...")
                df_with_phones = validator.validate_phone_numbers() # Operates on validator.data
                valid_phones_count = df_with_phones['phone_valid'].sum() if 'phone_valid' in df_with_phones.columns else 0
                logger.info(f"Phone validation complete. Valid phones: {valid_phones_count} ({ (valid_phones_count/len(df_with_phones)*100 if len(df_with_phones) > 0 else 0.0):.1f}%)")
                
                # Update validator data with phone validation results
                validator.data = df_with_phones
                # df = df_with_phones # Not strictly needed here
            
            # Process the dataset (performs validation, scoring, and formatting, including deduplication)
            logger.info("Processing full dataset with ValidationProcessor...")
            
            exact_dedup_fields = None
            if dedup_config.get("exact_match", True):
                exact_dedup_fields = dedup_config.get("match_fields", [])
                if not exact_dedup_fields: # Ensure it's None if empty list
                    exact_dedup_fields = None 
            
            fuzzy_dedup_fields = None
            if dedup_config.get("fuzzy_match", False): 
                fuzzy_dedup_fields = dedup_config.get("match_fields", [])
                if not fuzzy_dedup_fields:
                    fuzzy_dedup_fields = None

            fuzzy_threshold_val = dedup_config.get("fuzzy_threshold", 80)

            processed_df = validator.process(
                deduplicate_exact_fields=exact_dedup_fields,
                deduplicate_fuzzy_fields=fuzzy_dedup_fields,
                fuzzy_threshold=fuzzy_threshold_val
            )
            df = processed_df # Update df with the fully processed data from ValidationProcessor
            
            # Run data quality monitoring if available
            logger.info("Running data quality assessment...")
            try:
                # Determine source name from validation_config or default to a fixed value
                source_name = validation_config.get("source_name", "combined_sources")
                
                # Perform data quality assessment using the validator
                quality_results = validator.assess_data_quality(source_name)
                
                # Log quality results
                quality_score = quality_results.get('overall_score', 0)
                records_with_issues = len(quality_results.get('issues', []))
                
                logger.info(f"Data quality assessment: Score={quality_score:.1f}/100, " +
                            f"Records with issues: {records_with_issues}/{len(df)} " +
                            f"({records_with_issues/len(df)*100 if len(df) > 0 else 0.0:.1f}%)")
                
                # Export quality report if enabled
                if validation_config.get("export_quality_report", False):
                    logger.info("Exporting data quality report...")
                    
                    # Create a timestamp for the report filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    report_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
                    os.makedirs(report_dir, exist_ok=True)
                    
                    # Save the report to a JSON file
                    report_path = os.path.join(report_dir, f"quality_report_{timestamp}.json")
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(quality_results, f, default=str, indent=2)
                    
                    logger.info(f"Data quality report saved to {report_path}")
            except Exception as e:
                logger.error(f"Error during data quality assessment: {str(e)}", exc_info=True)
                logger.warning("Continuing processing without data quality assessment")
                
            # Export quality reports if available and configured
            try:
                if 'data_quality_monitor' in globals() and os.environ.get("EXPORT_QUALITY_REPORTS", "True").lower() == "true":
                    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
                    os.makedirs(reports_dir, exist_ok=True)
                    
                    report_path = data_quality_monitor.export_report(
                        directory=reports_dir,
                        source_name=source_name
                    )
                    logger.info(f"Data quality report exported to: {report_path}")
                
                # Flag suspicious records if any
                if 'quality_results' in locals() and quality_results:
                    suspicious_records = quality_results.get('suspicious_records', [])
                    if suspicious_records:
                        logger.warning(f"Found {len(suspicious_records)} suspicious records that may require review")
                        
                        # Optionally add a flag to suspicious records
                        if 'suspicious_records' in quality_results and len(quality_results['suspicious_records']) > 0:
                            suspicious_indices = [df.index.get_loc(r.get('id')) if 'id' in r else i 
                                                for i, r in enumerate(quality_results['suspicious_records'])]
                            
                            # Mark suspicious records in the dataframe if possible
                            if suspicious_indices and not df.empty:
                                if 'suspicious' not in df.columns:
                                    df['suspicious'] = False
                                df.loc[suspicious_indices, 'suspicious'] = True
            except Exception as e:
                logger.error(f"Error in data quality reporting: {str(e)}", exc_info=True)
                # Continue processing if data quality reporting fails
            
            # Analyze validation results
            if 'is_valid' in processed_df.columns:
                valid_records = processed_df['is_valid'].sum()
                logger.info(f"Validation results:")
                logger.info(f"- Valid records: {valid_records} ({valid_records/len(processed_df)*100:.1f}%)")
                logger.info(f"- Invalid records: {len(processed_df) - valid_records}")
            
            # Calculate average quality score
            if 'validation_score' in processed_df.columns:
                avg_quality = processed_df['validation_score'].mean()
                logger.info(f"Average quality score: {avg_quality:.1f}%")
            
            df = processed_df
            
            # Apply minimum data quality threshold if specified
            min_quality = validation_config.get("min_data_quality", 0.0)
            if min_quality > 0:
                # Convert from 0-1 scale to 0-100 scale for filter_by_quality_score
                min_score = min_quality * 100
                logger.info(f"Filtering by quality score (min score: {min_score}%)...")
                filtered_df = validator.filter_by_quality_score(min_score=min_score)
                logger.info(f"After quality filtering: {len(filtered_df)} records")
                df = filtered_df
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}", exc_info=True)
            logger.warning("Continuing with unvalidated data")
    
    # Add timestamp column
    df['scrape_date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Upload to Google Sheets if enabled
    if google_sheets_config.get("enabled", False) and not df.empty:
        try:
            logger.info("Uploading processed data to Google Sheets...")
            upload_results = upload_to_google_sheets(df, google_sheets_config)
            
            if upload_results and upload_results.get("error"):
                logger.error(f"Google Sheets upload failed: {upload_results.get('error')}")
                # Fall through to return df, upload_results so error is propagated
            else:
                logger.info(f"Upload complete: {upload_results}")
            return df, upload_results
        except Exception as e:
            logger.error(f"Error uploading to Google Sheets: {str(e)}", exc_info=True)
            logger.warning("Continuing without uploading to Google Sheets")
    
    return df, None

if __name__ == "__main__":
    exit_code = main()
    print(f"ScraperMVP completed with exit code: {exit_code}")
    sys.exit(exit_code)
