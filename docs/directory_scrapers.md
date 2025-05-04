# Directory Scrapers Documentation

This documentation covers the implementation of directory scrapers for the LeadScraper LATAM project.

## Overview

The Directory Scrapers module is designed to collect business information from public business directories across Latin America. The following directories are currently supported:

1. **Páginas Amarillas** (Yellow Pages) - Available in multiple LATAM countries
2. **Cylex** - Business directory with presence across LATAM
3. **GuiaLocal** - Local business directory for LATAM countries

## Directory Scraper Base Class

All directory scrapers inherit from the `DirectoryScraper` abstract base class, which provides common functionality for scraping public business directories.

### Key Methods in Directory Scraper Base Class

- `build_search_url(query, location)` - Constructs the URL for searching the directory
- `parse_listing(html_element)` - Extracts business data from a single listing element
- `scrape(query, location)` - Core scraping method for the directory
- `get_listings()` - Retrieves listing elements from the current page
- `clean_results()` - Performs data cleaning on the scraped results

## Implemented Directory Scrapers

### 1. Páginas Amarillas Scraper

The `PaginasAmarillasScraper` extracts business information from Yellow Pages directories in Latin America.

#### Features

- Multi-country support (Mexico, Argentina, Chile, Colombia, Peru)
- Robust HTML parsing with multiple selector patterns
- Pagination handling
- Anti-detection measures
- CAPTCHA detection

#### Usage Example

```python
from scrapers.paginas_amarillas_scraper import PaginasAmarillasScraper

scraper = PaginasAmarillasScraper(country="mx", max_results=50)
results = scraper.scrape("restaurantes", "CDMX")
print(f"Found {len(results)} businesses")
```

### 2. Cylex Scraper

The `CylexScraper` extracts business information from Cylex directories in Latin America.

#### Features

- Multi-country support (Mexico, Argentina, Chile, Colombia, Peru)
- Handles Cylex's specific HTML structure
- Extracts comprehensive business information
- Pagination handling
- Anti-detection measures

#### Usage Example

```python
from scrapers.cylex_scraper import CylexScraper

scraper = CylexScraper(country="mx", max_results=50)
results = scraper.scrape("hoteles", "Cancun")
print(f"Found {len(results)} businesses")
```

### 3. GuiaLocal Scraper

The `GuiaLocalScraper` extracts business information from GuiaLocal directories in Latin America.

#### Features

- Multi-country support (Mexico, Argentina, Chile, Colombia, Peru)
- Handles GuiaLocal's specific HTML structure
- Extracts comprehensive business information
- Pagination handling
- Anti-detection measures

#### Usage Example

```python
from scrapers.guialocal_scraper import GuiaLocalScraper

scraper = GuiaLocalScraper(country="mx", max_results=50)
results = scraper.scrape("dentistas", "Guadalajara")
print(f"Found {len(results)} businesses")
```

## Command-Line Interface

Each directory scraper comes with a dedicated CLI script for easy standalone use:

- `scripts/paginas_amarillas_cli.py`
- `scripts/cylex_cli.py`
- `scripts/guialocal_cli.py`

Additionally, there's a combined demo script that demonstrates using all three scrapers together:

- `scripts/demo_directory_scrapers.py`

### CLI Usage Examples

1. Páginas Amarillas CLI:

```
python scripts/paginas_amarillas_cli.py --query "restaurantes" --location "CDMX" --country "mx" --max-results 50 --headless
```

2. Cylex CLI:

```
python scripts/cylex_cli.py --query "hoteles" --location "Cancun" --country "mx" --max-results 50 --headless
```

3. GuiaLocal CLI:

```
python scripts/guialocal_cli.py --query "dentistas" --location "Guadalajara" --country "mx" --max-results 50 --headless
```

4. Combined Demo:

```
python scripts/demo_directory_scrapers.py --query "cafeterias" --location "CDMX" --directory all --country "mx" --max-results 30 --headless
```

## Data Output Format

All directory scrapers produce data in a consistent JSON format with the following fields:

```json
{
  "source": "paginas_amarillas_mx",
  "scrape_date": "2025-05-04",
  "name": "Business Name",
  "address": "Business Address",
  "phone": "Phone Number",
  "website": "Website URL",
  "email": "Contact Email",
  "category": "Business Category",
  "description": "Business Description",
  "rating": 4.5,
  "review_count": 25,
  "social_media": {}
}
```

Not all fields may be available for every business. Fields will be `null` if the data could not be extracted.

## Anti-Detection Measures

Directory scrapers implement several anti-detection measures:

- Random user-agent rotation
- Variable delays between requests
- Human-like navigation patterns
- CAPTCHA detection
- Configurable request delays

## Error Handling

The scrapers are designed to be resilient against common issues:

- Missing HTML elements
- CAPTCHA challenges
- Network failures
- Structure changes in the directories

Extensive logging is implemented to track the scraping process and troubleshoot any issues.
