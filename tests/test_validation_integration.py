#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test for ValidationProcessor methods used in main.py

This script validates that the methods used in main.py for integrating
the ValidationProcessor class are working correctly:
- validate_emails()
- validate_phone_numbers()
- filter_by_quality_score()
"""

import os
import sys
import pandas as pd
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the class we need to test
from processing.data_processor import ValidationProcessor

def run_integration_test():
    """Run integration tests for ValidationProcessor in main.py flow"""
    print("\n==== ValidationProcessor Integration Test ====\n")
    
    # Create sample test data similar to what we'd get from scrapers
    test_data = {
        'business_name': [
            'Alpha Technologies', 
            'Beta Services', 
            'Gamma Solutions', 
            'Delta Inc.',
            'Test Company'
        ],
        'phone': [
            '+52 55 1234 5678',       # Valid Mexico
            '+55 11 91234-5678',      # Valid Brazil
            '123456',                 # Invalid - too short
            '+56 9 8765 4321',        # Valid Chile
            'not-a-phone'             # Invalid - not a number
        ],
        'email': [
            'info@alphatech.com',     # Valid
            'contact@betaservices.com.br', # Valid
            'invalid.email',          # Invalid
            'sales@delta-corp.com',   # Valid
            'test@test.com'           # Valid but suspicious
        ],
        'location': [
            'Mexico City, Mexico',
            'São Paulo, Brazil',
            'Buenos Aires, Argentina',
            'Santiago, Chile',
            'Test Location'
        ],
        'website': [
            'https://www.alphatech.com',
            'https://betaservices.com.br',
            '',
            'http://delta-inc.com',
            'test.com'                # Missing http://
        ]
    }
    
    # Create a DataFrame
    df = pd.DataFrame(test_data)
    
    print("Original Data:")
    print(df[['business_name', 'phone', 'email']])
    print("\n")
    
    # Initialize ValidationProcessor with test data
    processor = ValidationProcessor(df)
    
    # Test 1: Validate Emails
    print("=== Testing validate_emails() ===")
    email_validated_df = processor.validate_emails()
    valid_email_count = email_validated_df['email_valid'].sum()
    print(f"Valid emails: {valid_email_count} out of {len(email_validated_df)}")
    print("Email validation columns:", [col for col in email_validated_df.columns if 'email' in col])
    print(email_validated_df[['business_name', 'email', 'email_valid']])
    print("\n")
    
    # Test 2: Validate Phone Numbers
    print("=== Testing validate_phone_numbers() ===")
    phone_validated_df = processor.validate_phone_numbers()
    valid_phone_count = phone_validated_df['phone_valid'].sum()
    print(f"Valid phones: {valid_phone_count} out of {len(phone_validated_df)}")
    print("Phone validation columns:", [col for col in phone_validated_df.columns if 'phone' in col])
    print(phone_validated_df[['business_name', 'phone', 'phone_valid']])
    print("\n")
    
    # Test 3: Apply Both Validations (Simulating main.py flow)
    print("=== Testing Validation Chain (main.py simulation) ===")
    # First, validate emails
    processor.data = processor.validate_emails()
    # Then, validate phones
    processor.data = processor.validate_phone_numbers()
    
    # Verify both validation columns exist
    both_validated_df = processor.data
    print("After both validations, columns:", [col for col in both_validated_df.columns if 'valid' in col])
    print(both_validated_df[['business_name', 'email_valid', 'phone_valid']])
    print("\n")
    
    # Test 4: Filter by Quality Score
    print("=== Testing filter_by_quality_score() ===")
    # First, calculate quality scores
    processed_df = processor.process()
    processor.data = processed_df  # Replace with fully processed data, including scores
    
    # Filter with various thresholds
    high_quality_df = processor.filter_by_quality_score(min_score=80)
    medium_quality_df = processor.filter_by_quality_score(min_score=50)
    low_quality_df = processor.filter_by_quality_score(min_score=20)
    
    print(f"Records with quality ≥ 80%: {len(high_quality_df)}")
    print(f"Records with quality ≥ 50%: {len(medium_quality_df)}")
    print(f"Records with quality ≥ 20%: {len(low_quality_df)}")
    
    # Display records with scores
    print("\nQuality scores for all records:")
    for idx, row in processed_df.iterrows():
        print(f"{row['business_name']}: {row['validation_score']}%")
    
    # Test 5: Verify email/phone validation aligns with is_valid flag
    print("\n=== Testing Validation Consistency ===")
    validation_consistent = True
    for idx, row in processed_df.iterrows():
        # Check if email_valid and phone_valid flags are consistent with is_valid
        if row.get('email') and row.get('phone'):
            # If both are provided, at least one should be valid for is_valid=True
            expected_is_valid = row['email_valid'] or row['phone_valid']
            if row['is_valid'] != expected_is_valid:
                validation_consistent = False
                print(f"Inconsistency for {row['business_name']}: is_valid={row['is_valid']}, email_valid={row['email_valid']}, phone_valid={row['phone_valid']}")
    
    print(f"Validation consistency check: {'PASSED' if validation_consistent else 'FAILED'}")
    
    print("\nIntegration test completed.")
    return True

if __name__ == "__main__":
    run_integration_test()
