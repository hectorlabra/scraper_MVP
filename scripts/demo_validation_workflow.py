#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example script demonstrating the complete ValidationProcessor workflow.

This script shows a real-world example of using ValidationProcessor for:
1. Validating email addresses and phone numbers
2. Applying data quality scoring
3. Filtering by quality score
4. Processing a real dataset from different sources
"""

import os
import sys
import json
import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path to allow imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import ValidationProcessor
from processing.data_processor import ValidationProcessor

def main():
    """Main function demonstrating ValidationProcessor workflow"""
    print("=== ValidationProcessor Complete Workflow Example ===\n")
    
    # Create results directory if needed
    results_dir = os.path.join(project_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Step 1: Load data (simulating data from multiple sources)
    test_data_path = os.path.join(results_dir, "test_data.json")
    if not os.path.exists(test_data_path):
        print(f"Test data not found at: {test_data_path}")
        print("Creating synthetic data...")
        create_synthetic_data(test_data_path)
    
    with open(test_data_path, "r") as f:
        combined_data = json.load(f)
    
    print(f"Loaded {len(combined_data)} records from combined sources")
    
    # Step 2: Convert to DataFrame
    df = pd.DataFrame(combined_data)
    print(f"\nData statistics:")
    print(f"- Records: {len(df)}")
    print(f"- Sources: {df['source'].unique()}")
    print(f"- Countries: {df['location'].str.split(',').str[-1].str.strip().unique()}")
    
    # Step 3: Initialize ValidationProcessor
    print("\nInitializing ValidationProcessor...")
    validator = ValidationProcessor(df)
    
    # Step 4: Validate email addresses
    print("\nValidating email addresses...")
    df_with_emails = validator.validate_emails()
    valid_emails_count = df_with_emails['email_valid'].sum()
    print(f"- Valid emails: {valid_emails_count} ({valid_emails_count/len(df)*100:.1f}%)")

    # Update validator data with email validation results
    validator.data = df_with_emails

    # Step 5: Validate phone numbers
    print("\nValidating phone numbers...")
    df_with_phones = validator.validate_phone_numbers()
    valid_phones_count = df_with_phones['phone_valid'].sum()
    print(f"- Valid phones: {valid_phones_count} ({valid_phones_count/len(df)*100:.1f}%)")

    # Update validator data with phone validation results
    validator.data = df_with_phones

    # Step 6: Process the dataset (performs validation, scoring, and formatting)
    print("\nProcessing full dataset...")
    processed_df = validator.process()

    # Step 7: Analyze validation results
    valid_records = processed_df['is_valid'].sum()
    print(f"\nValidation results:")
    print(f"- Valid records: {valid_records} ({valid_records/len(processed_df)*100:.1f}%)")
    print(f"- Invalid records: {len(processed_df) - valid_records}")

    # Calculate average quality score
    avg_quality = processed_df['validation_score'].mean()
    print(f"- Average quality score: {avg_quality:.1f}%")

    # Step 8: Filter by quality score thresholds
    print("\nFiltering by quality score thresholds...")
    high_quality = validator.filter_by_quality_score(min_score=80)
    medium_quality = validator.filter_by_quality_score(min_score=50)
    low_quality = validator.filter_by_quality_score(min_score=30)
    
    print(f"- High quality (≥80%): {len(high_quality)} records")
    print(f"- Medium quality (≥50%): {len(medium_quality)} records")
    print(f"- Low quality (≥30%): {len(low_quality)} records")
    
    # Step 9: Save processed results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(results_dir, f"validated_data_{timestamp}.csv")
    processed_df.to_csv(output_path, index=False)
    print(f"\nSaved processed data to: {output_path}")
    
    # Step 10: Show example of high-quality records
    print("\nSample of high-quality records:")
    sample_columns = ['business_name', 'email', 'phone', 'validation_score']
    if len(high_quality) > 0:
        print(high_quality[sample_columns].head(3))
    else:
        print("No high-quality records found.")
    
    print("\nExample completed successfully!")

def create_synthetic_data(output_path, num_records=5):
    """Create synthetic test data if none exists"""
    test_data = [
        {
            "business_name": "Alpha Technologies",
            "phone": "+52 55 1234 5678",
            "email": "info@alphatech.com",
            "location": "Mexico City, Mexico",
            "website": "https://www.alphatech.com",
            "industry": "Technology",
            "description": "Leading technology provider in LATAM",
            "source": "Google Maps"
        },
        {
            "business_name": "Beta Services",
            "phone": "+55 11 91234-5678",
            "email": "contact@betaservices.com.br",
            "location": "São Paulo, Brazil",
            "website": "https://betaservices.com.br",
            "industry": "Consulting",
            "description": "Business consulting services",
            "source": "Google Maps"
        },
        {
            "business_name": "Gamma Solutions",
            "phone": "123456",
            "email": "invalid.email",
            "location": "Buenos Aires, Argentina",
            "website": "",
            "industry": "IT Services",
            "description": "",
            "source": "Instagram"
        },
        {
            "business_name": "Delta Inc.",
            "phone": "+56 9 8765 4321",
            "email": "sales@delta-corp.com",
            "location": "Santiago, Chile",
            "website": "http://delta-inc.com",
            "industry": "Manufacturing",
            "description": "Manufacturing solutions for industry",
            "source": "Paginas Amarillas"
        },
        {
            "business_name": "Test Company",
            "phone": "not-a-phone",
            "email": "test@test.com",
            "location": "Test Location",
            "website": "test.com",
            "industry": "Testing",
            "description": "This is a test company",
            "source": "Cylex"
        }
    ]
    
    with open(output_path, 'w') as f:
        json.dump(test_data, f, indent=2)

if __name__ == "__main__":
    main()
