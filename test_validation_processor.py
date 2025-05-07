#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for ValidationProcessor integration.
This script tests the newly implemented methods directly.
"""

import os
import sys
import json
import pandas as pd
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the ValidationProcessor directly
from processing.data_processor import ValidationProcessor

def main():
    """Run test for ValidationProcessor methods"""
    # Load test data
    test_data_path = os.path.join("results", "test_data.json")
    
    with open(test_data_path, "r") as f:
        test_data = json.load(f)
    
    print(f"\nLoaded {len(test_data)} test records")
    
    # Convert to DataFrame
    df = pd.DataFrame(test_data)
    
    print("\nOriginal data:")
    print(df[["business_name", "email", "phone"]])
    
    # Initialize ValidationProcessor
    processor = ValidationProcessor(df)
    
    # Test validate_emails
    print("\nValidating emails...")
    df_with_emails = processor.validate_emails()
    print(f"Valid emails: {df_with_emails['email_valid'].sum()} out of {len(df_with_emails)}")
    print(df_with_emails[["business_name", "email", "email_valid"]])
    
    # Test validate_phone_numbers
    print("\nValidating phone numbers...")
    df_with_phones = processor.validate_phone_numbers()
    print(f"Valid phones: {df_with_phones['phone_valid'].sum()} out of {len(df_with_phones)}")
    print(df_with_phones[["business_name", "phone", "phone_valid"]])
    
    # Test combined process (simulating main.py flow)
    print("\nSimulating complete processing flow...")
    # Update the processor's data with email validation results
    processor.data = processor.validate_emails()
    # Update with phone validation results
    processor.data = processor.validate_phone_numbers()
    # Process the data (calculates scores, validates records, etc.)
    processed_df = processor.process()
    
    # Test filter_by_quality_score
    print("\nFiltering by quality score...")
    high_quality_df = processor.filter_by_quality_score(min_score=80)
    medium_quality_df = processor.filter_by_quality_score(min_score=50)
    
    print(f"Records with quality ≥ 80%: {len(high_quality_df)} out of {len(processed_df)}")
    print(f"Records with quality ≥ 50%: {len(medium_quality_df)} out of {len(processed_df)}")
    
    # Display quality scores
    print("\nQuality scores for all records:")
    for _, row in processed_df.iterrows():
        print(f"{row['business_name']}: {row['validation_score']}%")
    
    # Save processed results
    output_path = os.path.join("results", "validation_processed_test.csv")
    processed_df.to_csv(output_path, index=False)
    print(f"\nSaved processed data to: {output_path}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
