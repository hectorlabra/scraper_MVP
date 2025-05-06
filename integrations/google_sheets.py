#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets Integration Module

This module provides functionality to authenticate, connect to, and
interact with Google Sheets API, including managing permissions and sharing.
"""

import logging
import os
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
import time
import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)


class PermissionType(Enum):
    """Enum for Google Sheets permission types."""
    READER = "reader"
    WRITER = "writer"
    OWNER = "owner"


class GoogleSheetsIntegration:
    """
    Class for integrating with Google Sheets.
    
    This class handles authentication with Google Sheets API using OAuth2 and service
    account credentials, creates or accesses spreadsheets, and manages permissions.
    """
    
    # Google API scopes needed for spreadsheet operations
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Retry parameters for API rate limiting
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    # Cache settings
    CACHE_TTL = 300  # seconds (5 minutes)
    MAX_CACHE_ITEMS = 100
    
    def __init__(self, 
                 credentials_file: Optional[str] = None,
                 credentials_dict: Optional[Dict] = None,
                 credentials_env_var: str = 'GOOGLE_SERVICE_ACCOUNT_FILE',
                 credentials_json_env_var: str = 'GOOGLE_SERVICE_ACCOUNT_JSON',
                 spreadsheet_id: Optional[str] = None,
                 spreadsheet_id_env_var: str = 'GOOGLE_SHEETS_SPREADSHEET_ID',
                 enable_caching: bool = True):
        """
        Initialize the Google Sheets integration.
        
        Args:
            credentials_file: Path to the Google service account credentials file
            credentials_dict: Dictionary containing service account credentials
            credentials_env_var: Environment variable name for credentials file path
            credentials_json_env_var: Environment variable name for credentials JSON string
            spreadsheet_id: ID of the Google spreadsheet to use
            spreadsheet_id_env_var: Environment variable name for spreadsheet ID
            enable_caching: Whether to enable caching for API calls (reduces API usage)
        """
        self.credentials_file = credentials_file
        self.credentials_dict = credentials_dict
        self.credentials_env_var = credentials_env_var
        self.credentials_json_env_var = credentials_json_env_var
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet_id_env_var = spreadsheet_id_env_var
        self.enable_caching = enable_caching
        
        self.client = None
        self.spreadsheet = None
        self.credentials = None
        self.authenticated = False
        
        # Cache for worksheet data
        self._worksheet_cache = {}
        self._permissions_cache = {}
        self._last_sync_timestamp = None
        
        # Try to load credentials and spreadsheet ID if not explicitly provided
        if not self.credentials_file and not self.credentials_dict:
            self._load_credentials_from_environment()
        
        if not self.spreadsheet_id:
            self.spreadsheet_id = os.getenv(self.spreadsheet_id_env_var)
            
        if not self.credentials_file and not self.credentials_dict:
            logger.warning("No credentials provided. Use set_credentials() to set them later.")
        
        if not self.spreadsheet_id:
            logger.warning("No spreadsheet ID provided. Use set_spreadsheet_id() to set it later.")
    
    def _load_credentials_from_environment(self) -> None:
        """
        Load credentials from environment variables.
        
        This method tries different approaches in the following order:
        1. Load credentials file path from environment variable
        2. Load credentials JSON directly from environment variable
        """
        # Try to load credentials file path from environment variable
        creds_file = os.getenv(self.credentials_env_var)
        if creds_file and os.path.exists(creds_file):
            self.credentials_file = creds_file
            logger.debug(f"Loaded credentials file path from {self.credentials_env_var}")
            return
            
        # Try to load credentials JSON from environment variable
        creds_json = os.getenv(self.credentials_json_env_var)
        if creds_json:
            try:
                self.credentials_dict = json.loads(creds_json)
                logger.debug(f"Loaded credentials JSON from {self.credentials_json_env_var}")
                return
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse credentials JSON from {self.credentials_json_env_var}")
                
        logger.debug("No credentials found in environment variables")
    
    def set_credentials(self, 
                       credentials_file: Optional[str] = None,
                       credentials_dict: Optional[Dict] = None) -> None:
        """
        Set the credentials for Google Sheets authentication.
        
        Args:
            credentials_file: Path to the Google service account credentials file
            credentials_dict: Dictionary containing service account credentials
            
        Raises:
            ValueError: If neither credentials_file nor credentials_dict is provided
        """
        if not credentials_file and not credentials_dict:
            raise ValueError("Either credentials_file or credentials_dict must be provided")
            
        self.credentials_file = credentials_file
        self.credentials_dict = credentials_dict
        self.authenticated = False  # Reset authentication status
    
    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        """
        Set the spreadsheet ID.
        
        Args:
            spreadsheet_id: ID of the Google spreadsheet to use
        """
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet = None  # Reset spreadsheet object
    
    def _create_credentials(self) -> Credentials:
        """
        Create Google OAuth2 credentials from provided sources.
        
        Returns:
            Credentials object
            
        Raises:
            FileNotFoundError: If credentials file does not exist
            ValueError: If no credentials source is available
            GoogleAuthError: If credentials are invalid
        """
        try:
            if self.credentials_file:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                    
                return Credentials.from_service_account_file(
                    self.credentials_file, scopes=self.SCOPES
                )
            elif self.credentials_dict:
                return Credentials.from_service_account_info(
                    self.credentials_dict, scopes=self.SCOPES
                )
            else:
                raise ValueError("No credentials source available")
        except GoogleAuthError as e:
            logger.error(f"Error creating credentials: {str(e)}")
            raise
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API.
        
        Returns:
            Boolean indicating if authentication was successful
            
        Raises:
            ValueError: If spreadsheet ID is not set
            Various exceptions from gspread or Google Auth libraries
        """
        if self.authenticated and self.client:
            logger.debug("Already authenticated")
            return True
            
        try:
            # Create credentials
            self.credentials = self._create_credentials()
            
            # Authorize with gspread
            self.client = gspread.authorize(self.credentials)
            
            # Test authentication by trying to list all spreadsheets
            try:
                # Just try to list spreadsheets instead of opening a specific one
                self.client.list_spreadsheet_files()
            except gspread.exceptions.APIError as e:
                error_message = str(e)
                # Check if it's an "API not enabled" error
                if (
                    "API has not been used" in error_message 
                    or "it is disabled" in error_message
                    or "Access Not Configured" in error_message
                ):
                    logger.error(
                        f"Error de API: {error_message}. "
                        "Es necesario habilitar las APIs en la consola de Google Cloud."
                    )
                    raise RuntimeError(
                        f"Google Sheets API no está habilitada. Error original: {error_message}"
                    ) from e
                # Other API error
                raise
                
            # If spreadsheet_id is provided, try to open it
            if self.spreadsheet_id:
                try:
                    self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
                except Exception as e:
                    logger.warning(f"Could not open spreadsheet with ID {self.spreadsheet_id}: {str(e)}")
                    # Don't raise, just log a warning
                    
            self.authenticated = True
            logger.info("Successfully authenticated with Google Sheets API")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Authentication failed - Credentials file not found: {str(e)}")
            self.authenticated = False
            raise
        except ValueError as e:
            logger.error(f"Authentication failed - Invalid parameters: {str(e)}")
            self.authenticated = False
            raise
        except GoogleAuthError as e:
            logger.error(f"Authentication failed - Google auth error: {str(e)}")
            self.authenticated = False
            raise
        except gspread.exceptions.GSpreadException as e:
            logger.error(f"Authentication failed - GSpread error: {str(e)}")
            self.authenticated = False
            raise
        except Exception as e:
            logger.error(f"Authentication failed - Unexpected error: {str(e)}")
            self.authenticated = False
            raise
    
    def is_authenticated(self) -> bool:
        """
        Check if client is authenticated.
        
        Returns:
            Boolean indicating if client is authenticated
        """
        return self.authenticated and self.client is not None
    
    
    def _ensure_authenticated(self) -> None:
        """
        Ensure that the client is authenticated.
        
        Raises:
            RuntimeError: If authentication fails
        """
        if not self.is_authenticated():
            success = self.authenticate()
            if not success:
                raise RuntimeError("Failed to authenticate with Google Sheets API")
    
    def create_spreadsheet(self, title: str) -> str:
        """
        Create a new Google Sheets spreadsheet.
        
        Args:
            title: Title of the spreadsheet to create
            
        Returns:
            ID of the newly created spreadsheet
            
        Raises:
            RuntimeError: If not authenticated or operation fails
        """
        self._ensure_authenticated()
        
        try:
            for attempt in range(self.MAX_RETRIES):
                try:
                    spreadsheet = self.client.create(title)
                    self.spreadsheet = spreadsheet
                    self.spreadsheet_id = spreadsheet.id
                    logger.info(f"Created new spreadsheet: {title} (ID: {spreadsheet.id})")
                    return spreadsheet.id
                except gspread.exceptions.APIError as e:
                    if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                        # Rate limiting - wait and retry
                        time.sleep(self.RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                    else:
                        raise
        except Exception as e:
            logger.error(f"Failed to create spreadsheet: {str(e)}")
            raise
    
    def open_spreadsheet_by_id(self, spreadsheet_id: str) -> bool:
        """
        Open a spreadsheet by its ID.
        
        Args:
            spreadsheet_id: ID of the spreadsheet to open
            
        Returns:
            Boolean indicating if the operation was successful
            
        Raises:
            ValueError: If spreadsheet ID is invalid
            gspread.exceptions.SpreadsheetNotFound: If spreadsheet doesn't exist
        """
        self._ensure_authenticated()
        
        try:
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            self.spreadsheet_id = spreadsheet_id
            logger.info(f"Opened spreadsheet with ID: {spreadsheet_id}")
            return True
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet not found: {spreadsheet_id}")
            raise
        except Exception as e:
            logger.error(f"Error opening spreadsheet: {str(e)}")
            raise
    
    def open_spreadsheet_by_url(self, url: str) -> bool:
        """
        Open a spreadsheet by its URL.
        
        Args:
            url: URL of the spreadsheet to open
            
        Returns:
            Boolean indicating if the operation was successful
            
        Raises:
            ValueError: If URL is invalid
            gspread.exceptions.SpreadsheetNotFound: If spreadsheet doesn't exist
        """
        self._ensure_authenticated()
        
        try:
            self.spreadsheet = self.client.open_by_url(url)
            self.spreadsheet_id = self.spreadsheet.id
            logger.info(f"Opened spreadsheet with URL: {url}")
            return True
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Spreadsheet not found at URL: {url}")
            raise
        except Exception as e:
            logger.error(f"Error opening spreadsheet by URL: {str(e)}")
            raise
    
    def get_worksheet(self, 
                      worksheet_name: str, 
                      create_if_missing: bool = True) -> gspread.Worksheet:
        """
        Get a worksheet by name, optionally creating it if it doesn't exist.
        
        Args:
            worksheet_name: Name of the worksheet to get
            create_if_missing: Whether to create the worksheet if it doesn't exist
            
        Returns:
            Worksheet object
            
        Raises:
            RuntimeError: If not authenticated
            gspread.exceptions.WorksheetNotFound: If worksheet doesn't exist and create_if_missing is False
        """
        self._ensure_authenticated()
        
        if not self.spreadsheet:
            if not self.spreadsheet_id:
                raise ValueError("No spreadsheet selected. Call open_spreadsheet_by_id() first")
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
        
        # Check the cache first if caching is enabled
        if self.enable_caching and worksheet_name in self._worksheet_cache:
            cache_time, worksheet = self._worksheet_cache[worksheet_name]
            if (datetime.datetime.now() - cache_time).total_seconds() < self.CACHE_TTL:
                logger.debug(f"Using cached worksheet: {worksheet_name}")
                return worksheet
        
        # Not in cache or cache expired, try to get from API
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            # Update cache if caching is enabled
            if self.enable_caching:
                self._worksheet_cache[worksheet_name] = (datetime.datetime.now(), worksheet)
                # Trim cache if needed
                if len(self._worksheet_cache) > self.MAX_CACHE_ITEMS:
                    # Remove oldest item
                    oldest_key = min(self._worksheet_cache.keys(), 
                                    key=lambda k: self._worksheet_cache[k][0])
                    del self._worksheet_cache[oldest_key]
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            if create_if_missing:
                logger.info(f"Creating new worksheet: {worksheet_name}")
                worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name, rows=1000, cols=26
                )
                if self.enable_caching:
                    self._worksheet_cache[worksheet_name] = (datetime.datetime.now(), worksheet)
                return worksheet
            else:
                logger.error(f"Worksheet not found: {worksheet_name}")
                raise
                
    def clear_cache(self) -> None:
        """
        Clear all cached data.
        
        This can be useful when you know the data has changed on the server
        and want to force a refresh.
        """
        logger.debug("Clearing cache")
        self._worksheet_cache.clear()
        self._permissions_cache.clear()
        self._last_sync_timestamp = None
    
    def upload_data(self, 
                    data: Union[List[Dict[str, Any]], pd.DataFrame],
                    worksheet_name: str,
                    clear_existing: bool = True) -> None:
        """
        Upload data to a Google Sheets worksheet.
        
        Args:
            data: List of dictionaries or DataFrame containing data to upload
            worksheet_name: Name of the worksheet to upload to
            clear_existing: Whether to clear the existing data in the worksheet
            
        Raises:
            RuntimeError: If not authenticated
            ValueError: If data is empty
        """
        self._ensure_authenticated()
        
        if isinstance(data, pd.DataFrame):
            # Convert DataFrame to list of dictionaries
            data_dict = data.to_dict(orient='records')
        else:
            data_dict = data
            
        if not data_dict:
            logger.warning("No data to upload")
            return
            
        # Get column headers from the first row
        headers = list(data_dict[0].keys())
        
        # Convert data to list of lists for uploading
        values = [headers]  # First row is headers
        for item in data_dict:
            row = [item.get(header, "") for header in headers]
            values.append(row)
            
        # Get the worksheet
        worksheet = self.get_worksheet(worksheet_name)
        
        # Clear existing data if requested
        if clear_existing:
            worksheet.clear()
            # Also clear cache for this worksheet if caching is enabled
            if self.enable_caching and worksheet_name in self._worksheet_cache:
                del self._worksheet_cache[worksheet_name]
        
        try:
            # Try with exponential backoff for rate limiting
            for attempt in range(self.MAX_RETRIES):
                try:
                    worksheet.update(values)
                    logger.info(f"Successfully uploaded {len(data_dict)} rows to worksheet '{worksheet_name}'")
                    # Update last sync timestamp
                    self._last_sync_timestamp = datetime.datetime.now()
                    break
                except gspread.exceptions.APIError as e:
                    if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                        # Rate limiting - wait and retry
                        time.sleep(self.RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                    else:
                        raise
        except Exception as e:
            logger.error(f"Error uploading data: {str(e)}")
            raise
            
    def upload_data_optimized(self,
                             data: Union[List[Dict[str, Any]], pd.DataFrame],
                             worksheet_name: str,
                             clear_existing: bool = False,
                             detect_changes: bool = True) -> Dict[str, int]:
        """
        Upload data to a Google Sheets worksheet with optimizations to reduce API calls.
        
        This method can detect changes and only update modified cells, which
        significantly reduces API usage for large worksheets with minimal changes.
        
        Args:
            data: List of dictionaries or DataFrame containing data to upload
            worksheet_name: Name of the worksheet to upload to
            clear_existing: Whether to clear the existing data in the worksheet
            detect_changes: Whether to detect changes and only update modified cells
            
        Returns:
            Dictionary with counts of cells added, updated, and unchanged
            
        Raises:
            RuntimeError: If not authenticated
            ValueError: If data is empty
        """
        self._ensure_authenticated()
        
        if isinstance(data, pd.DataFrame):
            # Convert DataFrame to list of dictionaries
            data_dict = data.to_dict(orient='records')
        else:
            data_dict = data
            
        if not data_dict:
            logger.warning("No data to upload")
            return {"added": 0, "updated": 0, "unchanged": 0}
            
        # Get column headers from the first row
        headers = list(data_dict[0].keys())
        
        # Convert data to list of lists for uploading
        new_values = [headers]  # First row is headers
        for item in data_dict:
            row = [item.get(header, "") for header in headers]
            new_values.append(row)
            
        # Get the worksheet
        worksheet = self.get_worksheet(worksheet_name)
        
        # Clear existing data if requested
        if clear_existing:
            worksheet.clear()
            # Also clear cache for this worksheet if caching is enabled
            if self.enable_caching and worksheet_name in self._worksheet_cache:
                del self._worksheet_cache[worksheet_name]
            # Upload all data at once
            try:
                worksheet.update(new_values)
                return {"added": len(new_values), "updated": 0, "unchanged": 0}
            except Exception as e:
                logger.error(f"Error uploading data: {str(e)}")
                raise
                
        # If not clearing and we want to detect changes
        if detect_changes:
            try:
                # Get existing data
                existing_values = worksheet.get_all_values()
                
                # If no existing data or headers don't match, just update everything
                if not existing_values or existing_values[0] != new_values[0]:
                    worksheet.update(new_values)
                    return {"added": len(new_values), "updated": 0, "unchanged": 0}
                
                # Count stats
                stats = {"added": 0, "updated": 0, "unchanged": 0}
                
                # Check which rows need to be updated
                existing_len = len(existing_values)
                new_len = len(new_values)
                
                # Create a batch update for changed cells
                batch_updates = []
                
                # Process common rows (update only if changed)
                for i in range(1, min(existing_len, new_len)):  # Skip header row
                    for j in range(len(headers)):
                        # Check if column exists in both old and new data
                        if j < len(existing_values[i]) and j < len(new_values[i]):
                            if existing_values[i][j] != new_values[i][j]:
                                # Cell value has changed
                                batch_updates.append({
                                    'range': f'{chr(65+j)}{i+1}',  # A1 notation
                                    'values': [[new_values[i][j]]]
                                })
                                stats["updated"] += 1
                            else:
                                stats["unchanged"] += 1
                
                # Process new rows if any (add)
                if new_len > existing_len:
                    range_notation = f'A{existing_len+1}:{chr(65+len(headers)-1)}{new_len}'
                    new_rows = new_values[existing_len:]
                    batch_updates.append({
                        'range': range_notation,
                        'values': new_rows
                    })
                    stats["added"] += (new_len - existing_len) * len(headers)
                
                # Execute batch update if there are any changes
                if batch_updates:
                    worksheet.batch_update(batch_updates)
                    logger.info(f"Updated {stats['updated']} cells, added {stats['added']} cells")
                else:
                    logger.info("No changes detected, skipping update")
                
                return stats
            except Exception as e:
                logger.error(f"Error in optimized upload: {str(e)}")
                # Fall back to regular update
                worksheet.update(new_values)
                return {"added": 0, "updated": len(new_values), "unchanged": 0}
        else:
            # If not detecting changes, just update everything
            worksheet.update(new_values)
            return {"added": 0, "updated": len(new_values), "unchanged": 0}
        
    def append_data(self,
                    data: Union[List[Dict[str, Any]], pd.DataFrame],
                    worksheet_name: str) -> None:
        """
        Append data to a Google Sheets worksheet without clearing existing data.
        
        Args:
            data: List of dictionaries or DataFrame containing data to append
            worksheet_name: Name of the worksheet to append to
            
        Raises:
            RuntimeError: If not authenticated
            ValueError: If data is empty
        """
        # Just call upload_data with clear_existing=False
        self.upload_data(data, worksheet_name, clear_existing=False)
        
    def get_spreadsheet_permissions(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get the current permissions for the spreadsheet.
        
        Args:
            force_refresh: Whether to force refresh the permissions from the API
                          even if cached permissions are available
        
        Returns:
            List of permission objects
            
        Raises:
            RuntimeError: If not authenticated or no spreadsheet is selected
        """
        self._ensure_authenticated()
        
        if not self.spreadsheet:
            raise ValueError("No spreadsheet selected")
        
        # Check the cache first if caching is enabled and not forcing refresh
        if (self.enable_caching and 
            'permissions' in self._permissions_cache and 
            not force_refresh):
            
            cache_time, permissions = self._permissions_cache['permissions']
            if (datetime.datetime.now() - cache_time).total_seconds() < self.CACHE_TTL:
                logger.debug("Using cached permissions")
                return permissions
        
        # Not in cache, cache expired, or forcing refresh - get from API
        try:
            permissions = self.spreadsheet.list_permissions()
            
            # Update cache if caching is enabled
            if self.enable_caching:
                self._permissions_cache['permissions'] = (datetime.datetime.now(), permissions)
                
            return permissions
        except Exception as e:
            logger.error(f"Error getting permissions: {str(e)}")
            raise
    
    def _validate_email(self, email: str) -> bool:
        """
        Validate that a string is a properly formatted email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            Boolean indicating if email is valid
        """
        # Basic email validation
        if not email or '@' not in email:
            return False
        
        # Split by @ and check both parts
        parts = email.split('@')
        if len(parts) != 2 or not parts[0] or not parts[1] or '.' not in parts[1]:
            return False
            
        return True
    
    def check_api_access(self) -> Dict[str, bool]:
        """
        Check if the current credentials have access to the required Google APIs.
        
        Returns:
            Dictionary with API names as keys and boolean access status as values
        """
        self._ensure_authenticated()
        
        api_status = {
            'drive': False,
            'sheets': False
        }
        
        # Check Drive API access
        try:
            self.client.list_spreadsheet_files(1)  # Just try to list one file
            api_status['drive'] = True
        except Exception as e:
            logger.warning(f"No access to Google Drive API: {str(e)}")
        
        # Check Sheets API access
        if self.spreadsheet_id:
            try:
                self.client.open_by_key(self.spreadsheet_id)
                api_status['sheets'] = True
            except Exception as e:
                logger.warning(f"No access to Google Sheets API: {str(e)}")
        
        return api_status
        
    def _validate_permission_type(self, permission_type: Union[str, PermissionType]) -> str:
        """
        Validate and normalize permission type.
        
        Args:
            permission_type: Permission type (string or enum)
            
        Returns:
            Normalized permission type string
            
        Raises:
            ValueError: If permission type is invalid
        """
        if isinstance(permission_type, PermissionType):
            return permission_type.value
            
        if permission_type not in [pt.value for pt in PermissionType]:
            valid_types = ", ".join([pt.value for pt in PermissionType])
            raise ValueError(f"Invalid permission type: {permission_type}. Valid types: {valid_types}")
            
        return permission_type
    
    def share_spreadsheet(self, 
                          email: str, 
                          permission_type: Union[str, PermissionType] = PermissionType.READER,
                          notify: bool = True,
                          message: Optional[str] = None) -> bool:
        """
        Share the spreadsheet with a user.
        
        Args:
            email: Email address to share with
            permission_type: Permission type (reader, writer, owner)
            notify: Whether to notify the user by email
            message: Optional message to include in the notification email
            
        Returns:
            Boolean indicating if the operation was successful
            
        Raises:
            RuntimeError: If not authenticated or no spreadsheet is selected
            ValueError: If email is invalid or permission type is invalid
        """
        self._ensure_authenticated()
        
        if not self.spreadsheet:
            raise ValueError("No spreadsheet selected")
            
        if not self._validate_email(email):
            raise ValueError(f"Invalid email address: {email}")
            
        perm_type = self._validate_permission_type(permission_type)
        
        try:
            for attempt in range(self.MAX_RETRIES):
                try:
                    self.spreadsheet.share(
                        email, 
                        perm_type=perm_type,
                        notify=notify,
                        email_message=message
                    )
                    logger.info(f"Shared spreadsheet with {email} as {perm_type}")
                    return True
                except gspread.exceptions.APIError as e:
                    if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                        # Rate limiting - wait and retry
                        time.sleep(self.RETRY_DELAY * (2 ** attempt))
                    else:
                        raise
        except Exception as e:
            logger.error(f"Error sharing spreadsheet: {str(e)}")
            raise
    
    def remove_permission(self, email: str) -> bool:
        """
        Remove a user's permission from the spreadsheet.
        
        Args:
            email: Email address to remove permissions for
            
        Returns:
            Boolean indicating if the operation was successful
            
        Raises:
            RuntimeError: If not authenticated or no spreadsheet is selected
            ValueError: If email is invalid
        """
        self._ensure_authenticated()
        
        if not self.spreadsheet:
            raise ValueError("No spreadsheet selected")
            
        if not self._validate_email(email):
            raise ValueError(f"Invalid email address: {email}")
            
        try:
            # Get current permissions to find the permission ID
            permissions = self.get_spreadsheet_permissions()
            permission_id = None
            
            for perm in permissions:
                if perm.get('emailAddress') == email:
                    permission_id = perm.get('id')
                    break
                    
            if not permission_id:
                logger.warning(f"No permission found for {email}")
                return False
                
            # Remove the permission
            self.spreadsheet.remove_permission(permission_id)
            logger.info(f"Removed permission for {email}")
            return True
        except Exception as e:
            logger.error(f"Error removing permission: {str(e)}")
            raise
    
    def make_public(self, permission_type: Union[str, PermissionType] = PermissionType.READER) -> bool:
        """
        Make the spreadsheet publicly accessible.
        
        Note:
            The gspread API uses different parameter formats for sharing with specific users
            versus making a spreadsheet public:
            - For specific users: use email and perm_type="reader|writer|owner"
            - For public access: use None for email, perm_type="anyone", and role="reader|writer"
        
        Args:
            permission_type: Permission type for public access (reader, writer)
            
        Returns:
            Boolean indicating if the operation was successful
            
        Raises:
            RuntimeError: If not authenticated or no spreadsheet is selected
            ValueError: If permission type is invalid
        """
        self._ensure_authenticated()
        
        if not self.spreadsheet:
            raise ValueError("No spreadsheet selected")
            
        perm_type = self._validate_permission_type(permission_type)
        
        if perm_type == PermissionType.OWNER.value:
            raise ValueError("Cannot make a spreadsheet publicly owned")
        
        # Map our permission types to gspread's role values
        # Note: For public sharing, gspread requires role parameter instead of perm_type
        role_mapping = {
            PermissionType.READER.value: "reader",
            PermissionType.WRITER.value: "writer"
        }
        
        try:
            for attempt in range(self.MAX_RETRIES):
                try:
                    # For public sharing, we need to use different parameters
                    self.spreadsheet.share(
                        None,  # No specific user
                        perm_type='anyone',  # This is the type parameter for gspread
                        role=role_mapping[perm_type]  # Role should be "reader" or "writer"
                    )
                    logger.info(f"Made spreadsheet public with {perm_type} access")
                    return True
                except gspread.exceptions.APIError as e:
                    if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                        # Rate limiting - wait and retry
                        time.sleep(self.RETRY_DELAY * (2 ** attempt))
                    else:
                        raise
        except Exception as e:
            logger.error(f"Error making spreadsheet public: {str(e)}")
            raise
    
    def make_private(self) -> bool:
        """
        Make the spreadsheet private (remove public access).
        
        Returns:
            Boolean indicating if the operation was successful
            
        Raises:
            RuntimeError: If not authenticated or no spreadsheet is selected
        """
        self._ensure_authenticated()
        
        if not self.spreadsheet:
            raise ValueError("No spreadsheet selected")
            
        try:
            # Get current permissions to find the public permission
            permissions = self.get_spreadsheet_permissions()
            public_perm_id = None
            
            for perm in permissions:
                if perm.get('type') == 'anyone':
                    public_perm_id = perm.get('id')
                    break
                    
            if not public_perm_id:
                logger.warning("Spreadsheet is not public")
                return False
                
            # Remove the public permission
            self.spreadsheet.remove_permission(public_perm_id)
            logger.info("Made spreadsheet private")
            return True
        except Exception as e:
            logger.error(f"Error making spreadsheet private: {str(e)}")
            raise
            
    def check_api_access(self) -> Dict[str, bool]:
        """
        Check if the current credentials have access to the required APIs.
        
        This method attempts to perform basic operations with both the Google Sheets
        and Google Drive APIs to verify that the credentials have the necessary
        permissions.
        
        Returns:
            Dictionary with access status for each API:
            {
                'sheets': True/False,
                'drive': True/False
            }
        """
        result = {
            'sheets': False,
            'drive': False
        }
        
        # Only try if we're authenticated
        if not self.authenticated:
            try:
                self.authenticate()
            except Exception as e:
                logger.error(f"Authentication failed during API access check: {e}")
                return result
        
        # Check Google Sheets API
        try:
            # Try to list spreadsheets - this will test Sheets API
            self.client.openall()  # Get all accessible spreadsheets
            result['sheets'] = True
            logger.debug("Successfully verified access to Google Sheets API")
        except Exception as e:
            logger.warning(f"No access to Google Sheets API: {e}")
        
        # Check Google Drive API
        try:
            # Try to get permissions of a file - this will test Drive API
            # If we don't have a spreadsheet, create a temporary one
            temp_spreadsheet_created = False
            if not self.spreadsheet_id:
                try:
                    self.spreadsheet_id = self.create_spreadsheet("Temporary API Test")
                    temp_spreadsheet_created = True
                except Exception as e:
                    logger.warning(f"Could not create temporary spreadsheet for Drive API test: {e}")
                    return result
            
            # Try to access permissions
            self.get_spreadsheet_permissions(force_refresh=True)
            result['drive'] = True
            logger.debug("Successfully verified access to Google Drive API")
            
            # Delete the temporary spreadsheet if we created one
            if temp_spreadsheet_created:
                try:
                    self.client.del_spreadsheet(self.spreadsheet_id)
                    self.spreadsheet_id = None
                    self.spreadsheet = None
                except Exception as e:
                    logger.warning(f"Could not delete temporary spreadsheet: {e}")
                    
        except Exception as e:
            logger.warning(f"No access to Google Drive API: {e}")
        
        return result
    
    def convert_dataframe_to_sheets_format(self, 
                                          df: pd.DataFrame,
                                          include_timestamp: bool = True,
                                          timestamp_column: str = "timestamp",
                                          timestamp_format: str = "%Y-%m-%d %H:%M:%S") -> List[List[Any]]:
        """
        Convert a DataFrame to the format required by Google Sheets API.
        
        Args:
            df: The DataFrame to convert
            include_timestamp: Whether to include a timestamp column
            timestamp_column: Name of the timestamp column to add
            timestamp_format: Format for the timestamp
            
        Returns:
            List of lists (rows) formatted for Google Sheets API
            
        Raises:
            ValueError: If the DataFrame is empty
        """
        if df.empty:
            raise ValueError("Cannot convert empty DataFrame")
        
        # Make a copy to avoid modifying the original DataFrame
        df_copy = df.copy()
        
        # Add timestamp column if requested
        current_time = datetime.datetime.now().strftime(timestamp_format)
        if include_timestamp and timestamp_column not in df_copy.columns:
            df_copy[timestamp_column] = current_time
        
        # Convert DataFrame to list of lists format required by Google Sheets
        headers = df_copy.columns.tolist()
        rows = df_copy.values.tolist()
        
        # Insert headers as the first row
        sheets_data = [headers] + rows
        
        # Replace NaN and None values with empty strings for Google Sheets compatibility
        for i, row in enumerate(sheets_data):
            sheets_data[i] = ['' if pd.isna(cell) or cell is None else cell for cell in row]
            
        logger.debug(f"Converted DataFrame with {len(rows)} rows and {len(headers)} columns to Google Sheets format")
        return sheets_data
    
    def format_worksheet(self,
                     worksheet_name: str,
                     bold_header: bool = True,
                     freeze_header: bool = True,
                     autofit_columns: bool = True,
                     number_format: Optional[Dict[str, str]] = None) -> bool:
        """
        Format a worksheet with various styling options.
        
        Args:
            worksheet_name: Name of the worksheet to format
            bold_header: Whether to make the header row bold
            freeze_header: Whether to freeze the header row
            autofit_columns: Whether to automatically adjust column widths based on content
            number_format: Dictionary mapping column names to number formats
                           Example: {'Price': '0.00', 'Quantity': '0'}
            
        Returns:
            Boolean indicating if the operation was successful
            
        Raises:
            RuntimeError: If not authenticated or worksheet doesn't exist
        """
        self._ensure_authenticated()
        
        # Get the worksheet
        worksheet = self.get_worksheet(worksheet_name, create_if_missing=False)
        
        try:
            # Get current worksheet data to determine dimensions
            data = worksheet.get_all_values()
            if not data:
                logger.warning(f"Worksheet '{worksheet_name}' is empty, nothing to format")
                return False
                
            header_row = data[0]
            
            # Format the header row (bold)
            if bold_header:
                header_cells = worksheet.range(1, 1, 1, len(header_row))
                for cell in header_cells:
                    cell.value = cell.value  # Keep the same value
                    
                # Use batch update to set the bold format
                format_request = {
                    "requests": [
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 0,
                                    "endRowIndex": 1,
                                    "startColumnIndex": 0,
                                    "endColumnIndex": len(header_row)
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "textFormat": {
                                            "bold": True
                                        }
                                    }
                                },
                                "fields": "userEnteredFormat.textFormat.bold"
                            }
                        }
                    ]
                }
                self.spreadsheet.batch_update(format_request)
            
            # Freeze the header row
            if freeze_header:
                worksheet.freeze(rows=1)
            
            # Auto-resize columns
            if autofit_columns and len(data) > 0:
                # Get column widths based on content
                column_widths = []
                for col_idx, header in enumerate(header_row):
                    # Start with header width
                    max_width = len(str(header))
                    
                    # Find the maximum width in this column
                    for row in data[1:]:  # Skip header row
                        if col_idx < len(row):
                            cell_value = str(row[col_idx])
                            max_width = max(max_width, min(len(cell_value), 200))  # Cap at 200 chars
                    
                    # Add some padding
                    column_widths.append(max_width + 2)
                
                # Set column widths
                for i, width in enumerate(column_widths):
                    # Create column resize request
                    resize_request = {
                        "requests": [
                            {
                                "updateDimensionProperties": {
                                    "range": {
                                        "sheetId": worksheet.id,
                                        "dimension": "COLUMNS",
                                        "startIndex": i,
                                        "endIndex": i + 1
                                    },
                                    "properties": {
                                        "pixelSize": width * 8  # Approximate pixel width
                                    },
                                    "fields": "pixelSize"
                                }
                            }
                        ]
                    }
                self.spreadsheet.batch_update(resize_request)
            # Apply number formats if provided
            if number_format:
                fmt_requests = []
                for col_name, pattern in number_format.items():
                    if col_name in header_row:
                        idx = header_row.index(col_name)
                        fmt_requests.append({
                            "repeatCell": {
                                "range": {
                                    "sheetId": worksheet.id,
                                    "startRowIndex": 1,
                                    "endRowIndex": len(data),
                                    "startColumnIndex": idx,
                                    "endColumnIndex": idx + 1
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "numberFormat": {
                                            "type": "NUMBER",
                                            "pattern": pattern
                                        }
                                    }
                                },
                                "fields": "userEnteredFormat.numberFormat"
                            }
                        })
                if fmt_requests:
                    self.spreadsheet.batch_update({"requests": fmt_requests})
            return True
            
            # Apply number formats if specified
            if number_format and len(data) > 1:  # At least header + 1 row
                for col_name, format_str in number_format.items():
                    # Find the column index
                    try:
                        col_idx = header_row.index(col_name)
                        
                        # Apply number format to the entire column (except header)
                        format_request = {
                            "requests": [
                                {
                                    "repeatCell": {
                                        "range": {
                                            "sheetId": worksheet.id,
                                            "startRowIndex": 1,  # Skip header
                                            "endRowIndex": len(data),
                                            "startColumnIndex": col_idx,
                                            "endColumnIndex": col_idx + 1
                                        },
                                        "cell": {
                                            "userEnteredFormat": {
                                                "numberFormat": {
                                                    "type": "NUMBER",
                                                    "pattern": format_str
                                                }
                                            }
                                        },
                                        "fields": "userEnteredFormat.numberFormat"
                                    }
                                }
                            ]
                        }
                        self.spreadsheet.batch_update(format_request)
                    except ValueError:
                        logger.warning(f"Column '{col_name}' not found in worksheet")
            
            logger.info(f"Successfully formatted worksheet '{worksheet_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error formatting worksheet: {str(e)}")
            raise
    
    def batch_update_data(self,
                       data: Union[List[Dict[str, Any]], pd.DataFrame],
                       worksheet_name: str,
                       batch_size: int = 1000,
                       mode: str = 'append',
                       rate_limit_pause: float = 1.0) -> Dict[str, int]:
        """
        Update a worksheet with large datasets by splitting into manageable batches.
        
        This method is designed for large datasets that might exceed API limits if
        uploaded in a single operation. It splits the data into smaller batches and
        handles rate limiting automatically.
        
        Args:
            data: DataFrame or list of dictionaries containing the data
            worksheet_name: Name of the worksheet to update
            batch_size: Maximum number of rows per batch
            mode: Update mode ('append' or 'overwrite')
            rate_limit_pause: Pause between batches in seconds to avoid rate limits
            
        Returns:
            Dictionary with statistics about the operation:
            {
                'total_rows': Total number of rows processed,
                'batches': Number of batches used,
                'errors': Number of batches that failed
            }
            
        Raises:
            RuntimeError: If not authenticated
            ValueError: If data is empty or mode is invalid
        """
        self._ensure_authenticated()
        
        # Validate mode
        valid_modes = ['append', 'overwrite']
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {valid_modes}")
        
        # Convert DataFrame to list of dictionaries if needed
        if isinstance(data, pd.DataFrame):
            data_dict = data.to_dict(orient='records')
        else:
            data_dict = data
            
        if not data_dict:
            logger.warning("No data to upload")
            return {'total_rows': 0, 'batches': 0, 'errors': 0}
            
        # Initialize statistics
        stats = {'total_rows': len(data_dict), 'batches': 0, 'errors': 0}
        
        # Get the worksheet
        worksheet = self.get_worksheet(worksheet_name)
        
        # If overwrite mode, clear the worksheet at the beginning
        if mode == 'overwrite':
            worksheet.clear()
            # Also clear cache for this worksheet if caching is enabled
            if self.enable_caching and worksheet_name in self._worksheet_cache:
                del self._worksheet_cache[worksheet_name]
        
        # Get column headers from the first row
        headers = list(data_dict[0].keys())
        
        # Split data into batches
        batches = []
        current_batch = []
        
        for item in data_dict:
            current_batch.append(item)
            if len(current_batch) >= batch_size:
                batches.append(current_batch)
                current_batch = []
                
        # Add any remaining items as the last batch
        if current_batch:
            batches.append(current_batch)
            
        # Process each batch
        for batch_index, batch in enumerate(batches):
            stats['batches'] += 1
            logger.info(f"Processing batch {batch_index + 1}/{len(batches)} ({len(batch)} rows)")
            
            # Convert batch to list of lists
            batch_values = [headers] if batch_index == 0 else []  # Only include headers in first batch
            for item in batch:
                row = [item.get(header, "") for header in headers]
                batch_values.append(row)
                
            # Calculate the starting row for this batch
            if mode == 'append':
                if batch_index == 0 and worksheet.row_count <= 1:
                    # First batch and empty worksheet - just update
                    start_row = 1
                elif batch_index == 0:
                    # First batch with existing data - get the last row
                    existing_data = worksheet.get_all_values()
                    start_row = len(existing_data) + 1
                else:
                    # Subsequent batches - calculate from previous batches
                    start_row += len(batches[batch_index-1])
            else:  # overwrite mode
                if batch_index == 0:
                    start_row = 1  # Start at the beginning
                else:
                    # Subsequent batches - calculate from previous batches plus 1 for header
                    start_row = 1 + sum(len(b) for b in batches[:batch_index])
                    
            # Try to upload this batch with exponential backoff for rate limiting
            success = False
            for attempt in range(self.MAX_RETRIES):
                try:
                    if batch_index == 0 and mode == 'overwrite':
                        # For first batch in overwrite mode, just update
                        worksheet.update(batch_values)
                    else:
                        # For append mode or subsequent batches, use range update
                        if start_row == 1 and batch_index == 0:
                            # First batch and starting from beginning
                            worksheet.update(batch_values)
                        else:
                            # Calculate the range for this batch
                            last_column = chr(65 + len(headers) - 1)  # Convert to letter (A, B, C, etc.)
                            range_name = f'A{start_row}:{last_column}{start_row + len(batch_values) - 1}'
                            worksheet.update(range_name, batch_values)
                    
                    success = True
                    break
                except gspread.exceptions.APIError as e:
                    if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                        # Rate limiting - wait and retry with exponential backoff
                        backoff_time = self.RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"Rate limit hit, retrying in {backoff_time:.1f} seconds")
                        time.sleep(backoff_time)
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Error uploading batch {batch_index + 1}: {str(e)}")
                    stats['errors'] += 1
                    break
                    
            if not success:
                stats['errors'] += 1
                
            # Pause between batches to avoid rate limiting
            if batch_index < len(batches) - 1:  # Don't pause after the last batch
                time.sleep(rate_limit_pause)
        
        # Update last sync timestamp
        self._last_sync_timestamp = datetime.datetime.now()
        
        # Clear cache for this worksheet if caching is enabled
        if self.enable_caching and worksheet_name in self._worksheet_cache:
            del self._worksheet_cache[worksheet_name]
            
        logger.info(f"Batch update complete: {stats['total_rows']} rows in {stats['batches']} batches with {stats['errors']} errors")
        return stats
