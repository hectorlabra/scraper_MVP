#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script for ValidationProcessor functionality.

This script demonstrates the use of the ValidationProcessor class for:
1. Validating and formatting emails
2. Validating and formatting phone numbers for LATAM countries
3. Calculating data quality scores
4. Flagging suspicious data
5. Processing entire DataFrames
"""

import os
import sys
import pandas as pd
import logging

# Add project root to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from processing import ValidationProcessor

def main():
    """Main demonstration function"""
    print("\n==== ValidationProcessor Demo ====\n")
    
    # Create sample data
    sample_data = {
        'business_name': [
            'Alpha Technologies', 
            'Beta Services', 
            'Gamma Solutions', 
            'Test Company',
            'Delta Inc.'
        ],
        'phone': [
            '+52 55 1234 5678',       # Mexico
            '+55 11 91234-5678',      # Brazil
            '123456',                 # Invalid - too short
            '1234567890',             # Generic format (likely invalid)
            '+56 9 8765 4321'         # Chile
        ],
        'email': [
            'info@alphatech.com',     
            'contact@betaservices.com',
            'invalid.email',          # Invalid format
            'test@test.com',          # Suspicious
            'support@delta.com'
        ],
        'location': [
            'Mexico City, Mexico',
            'São Paulo, Brazil',
            'Buenos Aires, Argentina', 
            '',                         # Empty
            'Santiago, Chile'
        ],
        'website': [
            'https://www.alphatech.com',
            'https://betaservices.com',
            '',                        # Empty
            'http://test-company.com',
            'https://delta-inc.com'
        ]
    }
    
    df = pd.DataFrame(sample_data)
    
    print("Sample Data:")
    print(df)
    print("\n")
    
    # Initialize ValidationProcessor
    processor = ValidationProcessor(df)
    
    # Demonstrate individual email validation
    print("--- Email Validation ---")
    emails_to_test = [
        'valid.email@example.com',
        'invalid.email',
        'user.name+tag@example.co.uk',
        '@missing-username.com'
    ]
    
    for email in emails_to_test:
        is_valid = processor.validate_email(email)
        formatted = processor.format_email(email) if is_valid else "N/A"
        print(f"Email: {email}")
        print(f"  Valid: {is_valid}")
        print(f"  Formatted: {formatted}")
    print("\n")
    
    # Demonstrate phone validation and formatting
    print("--- Phone Number Validation ---")
    phones_to_test = [
        ('+52 55 1234 5678', 'MX'),   # Mexico
        ('5511912345678', 'BR'),      # Brazil
        ('+54 9 11 1234-5678', 'AR'), # Argentina
        ('123456', None),             # Invalid
        ('+56 9 8765 4321', 'CL')     # Chile
    ]
    
    for phone, country in phones_to_test:
        is_valid = processor.validate_phone_number(phone, country)
        formatted = processor.format_phone_number(phone, country) if is_valid else "N/A"
        country_str = country if country else "Auto-detect"
        print(f"Phone: {phone} (Country: {country_str})")
        print(f"  Valid: {is_valid}")
        print(f"  Formatted: {formatted}")
    print("\n")
    
    # Demonstrate quality scoring
    print("--- Data Quality Scoring ---")
    records_to_score = [
        # Complete record
        {
            'business_name': 'Alpha Tech',
            'phone': '+52 55 1234 5678',
            'email': 'info@alphatech.com',
            'location': 'Mexico City, Mexico',
            'website': 'https://alphatech.com'
        },
        # Partial record
        {
            'business_name': 'Beta Services',
            'phone': '+55 11 91234-5678',
            'email': None,
            'location': 'São Paulo, Brazil',
            'website': None
        },
        # Poor record
        {
            'business_name': 'Test Company',
            'phone': '123456',  # Invalid
            'email': 'invalid.email',  # Invalid
            'location': '',
            'website': None
        }
    ]
    
    for i, record in enumerate(records_to_score):
        score = processor.calculate_data_quality_score(record)
        print(f"Record {i+1}:")
        for key, value in record.items():
            print(f"  {key}: {value if value else 'N/A'}")
        print(f"  Quality Score: {score:.2f}%")
    print("\n")
    
    # Demonstrate suspicious data flagging
    print("--- Suspicious Data Flagging ---")
    suspicious_records = [
        # Generic test record
        {
            'business_name': 'Test Company',
            'phone': '1234567890',
            'email': 'test@test.com'
        },
        # Repeated digits in phone
        {
            'business_name': 'Alpha Tech',
            'phone': '5555555555',
            'email': 'info@alphatech.com'
        },
        # Disposable email
        {
            'business_name': 'Beta Services',
            'phone': '+55 11 91234-5678',
            'email': 'contact@mailinator.com'
        }
    ]
    
    for i, record in enumerate(suspicious_records):
        flags = processor.flag_suspicious_data(record)
        print(f"Record {i+1}:")
        for key, value in record.items():
            print(f"  {key}: {value}")
        if flags:
            print("  Suspicious flags:")
            for field, reason in flags.items():
                print(f"    - {field}: {reason}")
        else:
            print("  No suspicious flags")
    print("\n")
    
    # Process the entire DataFrame
    print("--- Processing Complete DataFrame ---")
    result_df = processor.process()
    
    # Display the results
    print("Processed DataFrame (showing validation columns):")
    columns_to_display = ['business_name', 'email', 'phone', 'email_valid', 'phone_valid', 'validation_score', 'is_valid']
    print(result_df[columns_to_display])
    print("\n")
    
    # Summary statistics
    valid_records = sum(result_df['is_valid'])
    valid_emails = sum(result_df['email_valid'])
    valid_phones = sum(result_df['phone_valid'])
    
    print("Summary Statistics:")
    print(f"  Total Records: {len(result_df)}")
    print(f"  Valid Records: {valid_records} ({valid_records/len(result_df)*100:.2f}%)")
    print(f"  Valid Emails: {valid_emails} ({valid_emails/len(result_df)*100:.2f}%)")
    print(f"  Valid Phones: {valid_phones} ({valid_phones/len(result_df)*100:.2f}%)")
    print(f"  Average Quality Score: {result_df['validation_score'].mean():.2f}%")
    print("\n")
    
    print("==== Demo Complete ====")

if __name__ == "__main__":
    main()
