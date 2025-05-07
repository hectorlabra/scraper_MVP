#!/usr/bin/env python3

"""
Script to show the corrected implementation of process_and_upload_data
This avoids DeduplicationProcessor references.
"""

def process_and_upload_data(df, config):
    """
    Process data through validation and upload it to Google Sheets.
    
    Args:
        df: DataFrame with data to process
        config: Configuration dictionary with validation and Google Sheets settings
        
    Returns:
        Tuple containing (processed DataFrame, upload results dictionary or None)
    """
    # Get processing configuration
    processing_config = config.get("processing", {})
    validation_config = processing_config.get("validation", {})
    dedup_config = processing_config.get("deduplication", {})
    google_sheets_config = config.get("google_sheets", {})
    
    logger.info(f"Starting data processing pipeline with {len(df)} records...")
    
    # Initial cleaning - remove rows with no business name
    if 'business_name' in df.columns:
        df = df[df['business_name'].notna()]
        logger.info(f"After removing records with no business name: {len(df)} records")
    
    # Deduplication functionality is now handled by ValidationProcessor
    dedup_config = processing_config.get("deduplication", {})
    if dedup_config.get("exact_match", True) or dedup_config.get("fuzzy_match", False):
        try:
            logger.info("Basic deduplication will be handled by ValidationProcessor")
            # Note: Advanced deduplication features from DeduplicationProcessor 
            # are not available. We'll use pandas built-in drop_duplicates instead.
            
            # Simple deduplication using pandas
            if 'business_name' in df.columns or 'email' in df.columns or 'phone' in df.columns:
                match_fields = [col for col in ['business_name', 'email', 'phone'] if col in df.columns]
                if match_fields:
                    original_len = len(df)
                    df = df.drop_duplicates(subset=match_fields, keep='first')
                    logger.info(f"After basic deduplication: {len(df)} records (removed {original_len - len(df)} duplicates)")
            
        except Exception as e:
            logger.error(f"Error during deduplication: {str(e)}", exc_info=True)
            logger.warning("Continuing with original data")
    
    # Run validation process if configured
    if validation_config.get("enable_email_validation", True) or validation_config.get("enable_phone_validation", True):
        try:
            # Initialize validation processor
            logger.info("Initializing ValidationProcessor...")
            validator = ValidationProcessor(df)
            
            # Run email validation if enabled
            if validation_config.get("enable_email_validation", True):
                logger.info("Validating email addresses...")
                df_with_emails = validator.validate_emails()
                valid_emails_count = df_with_emails['email_valid'].sum() if 'email_valid' in df_with_emails.columns else 0
                logger.info(f"Email validation complete. Valid emails: {valid_emails_count} ({valid_emails_count/len(df)*100:.1f}%)")
                
                # Update validator data with email validation results
                validator.data = df_with_emails
                df = df_with_emails
            
            # Run phone validation if enabled
            if validation_config.get("enable_phone_validation", True):
                logger.info("Validating phone numbers...")
                df_with_phones = validator.validate_phone_numbers()
                valid_phones_count = df_with_phones['phone_valid'].sum() if 'phone_valid' in df_with_phones.columns else 0
                logger.info(f"Phone validation complete. Valid phones: {valid_phones_count} ({valid_phones_count/len(df)*100:.1f}%)")
                
                # Update validator data with phone validation results
                validator.data = df_with_phones
                df = df_with_phones
            
            # Process the dataset (performs validation, scoring, and formatting)
            logger.info("Processing full dataset...")
            processed_df = validator.process()
            
            # Analyze validation results
            if 'is_valid' in processed_df.columns:
                valid_records = processed_df['is_valid'].sum()
                logger.info(f"Validation results:")
                logger.info(f"- Valid records: {valid_records} ({valid_records/len(processed_df)*100:.1f}%)")
                logger.info(f"- Invalid records: {len(processed_df) - valid_records}")
            
            # Calculate average quality score
            if 'validation_score' in processed_df.columns:
                avg_quality = processed_df['validation_score'].mean()
                logger.info(f"Average quality score: {avg_quality:.1f}%")
            
            df = processed_df
            
            # Apply minimum data quality threshold if specified
            min_quality = validation_config.get("min_data_quality", 0.0)
            if min_quality > 0:
                # Convert from 0-1 scale to 0-100 scale for filter_by_quality_score
                min_score = min_quality * 100
                logger.info(f"Filtering by quality score (min score: {min_score}%)...")
                filtered_df = validator.filter_by_quality_score(min_score=min_score)
                logger.info(f"After quality filtering: {len(filtered_df)} records")
                df = filtered_df
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}", exc_info=True)
            logger.warning("Continuing with unvalidated data")
    
    # Add timestamp column
    df['scrape_date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Upload to Google Sheets if enabled
    if google_sheets_config.get("enabled", False) and not df.empty:
        try:
            logger.info("Uploading processed data to Google Sheets...")
            upload_results = upload_to_google_sheets(df, google_sheets_config)
            logger.info(f"Upload complete: {upload_results}")
            return df, upload_results
        except Exception as e:
            logger.error(f"Error uploading to Google Sheets: {str(e)}", exc_info=True)
            logger.warning("Continuing without uploading to Google Sheets")
    
    return df, None
