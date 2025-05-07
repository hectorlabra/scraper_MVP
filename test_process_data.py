#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for process_data in main.py.
This script tests the integration of ValidationProcessor in the main workflow.
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the function we want to test
from main import process_data

def main():
    """Run test for process_data function"""
    # Load test data
    test_data_path = os.path.join("results", "test_data.json")
    
    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    
    # Verify if test data exists, create it if not
    if not os.path.exists(test_data_path):
        print(f"Test data not found at: {test_data_path}")
        return
    
    with open(test_data_path, "r") as f:
        test_data = json.load(f)
    
    print(f"Loaded {len(test_data)} test records")
    
    # Process data with validation enabled
    config = {
        "validation": {
            "enable_email_validation": True,
            "enable_phone_validation": True,
            "min_data_quality": 50  # 50%
        },
        "deduplication": {
            "exact_match": False,  # Disable deduplication for this test
            "fuzzy_match": False
        }
    }
    
    print("\nProcessing data with validation...")
    result_df = process_data(test_data, config)
    
    print(f"\nProcessed result: {len(result_df)} records")
    print("\nColumns in result:")
    print(result_df.columns.tolist())
    
    # Save the processed data to CSV for inspection
    output_path = os.path.join("results", "processed_test_data.csv")
    result_df.to_csv(output_path, index=False)
    print(f"\nSaved processed data to: {output_path}")
    
    # Show validation results
    if 'email_valid' in result_df.columns and 'phone_valid' in result_df.columns:
        print("\nValidation Results:")
        print(f"Valid emails: {result_df['email_valid'].sum()} out of {len(result_df)}")
        print(f"Valid phones: {result_df['phone_valid'].sum()} out of {len(result_df)}")
        
        # Show quality scores if available
        if 'validation_score' in result_df.columns:
            print("\nQuality Scores:")
            for _, row in result_df.iterrows():
                print(f"{row['business_name']}: {row.get('validation_score', 'N/A')}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
