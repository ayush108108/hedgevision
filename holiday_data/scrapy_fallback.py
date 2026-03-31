
# Create an alternative Scrapy-based scraper

scrapy_scraper_script = '''"""
Exchange Holiday Calendar Scraper using Scrapy
================================================
Alternative implementation using Scrapy framework for more robust scraping.

Requirements:
    pip install scrapy pandas

Usage:
    scrapy runspider exchange_holiday_scrapy.py -o holidays.json
"""

import scrapy
from scrapy.crawler import CrawlerProcess
from datetime import datetime
import json


class ExchangeHolidaySpider(scrapy.Spider):
    """Scrapy spider for scraping exchange holidays"""
    
    name = 'exchange_holidays'
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 2,
        'RETRY_TIMES': 3,
        'FEEDS': {
            'exchange_holidays_scrapy.json': {'format': 'json', 'overwrite': True},
        }
    }
    
    # Define all URLs to scrape
    start_urls = [
        'https://www.nyse.com/markets/hours-calendars',  # NYSE
        'https://www.nseindia.com/resources/exchange-communication-holidays',  # NSE
        'https://www.jpx.co.jp/english/corporate/about-jpx/calendar/index.html',  # Japan
        'https://english.sse.com.cn/start/trading/schedule/',  # China
        # Add fallback URLs as needed
    ]
    
    def parse(self, response):
        """Parse the response and extract holiday data"""
        
        # Determine which exchange based on URL
        url = response.url
        
        if 'nyse.com' in url or 'nasdaq.com' in url:
            yield from self.parse_nyse(response)
        elif 'nseindia.com' in url or 'zerodha.com' in url:
            yield from self.parse_nse(response)
        elif 'bseindia.com' in url:
            yield from self.parse_bse(response)
        elif 'jpx.co.jp' in url:
            yield from self.parse_japan(response)
        elif 'sse.com.cn' in url or 'szse.cn' in url:
            yield from self.parse_china(response)
        elif 'sifma.org' in url or 'cmegroup.com' in url:
            yield from self.parse_forex(response)
    
    def parse_nyse(self, response):
        """Parse NYSE holiday table"""
        self.logger.info(f"Parsing NYSE holidays from {response.url}")
        
        # Extract table rows
        rows = response.css('table tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.css('td::text').getall()
            if len(cols) >= 2:
                yield {
                    'exchange': 'NYSE',
                    'holiday': cols[0].strip(),
                    'date': cols[1].strip(),
                    'year': '2025',
                    'status': 'Closed',
                    'scraped_at': datetime.now().isoformat()
                }
    
    def parse_nse(self, response):
        """Parse NSE holiday table"""
        self.logger.info(f"Parsing NSE holidays from {response.url}")
        
        # Find all tables and parse the equity segment table
        tables = response.css('table')
        
        for table in tables:
            rows = table.css('tr')[1:]  # Skip header
            
            for row in rows:
                cols = row.css('td::text').getall()
                if len(cols) >= 4:
                    yield {
                        'exchange': 'NSE',
                        'date': cols[1].strip(),
                        'day': cols[2].strip(),
                        'holiday': cols[3].strip(),
                        'year': '2025',
                        'scraped_at': datetime.now().isoformat()
                    }
    
    def parse_bse(self, response):
        """Parse BSE holiday table"""
        self.logger.info(f"Parsing BSE holidays from {response.url}")
        
        rows = response.css('table tr')[1:]
        
        for row in rows:
            cols = row.css('td::text').getall()
            if len(cols) >= 4:
                yield {
                    'exchange': 'BSE',
                    'date': cols[1].strip(),
                    'day': cols[2].strip(),
                    'holiday': cols[3].strip(),
                    'year': '2025',
                    'scraped_at': datetime.now().isoformat()
                }
    
    def parse_japan(self, response):
        """Parse Japan market holidays"""
        self.logger.info(f"Parsing Japan holidays from {response.url}")
        
        rows = response.css('table tr')[1:]
        
        for row in rows:
            cols = row.css('td::text').getall()
            if len(cols) >= 2:
                yield {
                    'exchange': 'FOREX_JAPAN',
                    'date': cols[0].strip(),
                    'holiday': cols[1].strip(),
                    'year': '2025',
                    'market': 'Forex - Japan',
                    'scraped_at': datetime.now().isoformat()
                }
    
    def parse_china(self, response):
        """Parse China market holidays"""
        self.logger.info(f"Parsing China holidays from {response.url}")
        
        rows = response.css('table tr')[1:]
        
        for row in rows:
            cols = row.css('td::text').getall()
            if len(cols) >= 2:
                yield {
                    'exchange': 'FOREX_CHINA',
                    'holiday': cols[0].strip(),
                    'date': cols[1].strip(),
                    'year': '2025',
                    'market': 'Forex - China',
                    'scraped_at': datetime.now().isoformat()
                }
    
    def parse_forex(self, response):
        """Parse Forex market holidays (SIFMA)"""
        self.logger.info(f"Parsing Forex holidays from {response.url}")
        
        rows = response.css('table tr')[1:]
        
        for row in rows:
            cols = row.css('td::text').getall()
            if len(cols) >= 2:
                yield {
                    'exchange': 'FOREX_US',
                    'holiday': cols[0].strip(),
                    'date': cols[1].strip(),
                    'year': '2025',
                    'market': 'Forex - United States',
                    'scraped_at': datetime.now().isoformat()
                }


def run_spider():
    """Run the Scrapy spider"""
    process = CrawlerProcess()
    process.crawl(ExchangeHolidaySpider)
    process.start()


if __name__ == "__main__":
    run_spider()
'''

# Create a utility script for data validation and cleaning
utility_script = '''"""
Holiday Data Utilities
======================
Helper functions for validating, cleaning, and formatting holiday data.

Usage:
    from holiday_utils import validate_holidays, clean_date_format
"""

import pandas as pd
from datetime import datetime
import re


def parse_date(date_str: str) -> str:
    """
    Parse various date formats to standard YYYY-MM-DD format
    
    Args:
        date_str: Date string in various formats
    
    Returns:
        Standardized date string in YYYY-MM-DD format
    """
    # Remove extra whitespace
    date_str = date_str.strip()
    
    # Try common date formats
    date_formats = [
        '%B %d, %Y',      # January 1, 2025
        '%d-%b-%Y',       # 01-Jan-2025
        '%d-%B-%Y',       # 01-January-2025
        '%m/%d/%Y',       # 01/01/2025
        '%Y-%m-%d',       # 2025-01-01
        '%d %B %Y',       # 01 January 2025
        '%b %d, %Y',      # Jan 1, 2025
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # If no format matches, return original
    return date_str


def validate_holidays(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean holiday data
    
    Args:
        df: DataFrame with holiday data
    
    Returns:
        Cleaned DataFrame
    """
    # Remove rows with missing critical data
    df = df.dropna(subset=['holiday', 'date'])
    
    # Standardize date format
    if 'date' in df.columns:
        df['date_standardized'] = df['date'].apply(parse_date)
    
    # Remove duplicates
    df = df.drop_duplicates(subset=['exchange', 'holiday', 'date'])
    
    # Sort by date
    df = df.sort_values('date')
    
    return df


def export_calendar_format(df: pd.DataFrame, filename: str = 'calendar.ics'):
    """
    Export holidays to iCalendar (.ics) format for calendar applications
    
    Args:
        df: DataFrame with holiday data
        filename: Output filename
    """
    with open(filename, 'w') as f:
        f.write("BEGIN:VCALENDAR\\n")
        f.write("VERSION:2.0\\n")
        f.write("PRODID:-//Exchange Holiday Calendar//EN\\n")
        
        for _, row in df.iterrows():
            # Parse date
            date_str = row.get('date_standardized', row['date'])
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_ical = date_obj.strftime('%Y%m%d')
                
                f.write("BEGIN:VEVENT\\n")
                f.write(f"DTSTART;VALUE=DATE:{date_ical}\\n")
                f.write(f"DTEND;VALUE=DATE:{date_ical}\\n")
                f.write(f"SUMMARY:{row['exchange']} - {row['holiday']}\\n")
                f.write(f"DESCRIPTION:Trading holiday for {row['exchange']}\\n")
                f.write("END:VEVENT\\n")
            except:
                continue
        
        f.write("END:VCALENDAR\\n")


def compare_exchanges(df: pd.DataFrame):
    """
    Compare holidays across different exchanges
    
    Args:
        df: DataFrame with holiday data from multiple exchanges
    
    Returns:
        DataFrame with comparison
    """
    # Group by date and see which exchanges are closed
    comparison = df.groupby('date').agg({
        'exchange': lambda x: ', '.join(sorted(set(x))),
        'holiday': lambda x: ' | '.join(sorted(set(x)))
    }).reset_index()
    
    return comparison


def generate_trading_days(df: pd.DataFrame, year: int = 2025) -> pd.DataFrame:
    """
    Generate a full calendar of trading days vs holidays
    
    Args:
        df: DataFrame with holiday data
        year: Year to generate calendar for
    
    Returns:
        DataFrame with all days marked as trading or holiday
    """
    # Create date range for entire year
    date_range = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31', freq='D')
    
    # Create base calendar
    calendar = pd.DataFrame({'date': date_range})
    calendar['day_of_week'] = calendar['date'].dt.day_name()
    calendar['is_weekend'] = calendar['date'].dt.dayofweek >= 5
    
    # Mark holidays for each exchange
    for exchange in df['exchange'].unique():
        exchange_holidays = df[df['exchange'] == exchange]['date_standardized'].tolist()
        calendar[f'{exchange}_holiday'] = calendar['date'].astype(str).isin(exchange_holidays)
    
    return calendar


def main():
    """Example usage"""
    # Load scraped data
    df = pd.read_csv('exchange_holidays.csv')
    
    # Validate and clean
    df = validate_holidays(df)
    
    # Save cleaned data
    df.to_csv('exchange_holidays_cleaned.csv', index=False)
    
    # Export to calendar format
    export_calendar_format(df, 'exchange_holidays.ics')
    
    # Generate comparison
    comparison = compare_exchanges(df)
    comparison.to_csv('holiday_comparison.csv', index=False)
    
    # Generate full trading calendar
    trading_calendar = generate_trading_days(df)
    trading_calendar.to_csv('trading_calendar_2025.csv', index=False)
    
    print("Data processing complete!")


if __name__ == "__main__":
    main()
'''

# Create requirements.txt
requirements = '''# Required packages for Exchange Holiday Scraper

# Core scraping libraries
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0

# Alternative: Scrapy framework
scrapy>=2.11.0

# Data processing
pandas>=2.0.0

# Optional: For advanced features
python-dateutil>=2.8.0
pytz>=2023.3
'''

# Create README
readme = '''# Exchange Holiday Calendar Scraper

Automated scraper to fetch trading holiday calendars from major stock exchanges and forex markets.

## Supported Exchanges

- **NYSE** (New York Stock Exchange) - USA
- **BSE** (Bombay Stock Exchange) - India
- **NSE** (National Stock Exchange) - India
- **Forex Markets**: US, UK, Japan, China, India

## Features

- ✅ Scrapes official exchange websites
- ✅ Fallback URLs for reliability
- ✅ Multiple export formats (CSV, JSON, iCalendar)
- ✅ Data validation and cleaning
- ✅ Retry mechanism with exponential backoff
- ✅ User-Agent rotation
- ✅ Comprehensive error handling

## Installation

```bash
# Install required packages
pip install -r requirements.txt
```

## Usage

### Method 1: BeautifulSoup (Recommended for beginners)

```bash
python exchange_holiday_scraper.py
```

### Method 2: Scrapy (For advanced users)

```bash
scrapy runspider exchange_holiday_scrapy.py -o holidays.json
```

### Data Processing

```bash
python holiday_utils.py
```

## Output Files

- `exchange_holidays.csv` - All holidays in CSV format
- `exchange_holidays.json` - All holidays in JSON format
- `{exchange}_holidays_2025.csv` - Individual exchange files
- `exchange_holidays.ics` - iCalendar format for import
- `holiday_comparison.csv` - Cross-exchange comparison
- `trading_calendar_2025.csv` - Full year trading calendar

## Data Sources

### Primary Sources (Official)

| Exchange | Official URL |
|----------|-------------|
| NYSE | https://www.nyse.com/markets/hours-calendars |
| BSE | https://www.bseindia.com/static/about/Market_Holidays.html |
| NSE | https://www.nseindia.com/resources/exchange-communication-holidays |
| Forex US | https://www.sifma.org/resources/general/holiday-schedule/ |
| Forex UK | https://www.londonstockexchange.com/equities-trading/business-days |
| Forex Japan | https://www.jpx.co.jp/english/corporate/about-jpx/calendar/ |
| Forex China | https://english.sse.com.cn/start/trading/schedule/ |

### Fallback Sources

- NASDAQ: https://www.nasdaq.com/market-activity/stock-market-holiday-schedule
- Zerodha: https://zerodha.com/marketintel/holiday-calendar/
- CME Group: https://www.cmegroup.com/trading-hours.html
- Dukascopy: https://www.dukascopy.com/swiss/english/fx-market-tools/holiday-calendar/

## Important Notes

### Forex Market Holidays

Forex markets operate 24/5 (24 hours a day, 5 days a week), but trading activity and liquidity are significantly affected when major financial centers are closed. Each country's banking holidays impact their respective currency pairs:

- **US Dollar (USD)**: Affected by US bank holidays
- **British Pound (GBP)**: Affected by UK bank holidays
- **Japanese Yen (JPY)**: Affected by Japanese national holidays
- **Chinese Yuan (CNY)**: Affected by Chinese public holidays
- **Indian Rupee (INR)**: Affected by Indian bank holidays

### Best Practices

1. **Run regularly**: Holiday calendars can change, run scraper monthly
2. **Check fallbacks**: If primary source fails, script auto-switches to fallback
3. **Validate data**: Always review scraped data for accuracy
4. **Respect robots.txt**: Script includes delays to be respectful
5. **Update User-Agent**: Periodically update the User-Agent string

## Customization

### Adding New Exchanges

1. Add exchange details to `exchange_data` dictionary
2. Create new parsing method in scraper class
3. Add URL to `start_urls` or call method in `scrape_all()`

### Modifying Retry Logic

```python
def fetch_page(self, url: str, retry: int = 5):  # Increase retries
    # ... existing code
    time.sleep(5)  # Increase delay between retries
```

## Troubleshooting

### Common Issues

1. **403 Forbidden Error**: Website blocking the scraper
   - Solution: Update User-Agent header or use proxy

2. **TimeoutError**: Website taking too long to respond
   - Solution: Increase timeout value in `fetch_page()`

3. **No data scraped**: HTML structure changed
   - Solution: Inspect website HTML and update CSS selectors

4. **Date parsing errors**: Unexpected date format
   - Solution: Add new format to `parse_date()` function

## License

MIT License - Feel free to use and modify

## Disclaimer

This scraper is for educational and personal use. Always check and comply with the terms of service of the websites you're scraping. The accuracy of holiday data should be verified with official exchange announcements.
'''

print("\n" + "=" * 80)
print("SCRAPY ALTERNATIVE SCRIPT CREATED")
print("=" * 80)
print(f"Script length: {len(scrapy_scraper_script)} characters")

print("\n" + "=" * 80)
print("UTILITY SCRIPT CREATED")
print("=" * 80)
print(f"Script length: {len(utility_script)} characters")
print("\nFeatures:")
print("- Date format standardization")
print("- Data validation and cleaning")
print("- iCalendar export (.ics format)")
print("- Cross-exchange comparison")
print("- Full trading calendar generation")

print("\n" + "=" * 80)
print("DOCUMENTATION CREATED")
print("=" * 80)
print(f"README length: {len(readme)} characters")
print(f"Requirements.txt created")
