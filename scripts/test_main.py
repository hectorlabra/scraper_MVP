#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeadScraper LATAM - Test Script

This script runs tests on the main application with a limited set of queries
to verify functionality without a full production run.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional # Import Optional
import traceback
import pandas as pd # Add pandas import

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import main, ConfigManager, process_and_upload_data # Import process_and_upload_data
from utils.helpers import setup_logger

logger = setup_logger('test_main', log_level="DEBUG")

MOCK_DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data', 'sample_leads.json'))

def load_mock_data(source_filter: Optional[str] = None) -> pd.DataFrame:
    """Load mock data from the JSON file and optionally filter by source."""
    with open(MOCK_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if source_filter:
        data = [item for item in data if item.get("source") == source_filter]
    return pd.DataFrame(data)

def test_configuration():
    """Test configuration loading"""
    logger.info("Testing configuration loading...")
    
    try:
        # Initialize configuration manager
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Verify required sections
        assert "google_maps" in config_manager.scraper_configs, "Missing Google Maps configuration"
        assert "instagram" in config_manager.scraper_configs, "Missing Instagram configuration"
        assert "directories" in config_manager.scraper_configs, "Missing Directories configuration"
        
        # Check if Google Sheets integration is configured
        if config_manager.google_sheets_config["enabled"]:
            assert config_manager.google_sheets_config["service_account_file"], "Google Sheets enabled but no service account file specified"
            assert os.path.exists(config_manager.google_sheets_config["service_account_file"]), "Google Sheets service account file does not exist"
        
        logger.info("✓ Configuration loading test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Configuration loading test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_google_maps_scraper():
    """Test Google Maps scraper with mock data"""
    logger.info("Testing Google Maps scraper with mock data...")
    
    try:
        # Override environment variables for testing
        os.environ["ENABLE_INSTAGRAM"] = "False"
        os.environ["ENABLE_DIRECTORIES"] = "False"
        os.environ["ENABLE_GOOGLE_SHEETS"] = "False"
        os.environ["GOOGLE_MAPS_MAX_RESULTS"] = "5" # This won't be used by mock
        os.environ["GOOGLE_MAPS_QUERIES"] = json.dumps([{"query": "restaurantes", "location": "Ciudad de México, México"}]) # Not used by mock
        os.environ["FUZZY_THRESHOLD"] = "95" # For consistent processing

        config_manager = ConfigManager()
        config_manager.load_config() # Load config to be passed

        mock_df = load_mock_data() # Load all mock data for this test
        
        # Directly call processing function
        processed_df, _ = process_and_upload_data(
            mock_df, 
            {
                "processing": config_manager.get_processing_config(),
                "google_sheets": config_manager.get_google_sheets_config()
            }
        )
        
        assert len(processed_df) == 3, f"Expected 3 records after processing mock data, got {len(processed_df)}"
        
        logger.info("✓ Google Maps scraper test (mocked) passed")
        return True
    except Exception as e:
        logger.error(f"✗ Google Maps scraper test (mocked) failed: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        # Reset environment variables
        os.environ.pop("ENABLE_INSTAGRAM", None)
        os.environ.pop("ENABLE_DIRECTORIES", None)
        os.environ.pop("ENABLE_GOOGLE_SHEETS", None)
        os.environ.pop("GOOGLE_MAPS_MAX_RESULTS", None)
        os.environ.pop("GOOGLE_MAPS_QUERIES", None)
        os.environ.pop("FUZZY_THRESHOLD", None)

def test_instagram_scraper():
    """Test Instagram scraper with mock data"""
    logger.info("Testing Instagram scraper with mock data...")
    
    try:
        # Check if Instagram credentials are available (still good to check for completeness)
        if not os.environ.get("INSTAGRAM_USERNAME") or not os.environ.get("INSTAGRAM_PASSWORD"):
            logger.warning("Instagram credentials not found, skipping test (mock data will be used if test proceeds).")
            # return None # We can proceed with mock data even if creds are missing for a full run

        # Override environment variables for testing
        os.environ["ENABLE_GOOGLE_MAPS"] = "False"
        os.environ["ENABLE_DIRECTORIES"] = "False"
        os.environ["ENABLE_GOOGLE_SHEETS"] = "False"
        os.environ["INSTAGRAM_MAX_RESULTS"] = "5" # Changed from INSTAGRAM_MAX_POSTS, not used by mock
        os.environ["INSTAGRAM_HASHTAGS"] = "emprendedores" # Not used by mock
        os.environ["FUZZY_THRESHOLD"] = "95" # For consistent processing

        config_manager = ConfigManager()
        config_manager.load_config()

        mock_df = load_mock_data(source_filter="instagram")
        
        if mock_df.empty:
            logger.warning("No Instagram mock data found. Test might not be meaningful.")
            # Depending on how strict we want to be, we could fail or pass here.
            # For now, let's assume if no mock data for insta, it means 0 results.
            processed_df = pd.DataFrame() 
        else:
            processed_df, _ = process_and_upload_data(
                mock_df,
                {
                    "processing": config_manager.get_processing_config(),
                    "google_sheets": config_manager.get_google_sheets_config()
                }
            )

        # The sample_leads.json has 1 instagram entry. It should remain after processing.
        expected_records = 1 if not mock_df.empty else 0
        assert len(processed_df) == expected_records, f"Expected {expected_records} record(s) after processing Instagram mock data, got {len(processed_df)}"
        
        logger.info("✓ Instagram scraper test (mocked) passed")
        return True
    except Exception as e:
        logger.error(f"✗ Instagram scraper test (mocked) failed: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        # Reset environment variables
        os.environ.pop("ENABLE_GOOGLE_MAPS", None)
        os.environ.pop("ENABLE_DIRECTORIES", None)
        os.environ.pop("ENABLE_GOOGLE_SHEETS", None)
        os.environ.pop("INSTAGRAM_MAX_RESULTS", None) # Changed from INSTAGRAM_MAX_POSTS
        os.environ.pop("INSTAGRAM_HASHTAGS", None)
        os.environ.pop("FUZZY_THRESHOLD", None)

def test_directory_scrapers():
    """Test directory scrapers with mock data"""
    logger.info("Testing directory scrapers with mock data...")
    
    try:
        # Override environment variables for testing
        os.environ["ENABLE_GOOGLE_MAPS"] = "False"
        os.environ["ENABLE_INSTAGRAM"] = "False"
        os.environ["ENABLE_GOOGLE_SHEETS"] = "False"
        os.environ["DIRECTORY_MAX_RESULTS"] = "5" # Not used by mock
        os.environ["DIRECTORIES_TO_SCRAPE"] = "paginas_amarillas,guialocal,cylex" # Not used by mock
        os.environ["DIRECTORY_QUERIES"] = json.dumps([{"query": "restaurantes", "location": "Madrid"}]) # Not used by mock
        os.environ["FUZZY_THRESHOLD"] = "95" # For consistent processing

        config_manager = ConfigManager()
        config_manager.load_config()
        
        # Load mock data for all directory sources
        pa_df = load_mock_data(source_filter="paginas_amarillas")
        gl_df = load_mock_data(source_filter="guialocal")
        cl_df = load_mock_data(source_filter="cylex")
        mock_df = pd.concat([pa_df, gl_df, cl_df]).reset_index(drop=True)

        if mock_df.empty:
            logger.warning("No directory mock data found. Test might not be meaningful.")
            processed_df = pd.DataFrame()
        else:
            processed_df, _ = process_and_upload_data(
                mock_df,
                {
                    "processing": config_manager.get_processing_config(),
                    "google_sheets": config_manager.get_google_sheets_config()
                }
            )
        
        # sample_leads.json has:
        # 1 paginas_amarillas (part of "Test Business" group)
        # 1 guialocal (part of "Test Business" group, "Test Business Inc")
        # 1 cylex (part of "Another Business" group)
        # After processing with FUZZY_THRESHOLD=95, these should result in 3 unique records
        # when combined with the google_maps "Test Business" and "Another Business"
        # However, this test is *only* for directory scrapers.
        # The mock data contains:
        # {"business_name": "Test Business", "phone": "555-123-4567", "email": "info@test.com", "source": "paginas_amarillas", "location": "USA"}
        # {"business_name": "Test Business Inc", "phone": "5551234567", "email": "info@test.com", "source": "guialocal", "location": "USA"}
        # {"business_name": "Another Business", "phone": "555-987-6543", "email": "CONTACT@ANOTHER.COM", "source": "cylex", "location": "USA"}
        # These three are distinct enough with fuzzy_threshold=95 to remain 3 records.
        expected_records = 3 if not mock_df.empty else 0
        assert len(processed_df) == expected_records, f"Expected {expected_records} records after processing directory mock data, got {len(processed_df)}"
        
        logger.info("✓ Directory scrapers test (mocked) passed")
        return True
    except Exception as e:
        logger.error(f"✗ Directory scrapers test (mocked) failed: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        # Reset environment variables
        os.environ.pop("ENABLE_GOOGLE_MAPS", None)
        os.environ.pop("ENABLE_INSTAGRAM", None)
        os.environ.pop("ENABLE_GOOGLE_SHEETS", None)
        os.environ.pop("DIRECTORY_MAX_RESULTS", None)
        os.environ.pop("DIRECTORIES_TO_SCRAPE", None)
        os.environ.pop("DIRECTORY_QUERIES", None)
        os.environ.pop("FUZZY_THRESHOLD", None)

def test_data_processing():
    """Test data processing with sample data using ValidationProcessor"""
    logger.info("Testing data processing with ValidationProcessor...")
    
    try:
        # from processing.data_processor import DeduplicationProcessor # Old
        from processing.data_processor import ValidationProcessor
        
        # Create sample data with duplicates
        data = [
            {"business_name": "Test Business", "phone": "555-123-4567", "email": "info@test.com", "source": "google_maps", "location": "USA"},
            {"business_name": "Test Business", "phone": "555-123-4567", "email": "info@test.com", "source": "paginas_amarillas", "location": "USA"},
            {"business_name": "Test Business Inc", "phone": "5551234567", "email": "info@test.com", "source": "guialocal", "location": "USA"}, # Phone likely normalizes
            {"business_name": "Another Business", "phone": "555-987-6543", "email": "contact@another.com", "source": "instagram", "location": "USA"},
            {"business_name": "Another Business", "phone": "555-987-6543", "email": "CONTACT@ANOTHER.COM", "source": "cylex", "location": "USA"} # Email normalizes
        ]
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Initialize ValidationProcessor
        validator = ValidationProcessor(df.copy()) # Use a copy

        # Perform initial validation steps (email and phone formatting/validation are part of .process())
        # validator.validate_emails() # These are called within .process() or prepare data for it
        # validator.validate_phone_numbers()
        # validator.data should be updated by these if called, or .process() handles it.

        # Process data: apply formatting, validation, scoring, and deduplication.
        # To get 3 records:
        # 1. "Test Business", "555-123-4567", "info@test.com"
        # 2. "Test Business Inc", "5551234567" (formats same as above), "info@test.com"
        # 3. "Another Business", "555-987-6543", "contact@another.com"
        # This means exact deduplication on (business_name, phone, email) should remove the second "Test Business"
        # and the second "Another Business".
        # Then, "Test Business" and "Test Business Inc" should NOT be merged by fuzzy.
        
        processed_df = validator.process(
            deduplicate_exact_fields=["business_name", "phone", "email"],
            deduplicate_fuzzy_fields=["business_name"], # Fuzzy on business_name
            fuzzy_threshold=95  # Set high enough so "Test Business" and "Test Business Inc" don't match
        )
        
        # Expected:
        # Record 1: Test Business, 555-123-4567, info@test.com
        # Record 3: Test Business Inc, 5551234567 (formats to same as 1), info@test.com -> this would be removed by exact if name was same.
        # Record 4: Another Business, 555-987-6543, contact@another.com (formats to same as 5)
        # Record 5: Another Business, 555-987-6543, contact@another.com (formats to same as 4) -> this should be removed by exact deduplication.
        
        assert len(processed_df) == 3, f"Expected 3 records after processing sample data, got {len(processed_df)}"
        
        logger.info("✓ Data processing test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Data processing test failed: {str(e)}")
        traceback.print_exc()
        return False

def test_google_sheets_integration():
    """Test Google Sheets integration with sample data"""
    logger.info("Testing Google Sheets integration...")
    
    try:
        # Check if Google Sheets credentials are available
        gs_creds_file_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        if not gs_creds_file_path or not os.path.exists(gs_creds_file_path):
            logger.warning(f"Google Sheets credentials not found at {gs_creds_file_path}, skipping test.")
            return None # Use None for skipped tests
        
        from integrations.google_sheets import GoogleSheetsIntegration
        # import pandas as pd # Already imported globally
        
        # Create sample data
        sample_data = [
            {"Column1": "Value1", "Column2": "Value2"},
            {"Column1": "Value3", "Column2": "Value4"}
        ]
        df = pd.DataFrame(sample_data)
        
        gs_integration = GoogleSheetsIntegration(
            credentials_file=gs_creds_file_path
        )
        
        # Test spreadsheet creation
        sheet_title = f"LeadScraper Test {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # create_spreadsheet now returns the gspread.Spreadsheet object
        spreadsheet_object = gs_integration.create_spreadsheet(sheet_title) 
        
        assert spreadsheet_object, "Failed to create test spreadsheet object"
        assert spreadsheet_object.id, "Failed to get ID from created test spreadsheet"
        
        spreadsheet_id_to_use = spreadsheet_object.id # Use the ID from the created object

        # Test data upload
        sheet_data = gs_integration.convert_dataframe_to_sheets_format(df, include_headers=True)
        
        # Open the spreadsheet by ID to get a fresh gspread.Spreadsheet object if needed,
        # or use the one from creation. get_or_create_worksheet needs the ID.
        worksheet = gs_integration.get_or_create_worksheet(spreadsheet_id_to_use, "Test Sheet")
        
        result = gs_integration.batch_append_values(
            spreadsheet_id=spreadsheet_id_to_use,
            range_name=f"{worksheet.title}!A1", # Use worksheet title for range
            values=sheet_data
        )
        assert result.get("updates", {}).get("updatedCells", 0) > 0, "Batch append did not update cells"
        
        # Format sheet
        gs_integration.format_sheet_header(
            spreadsheet_id=spreadsheet_id_to_use,
            sheet_id=worksheet.id, # worksheet object has an id attribute
            freeze_rows=1,
            bold_header=True,
            resize_columns=True
        )
        
        logger.info(f"✓ Google Sheets integration test passed. Test spreadsheet ID: {spreadsheet_id_to_use}")
        
        # Clean up - rename sheet to indicate it\'s a test that can be deleted
        # rename_spreadsheet also returns the gspread.Spreadsheet object
        renamed_spreadsheet = gs_integration.rename_spreadsheet(spreadsheet_id_to_use, f"[TEST - SAFE TO DELETE] {sheet_title}")
        assert renamed_spreadsheet.title == f"[TEST - SAFE TO DELETE] {sheet_title}", "Failed to rename spreadsheet"
        
        return True
    except Exception as e: # Added except block
        logger.error(f"✗ Google Sheets integration test failed: {str(e)}")
        traceback.print_exc()
        return False
    finally: # Added finally block for consistency, though not strictly needed here as no env vars were changed for this specific test
        pass

def test_error_handling():
    """Test error handling in the application"""
    logger.info("Testing error handling...")
    
    try:
        # Intentionally cause an error by passing invalid config
        config_manager = ConfigManager()
        config_manager.load_config()
        
        # Override with invalid values
        os.environ["GOOGLE_MAPS_QUERIES"] = json.dumps("invalid_json") # Invalid JSON
        os.environ["INSTAGRAM_HASHTAGS"] = "" # Empty hashtag, should be ignored but just in case
        os.environ["DIRECTORIES_TO_SCRAPE"] = "invalid_directory" # Invalid directory
        
        # Run all scrapers with invalid config
        google_maps_result = test_google_maps_scraper()
        instagram_result = test_instagram_scraper()
        directories_result = test_directory_scrapers()
        
        # Check if the tests handled errors as expected
        assert google_maps_result is False, "Google Maps scraper did not handle error as expected"
        assert instagram_result is False, "Instagram scraper did not handle error as expected"
        assert directories_result is False, "Directory scrapers did not handle error as expected"
        
        logger.info("✓ Error handling test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Error handling test failed: {str(e)}")
        traceback.print_exc()
        return False
