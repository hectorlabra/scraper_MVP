#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets Formatting Helper

This module provides additional formatting functionality for the GoogleSheetsIntegration class.
It includes methods for formatting headers, adjusting column widths, and applying styles to cells.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import time

import gspread
from gspread.utils import rowcol_to_a1, a1_to_rowcol

# Configure logging
logger = logging.getLogger(__name__)

class SheetFormatter:
    """
    Helper class for formatting Google Sheets worksheets.
    
    This class provides methods for:
    - Formatting headers (bold, background color, etc.)
    - Adjusting column widths based on content
    - Freezing header rows
    - Applying conditional formatting
    - Creating data validation rules
    """
    
    # API request retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, worksheet: gspread.Worksheet):
        """
        Initialize the formatter with a worksheet.
        
        Args:
            worksheet: The gspread Worksheet object to format
        """
        self.worksheet = worksheet
        
    def format_header_row(self, 
                          row_index: int = 1, 
                          bold: bool = True, 
                          background_color: Optional[Dict[str, float]] = None,
                          text_color: Optional[Dict[str, float]] = None,
                          horizontal_alignment: str = "CENTER") -> None:
        """
        Format the header row with styling options.
        
        Args:
            row_index: The row index to format (default is 1, the first row)
            bold: Whether to make the text bold
            background_color: RGB background color as a dict, e.g., {"red": 0.8, "green": 0.8, "blue": 0.8}
            text_color: RGB text color as a dict
            horizontal_alignment: Text alignment ("LEFT", "CENTER", "RIGHT")
            
        Returns:
            None
        """
        if background_color is None:
            # Default light gray background
            background_color = {"red": 0.9, "green": 0.9, "blue": 0.9}
            
        if text_color is None:
            # Default black text
            text_color = {"red": 0, "green": 0, "blue": 0}
            
        # Get the number of columns in the worksheet
        data = self.worksheet.get_all_values()
        if not data:
            logger.warning("Worksheet is empty, cannot format header row")
            return
            
        num_cols = len(data[0])
        if num_cols == 0:
            logger.warning("Header row is empty, cannot format header row")
            return
            
        # Create the format request
        format_request = {
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": self.worksheet.id,
                            "startRowIndex": row_index - 1,  # 0-indexed
                            "endRowIndex": row_index,
                            "startColumnIndex": 0,
                            "endColumnIndex": num_cols
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": background_color,
                                "textFormat": {
                                    "bold": bold,
                                    "foregroundColor": text_color
                                },
                                "horizontalAlignment": horizontal_alignment
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
                    }
                }
            ]
        }
        
        # Execute the request with retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                self.worksheet.spreadsheet.batch_update(format_request)
                logger.info(f"Formatted header row {row_index}")
                break
            except gspread.exceptions.APIError as e:
                if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                    # Rate limiting - wait and retry
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                else:
                    logger.error(f"Error formatting header row: {str(e)}")
                    raise
        
    def freeze_rows(self, num_rows: int = 1) -> None:
        """
        Freeze the top rows of the worksheet.
        
        Args:
            num_rows: Number of rows to freeze (default is 1, the header row)
            
        Returns:
            None
        """
        freeze_request = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": self.worksheet.id,
                            "gridProperties": {
                                "frozenRowCount": num_rows
                            }
                        },
                        "fields": "gridProperties.frozenRowCount"
                    }
                }
            ]
        }
        
        # Execute the request with retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                self.worksheet.spreadsheet.batch_update(freeze_request)
                logger.info(f"Froze {num_rows} rows")
                break
            except gspread.exceptions.APIError as e:
                if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                    # Rate limiting - wait and retry
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                else:
                    logger.error(f"Error freezing rows: {str(e)}")
                    raise
    
    def adjust_column_widths(self, 
                            columns: Optional[List[int]] = None, 
                            min_width: int = 50,
                            max_width: int = 250,
                            header_padding: int = 10) -> None:
        """
        Automatically adjust column widths based on content.
        
        Args:
            columns: List of column indices to adjust (1-indexed). If None, adjusts all columns.
            min_width: Minimum column width in pixels
            max_width: Maximum column width in pixels
            header_padding: Extra padding for header text in pixels
            
        Returns:
            None
        """
        # Get worksheet data
        data = self.worksheet.get_all_values()
        if not data:
            logger.warning("Worksheet is empty, cannot adjust column widths")
            return
            
        # Determine which columns to adjust
        all_columns = list(range(1, len(data[0]) + 1))
        columns_to_adjust = columns if columns else all_columns
        
        # Calculate ideal width for each column
        column_widths = {}
        for col in columns_to_adjust:
            # Check that the column exists
            if col < 1 or col > len(data[0]):
                logger.warning(f"Column {col} is out of range, skipping")
                continue
                
            col_index = col - 1  # Convert to 0-indexed
            
            # Get the column header (assumed to be in the first row)
            header_text = data[0][col_index] if data and len(data) > 0 and len(data[0]) > col_index else ""
            
            # Calculate header width (approximately 7 pixels per character, plus padding)
            header_width = len(str(header_text)) * 7 + header_padding
            
            # Find the maximum width needed for data in this column
            max_data_width = 0
            for row in data[1:]:  # Skip header row
                if col_index < len(row):
                    # Calculate data width (approximately 7 pixels per character)
                    data_width = len(str(row[col_index])) * 7
                    max_data_width = max(max_data_width, data_width)
            
            # Use the greater of header width or data width, constrained by min/max
            ideal_width = max(min_width, min(max_width, max(header_width, max_data_width)))
            column_widths[col] = ideal_width
        
        # Apply the column widths
        for col, width in column_widths.items():
            col_letter = self._column_index_to_letter(col)
            
            dimension_request = {
                "requests": [
                    {
                        "updateDimensionProperties": {
                            "range": {
                                "sheetId": self.worksheet.id,
                                "dimension": "COLUMNS",
                                "startIndex": col - 1,  # 0-indexed
                                "endIndex": col  # exclusive
                            },
                            "properties": {
                                "pixelSize": width
                            },
                            "fields": "pixelSize"
                        }
                    }
                ]
            }
            
            # Execute the request with retry logic
            for attempt in range(self.MAX_RETRIES):
                try:
                    self.worksheet.spreadsheet.batch_update(dimension_request)
                    logger.info(f"Adjusted width of column {col_letter} to {width} pixels")
                    break
                except gspread.exceptions.APIError as e:
                    if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                        # Rate limiting - wait and retry
                        time.sleep(self.RETRY_DELAY * (2 ** attempt))
                    else:
                        logger.error(f"Error adjusting column width: {str(e)}")
                        raise
    
    def apply_alternating_row_colors(self,
                                     start_row: int = 2,  # Skip header
                                     even_color: Optional[Dict[str, float]] = None,
                                     odd_color: Optional[Dict[str, float]] = None) -> None:
        """
        Apply alternating row colors for better readability.
        
        Args:
            start_row: First row to apply coloring to (default is 2, skipping header)
            even_color: RGB color for even rows as a dict
            odd_color: RGB color for odd rows as a dict
            
        Returns:
            None
        """
        if even_color is None:
            # Default light gray for even rows
            even_color = {"red": 0.95, "green": 0.95, "blue": 0.95}
            
        if odd_color is None:
            # Default white for odd rows
            odd_color = {"red": 1, "green": 1, "blue": 1}
            
        # Get worksheet dimensions
        data = self.worksheet.get_all_values()
        if not data:
            logger.warning("Worksheet is empty, cannot apply alternating row colors")
            return
            
        num_rows = len(data)
        if num_rows < start_row:
            logger.warning("Worksheet has fewer rows than start_row, cannot apply alternating row colors")
            return
            
        num_cols = len(data[0])
        
        # Create the format requests for even and odd rows
        requests = []
        
        # Even rows
        even_rows = list(range(start_row, num_rows + 1, 2))
        for row in even_rows:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "startRowIndex": row - 1,  # 0-indexed
                        "endRowIndex": row,
                        "startColumnIndex": 0,
                        "endColumnIndex": num_cols
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": even_color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })
        
        # Odd rows
        odd_rows = list(range(start_row + 1, num_rows + 1, 2))
        for row in odd_rows:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": self.worksheet.id,
                        "startRowIndex": row - 1,  # 0-indexed
                        "endRowIndex": row,
                        "startColumnIndex": 0,
                        "endColumnIndex": num_cols
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": odd_color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            })
        
        # Execute the request with retry logic
        format_request = {"requests": requests}
        for attempt in range(self.MAX_RETRIES):
            try:
                self.worksheet.spreadsheet.batch_update(format_request)
                logger.info(f"Applied alternating row colors to {len(even_rows) + len(odd_rows)} rows")
                break
            except gspread.exceptions.APIError as e:
                if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                    # Rate limiting - wait and retry
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                else:
                    logger.error(f"Error applying alternating row colors: {str(e)}")
                    raise
    
    def apply_basic_formatting(self) -> None:
        """
        Apply a set of basic formatting options to make the spreadsheet more readable.
        
        This is a convenience method that applies:
        - Bold header with gray background
        - Frozen header row
        - Automatically adjusted column widths
        - Alternating row colors
        
        Returns:
            None
        """
        try:
            # Format and freeze header row
            self.format_header_row()
            self.freeze_rows(1)
            
            # Adjust column widths based on content
            self.adjust_column_widths()
            
            # Apply alternating row colors
            self.apply_alternating_row_colors()
            
            logger.info("Applied basic formatting to worksheet")
        except Exception as e:
            logger.error(f"Error applying basic formatting: {str(e)}")
            raise
    
    def _column_index_to_letter(self, column_index: int) -> str:
        """
        Convert a column index (1-indexed) to a column letter (A, B, C, etc.).
        
        Args:
            column_index: 1-indexed column number (1 for A, 2 for B, etc.)
            
        Returns:
            Column letter or letters (A, B, ..., Z, AA, AB, etc.)
        """
        column_index -= 1  # Convert to 0-indexed
        if column_index < 0:
            raise ValueError("Column index must be positive")
            
        result = ""
        while column_index >= 0:
            result = chr(65 + (column_index % 26)) + result
            column_index = (column_index // 26) - 1
            
        return result
    
    def add_filter(self) -> None:
        """
        Add a filter to the header row.
        
        Returns:
            None
        """
        # Get worksheet dimensions
        data = self.worksheet.get_all_values()
        if not data:
            logger.warning("Worksheet is empty, cannot add filter")
            return
            
        num_cols = len(data[0])
        
        # Create the filter request
        filter_request = {
            "requests": [
                {
                    "setBasicFilter": {
                        "filter": {
                            "range": {
                                "sheetId": self.worksheet.id,
                                "startRowIndex": 0,
                                "endRowIndex": len(data),
                                "startColumnIndex": 0,
                                "endColumnIndex": num_cols
                            }
                        }
                    }
                }
            ]
        }
        
        # Execute the request with retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                self.worksheet.spreadsheet.batch_update(filter_request)
                logger.info("Added filter to worksheet")
                break
            except gspread.exceptions.APIError as e:
                if attempt < self.MAX_RETRIES - 1 and e.response.status_code == 429:
                    # Rate limiting - wait and retry
                    time.sleep(self.RETRY_DELAY * (2 ** attempt))
                else:
                    logger.error(f"Error adding filter: {str(e)}")
                    raise
