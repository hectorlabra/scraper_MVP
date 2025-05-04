# Data Validation Processor

The ValidationProcessor class extends the ScraperMVP data processing capabilities by providing robust validation and standardization for contact data, especially emails and phone numbers, with specialized support for LATAM country formats.

## Features

- **Email Validation and Formatting**: Validate email addresses using comprehensive regex patterns that support various email formats, subdomains, and international domains. Format valid emails by stripping whitespace and standardizing case.

- **Phone Number Validation for LATAM Countries**: Specialized validation for phone numbers from Latin American countries, with support for country-specific formatting standards and automatic country detection.

- **Data Quality Scoring**: Calculate quality scores for records based on the completeness and validity of key fields, with customizable weighting for different attributes.

- **Suspicious Data Flagging**: Identify potentially suspicious or placeholder data in records, such as test emails, generic company names, or improbable phone patterns.

- **Comprehensive Record Validation Pipeline**: Process entire datasets to standardize formats, validate fields, calculate quality metrics, and flag suspicious entries.

## Usage

### Basic Usage

```python
import pandas as pd
from processing import ValidationProcessor

# Load your data
df = pd.DataFrame({
    'business_name': ['Alpha Tech', 'Beta Services'],
    'phone': ['+52 55 1234 5678', '123456'],
    'email': ['info@alphatech.com', 'invalid.email']
})

# Initialize processor
processor = ValidationProcessor(df)

# Process the entire dataset
result_df = processor.process()

# The result_df now contains additional columns:
# - email_valid: Boolean indicating valid email
# - phone_valid: Boolean indicating valid phone
# - validation_score: Data quality score (0-100)
# - validation_flags: Dictionary of suspicious data flags
# - is_valid: Overall validity of the record
```

### Individual Field Validation

```python
# Validate individual emails
processor.validate_email('user@example.com')  # True
processor.validate_email('invalid')           # False

# Format an email
processor.format_email(' User@Example.COM ')  # 'user@example.com'

# Validate phone numbers
processor.validate_phone_number('+52 55 1234 5678', 'MX')  # True for Mexico
processor.validate_phone_number('123456')                  # False

# Format phone numbers
processor.format_phone_number('5215512345678', 'MX')       # '+52 55 1234 5678'
```

### Data Quality Scoring

```python
# Calculate quality score for a record
record = {
    'business_name': 'Alpha Tech',
    'phone': '+52 55 1234 5678',
    'email': 'info@alphatech.com',
    'location': 'Mexico City'
}

# Using default weights
score = processor.calculate_data_quality_score(record)  # Returns a score from 0-100

# Using custom weights
custom_weights = {
    'business_name': 20,
    'phone': 35,
    'email': 35,
    'location': 10
}
score = processor.calculate_data_quality_score(record, custom_weights)
```

### Suspicious Data Flagging

```python
# Flag suspicious data
record = {
    'business_name': 'Test Company',
    'phone': '1234567890',  # Sequential, potentially fake
    'email': 'test@test.com'  # Generic test email
}

flags = processor.flag_suspicious_data(record)
# Returns: {'phone': 'Suspicious pattern: ^12345', 'email': 'Suspicious pattern: ^test.*@.*\\.com$'}
```

## Supported LATAM Countries

The ValidationProcessor provides specialized support for phone number validation and formatting in these Latin American countries:

| Country            | Code | Example Format     |
| ------------------ | ---- | ------------------ |
| Argentina          | AR   | +54 9 11 1234-5678 |
| Bolivia            | BO   | +591 X XXXXXXX     |
| Brazil             | BR   | +55 11 91234-5678  |
| Chile              | CL   | +56 9 XXXX XXXX    |
| Colombia           | CO   | +57 XXX XXX XXXX   |
| Costa Rica         | CR   | +506 XXXX XXXX     |
| Cuba               | CU   | +53 X XXX XXXX     |
| Dominican Republic | DO   | +1 XXX XXX XXXX    |
| Ecuador            | EC   | +593 X XXX XXXX    |
| El Salvador        | SV   | +503 XXXX XXXX     |
| Guatemala          | GT   | +502 XXXX XXXX     |
| Honduras           | HN   | +504 XXXX XXXX     |
| Mexico             | MX   | +52 55 1234 5678   |
| Nicaragua          | NI   | +505 XXXX XXXX     |
| Panama             | PA   | +507 XXXX XXXX     |
| Paraguay           | PY   | +595 XX XXX XXX    |
| Peru               | PE   | +51 XXX XXX XXX    |
| Puerto Rico        | PR   | +1 XXX XXX XXXX    |
| Uruguay            | UY   | +598 X XXX XXXX    |
| Venezuela          | VE   | +58 XXX XXX XXXX   |

## Customization

### Email Validation Patterns

The email validation uses a comprehensive regex pattern that validates standard email formats including:

- Username with dots, pluses, dashes, underscores
- Domain name with subdomains
- TLDs of various lengths
- IP address domains

### Suspicious Data Patterns

The processor includes built-in patterns for detecting suspicious data:

**Suspicious Emails:**

- test@example.com
- anything@test.com
- info@example.com (generic)
- admin@example.com (generic)
- Very short usernames (a@example.com)
- Disposable email domains (mailinator.com, yopmail.com, etc.)

**Suspicious Phone Numbers:**

- Repeated digits (111111, 2222222)
- Sequential digits starting pattern (12345...)
- Multiple leading zeros

## Installation

The ValidationProcessor requires the following packages:

- pandas
- phonenumbers
- pycountry
- fuzzywuzzy (optional, for fuzzy matching)

Make sure these are installed in your environment:

```bash
pip install pandas phonenumbers pycountry fuzzywuzzy python-Levenshtein
```
