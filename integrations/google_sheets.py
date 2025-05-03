#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets Integration Module

This module provides functionality to upload data to Google Sheets.
"""

import logging
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

class GoogleSheetsIntegration:
    """Class for integrating with Google Sheets."""
    
    def __init__(self, 
                 credentials_file: Optional[str] = None,
                 spreadsheet_id: Optional[str] = None):
        """
        Initialize the Google Sheets integration.
        
        Args:
            credentials_file: Path to the Google service account credentials file
            spreadsheet_id: ID of the Google spreadsheet to use
        """
        self.credentials_file = credentials_file or os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
        self.client = None
        self.spreadsheet = None
        
        if not self.credentials_file:
            logger.warning("No credentials file provided. Use set_credentials() to set it later.")
        
        if not self.spreadsheet_id:
            logger.warning("No spreadsheet ID provided. Use set_spreadsheet_id() to set it later.")
    
    def set_credentials(self, credentials_file: str) -> None:
        """
        Set the credentials file.
        
        Args:
            credentials_file: Path to the Google service account credentials file
        """
        self.credentials_file = credentials_file
    
    def set_spreadsheet_id(self, spreadsheet_id: str) -> None:
        """
        Set the spreadsheet ID.
        
        Args:
            spreadsheet_id: ID of the Google spreadsheet to use
        """
        self.spreadsheet_id = spreadsheet_id
    
    def authenticate(self) -> None:
        """Authenticate with Google Sheets API."""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                self.credentials_file, scopes=scopes
            )
            
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            logger.info("Successfully authenticated with Google Sheets")
        except Exception as e:
            logger.error(f"Error authenticating with Google Sheets: {str(e)}")
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
        """
        if not self.client or not self.spreadsheet:
            self.authenticate()
            
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            if create_if_missing:
                logger.info(f"Creating new worksheet: {worksheet_name}")
                return self.spreadsheet.add_worksheet(
                    title=worksheet_name, rows=1000, cols=26
                )
            else:
                logger.error(f"Worksheet not found: {worksheet_name}")
                raise
    
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
        """
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
            
        # Upload the data
        worksheet.update(values)
        logger.info(f"Successfully uploaded {len(data_dict)} rows to worksheet '{worksheet_name}'")
        
    def append_data(self,
                    data: Union[List[Dict[str, Any]], pd.DataFrame],
                    worksheet_name: str) -> None:
        """
        Append data to a Google Sheets worksheet without clearing existing data.
        
        Args:
            data: List of dictionaries or DataFrame containing data to append
            worksheet_name: Name of the worksheet to append to
        """
        # Just call upload_data with clear_existing=False
        self.upload_data(data, worksheet_name, clear_existing=False)
