#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Processor Module

This module provides functionality to process and transform data from different sources.
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Union, Optional

logger = logging.getLogger(__name__)

class DataProcessor:
    """Base class for processing and transforming scraped data."""
    
    def __init__(self):
        """Initialize the data processor."""
        self.data = pd.DataFrame()
        
    def load_data(self, data: Union[List[Dict[str, Any]], pd.DataFrame]) -> None:
        """
        Load data into the processor.
        
        Args:
            data: List of dictionaries or DataFrame containing data to process
        """
        if isinstance(data, list):
            self.data = pd.DataFrame(data)
        elif isinstance(data, pd.DataFrame):
            self.data = data
        else:
            raise TypeError("Data must be a list of dictionaries or a pandas DataFrame")
        
        logger.info(f"Loaded {len(self.data)} records into processor")
    
    def clean_data(self) -> None:
        """
        Perform basic data cleaning operations.
        
        - Remove duplicate rows
        - Remove rows with all NaN values
        - Strip whitespace from string columns
        """
        initial_count = len(self.data)
        
        # Remove duplicates
        self.data = self.data.drop_duplicates()
        
        # Remove rows with all NaN values
        self.data = self.data.dropna(how='all')
        
        # Strip whitespace from string columns
        for col in self.data.select_dtypes(include=['object']).columns:
            self.data[col] = self.data[col].str.strip() if hasattr(self.data[col], 'str') else self.data[col]
            
        final_count = len(self.data)
        logger.info(f"Cleaned data: removed {initial_count - final_count} records")
    
    def get_data(self) -> pd.DataFrame:
        """
        Get the processed data.
        
        Returns:
            DataFrame containing the processed data
        """
        return self.data
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """
        Convert the processed data to a list of dictionaries.
        
        Returns:
            List of dictionaries containing the processed data
        """
        return self.data.to_dict(orient='records')
    
    def to_csv(self, filepath: str, **kwargs) -> None:
        """
        Save the processed data to a CSV file.
        
        Args:
            filepath: Path to save the CSV file
            **kwargs: Additional arguments to pass to pandas.DataFrame.to_csv()
        """
        self.data.to_csv(filepath, **kwargs)
        logger.info(f"Saved {len(self.data)} records to {filepath}")
