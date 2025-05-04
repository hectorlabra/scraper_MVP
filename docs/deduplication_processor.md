# DeduplicationProcessor

The `DeduplicationProcessor` is a specialized class for identifying and removing duplicate leads from scraped data with advanced exact and fuzzy matching capabilities.

## Features

- **Exact Matching**: Identify duplicates based on exact matches in specified fields (e.g., email, phone)
- **Fuzzy Matching**: Find similar business names using string similarity algorithms
- **Configurable Rules**: Combine various matching strategies with AND/OR operators
- **Intelligent Record Preservation**: Keep the most complete record when duplicates are found
- **Detailed Statistics**: Track deduplication metrics and results

## Installation

The `DeduplicationProcessor` requires the following dependencies:

```
pandas
fuzzywuzzy (optional, for fuzzy matching)
python-Levenshtein (optional, for improved fuzzy matching performance)
```

Install the optional dependencies with:

```bash
pip install fuzzywuzzy python-Levenshtein
```

## Basic Usage

```python
import pandas as pd
from processing import DeduplicationProcessor

# Load your data
data = pd.read_csv('leads.csv')

# Initialize the processor
processor = DeduplicationProcessor(data)

# Perform deduplication
# Option 1: Exact matching on specific fields
deduplicated_data = processor.deduplicate_exact(
    subset=['email', 'phone'],
    keep_most_complete=True
)

# Option 2: Fuzzy matching on business names
deduplicated_data = processor.deduplicate_fuzzy(
    column='business_name',
    threshold=85,  # Similarity threshold (0-100)
    additional_exact_columns=['city']  # Optional exact match requirements
)

# Option 3: Configurable rules combining multiple strategies
rules = [
    {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
    {'type': 'exact', 'columns': ['phone'], 'operator': 'OR'},
    {'type': 'fuzzy', 'column': 'business_name', 'threshold': 80}
]
deduplicated_data = processor.deduplicate(rules=rules)

# Get deduplication stats
stats = processor.get_deduplication_stats()
print(f"Removed {stats['removed_count']} duplicates ({stats['removed_percentage']}%)")

# Save the results
processor.to_csv('deduplicated_leads.csv', index=False)
```

## Advanced Usage

### Exact Matching Deduplication

The `deduplicate_exact` method identifies duplicates based on exact matches in specified columns.

```python
processor.deduplicate_exact(
    subset=['email', 'phone', 'business_name'],  # Fields to check for exact matches
    keep_most_complete=True                      # Whether to keep the most complete record
)
```

Parameters:

- `subset`: List of column names to check for duplicates
- `keep_most_complete`: If True, keeps the record with the most non-null values when duplicates are found. If False, keeps the first occurrence.

### Fuzzy Matching Deduplication

The `deduplicate_fuzzy` method identifies duplicates based on string similarity.

```python
processor.deduplicate_fuzzy(
    column='business_name',              # Column to apply fuzzy matching to
    threshold=85,                        # Similarity threshold (0-100)
    keep_most_complete=True,             # Whether to keep the most complete record
    additional_exact_columns=['city']    # Additional columns that must match exactly
)
```

Parameters:

- `column`: Column name to apply fuzzy matching to (usually business_name)
- `threshold`: Similarity threshold (0-100) - higher values require closer matches
- `keep_most_complete`: If True, keeps the record with the most non-null values
- `additional_exact_columns`: Optional list of columns that must match exactly (in addition to fuzzy matching)

### Configurable Rules Interface

The `deduplicate` method provides a flexible interface for combining different deduplication strategies.

```python
rules = [
    {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
    {'type': 'exact', 'columns': ['phone'], 'operator': 'OR'},
    {'type': 'fuzzy', 'column': 'business_name', 'threshold': 80, 'additional_exact': ['city']}
]

processor.deduplicate(rules=rules)
```

Rule parameters:

- `type`: 'exact' or 'fuzzy'
- `columns` or `column`: List of columns for exact matching, or single column for fuzzy
- `threshold`: For fuzzy matching (default: 80)
- `keep_most_complete`: Whether to keep the most complete record (default: True)
- `operator`: 'AND' or 'OR' to define how to combine with the next rule (ignored for the last rule)
- `additional_exact`: List of columns that must match exactly (for fuzzy rules)

If no rules are provided, a default rule set will be applied, which looks for exact matches on ['email', 'phone'] or fuzzy matches on 'business_name' with a threshold of 80.

### Utility Methods

```python
# Save current state to allow multiple deduplication attempts
processor.save_original()

# Reset to original data
processor.reset()

# Get deduplication statistics
stats = processor.get_deduplication_stats()

# Get the deduplicated data as a DataFrame
df = processor.get_data()

# Export to CSV
processor.to_csv('deduplicated_leads.csv', index=False)

# Convert to list of dictionaries
leads_list = processor.to_dict_list()
```

## Example Scenarios

### Finding Exact Email Duplicates

```python
processor.deduplicate_exact(subset=['email'])
```

### Finding Companies with Similar Names in the Same City

```python
processor.deduplicate_fuzzy(
    column='business_name',
    threshold=85,
    additional_exact_columns=['city']
)
```

### Complex Deduplication Strategy

"Consider records duplicates if they have the same email OR phone OR (similar business name AND same city)"

```python
rules = [
    {'type': 'exact', 'columns': ['email'], 'operator': 'OR'},
    {'type': 'exact', 'columns': ['phone'], 'operator': 'OR'},
    {'type': 'fuzzy', 'column': 'business_name', 'threshold': 85, 'additional_exact': ['city']}
]

processor.deduplicate(rules=rules)
```

## Performance Considerations

- Fuzzy matching can be computationally expensive for large datasets
- For improved performance with large datasets, consider:
  - Filtering data before deduplication
  - Using exact columns to narrow down comparison groups
  - Increasing the similarity threshold to reduce potential matches
  - Using the python-Levenshtein package for faster fuzzy matching

## Logging

The DeduplicationProcessor logs its operations using the Python logging module. To capture these logs:

```python
import logging
logging.basicConfig(level=logging.INFO)
```
