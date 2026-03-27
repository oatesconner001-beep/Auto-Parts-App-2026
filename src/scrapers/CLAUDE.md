# Multi-Site Scrapers Documentation

## Overview

Multi-site scraping system that coordinates part searches across 6 auto parts websites. Built on existing Chrome/Playwright infrastructure with SQLite database integration.

## Architecture

### Core Components

- **MultiSiteScraperManager**: Central coordinator for all site scrapers
- **Individual Site Scrapers**: Dedicated scrapers for each site (ACDelco, Moog, etc.)
- **Database Integration**: SQLite storage with 8-table schema
- **Standardized Interface**: Common result format across all scrapers

## Implemented Scrapers

### ✅ ACDelco Scraper (`acdelco_scraper.py`)

**Status**: ✅ **COMPLETE & PRODUCTION READY** - Full implementation with comprehensive data extraction

**Site Details**:
- URL: `acdelco.com` → redirects to `parts.gmparts.com`
- Protection: None (Playwright accessible)
- Navigation: Catalog-based product discovery

**Data Fields Extracted**:
- ✅ Part Number (GM Part #)
- ✅ Product Name & Description
- ✅ Brand (ACDelco/GM Original Equipment/GM Genuine Parts)
- ✅ Pricing (MSRP)
- ✅ OEM Cross-References (ACDelco Part #)
- ✅ Product Images (6+ high-res images)
- ✅ Availability Status
- ✅ Technical Specifications
- ✅ **Fitment Data** (CRITICAL - solves fitment table 0-rows problem)

**Fitment Data Breakthrough**:
```
Parses comprehensive fitment strings like:
"Fits - 2011-2024 Buick Enclave ; 2016-2019 Cadillac ATS ; 2022-2025 Cadillac CT4 ; ..."

Creates individual fitment records:
- 2011 Buick Enclave
- 2012 Buick Enclave
- ...
- 2024 Buick Enclave
- 2016 Cadillac ATS
- etc.
```

**Database Tables Populated**:
- `parts` (main part record)
- `part_sources` (price, availability, product URL)
- `oem_references` (ACDelco cross-references)
- `part_images` (product images)
- `part_specs` (technical specifications)
- `fitment` (year/make/model combinations)

**Production Test Results**: ✅ **ALL 5 PARTS SUCCESSFUL**
- 12735811 (Oil Filter): 219 fitment records, $11.23, OEM: PF63
- 84801575 (Washer Pump): $15.42, OEM: 84801575
- 19474058 (Thermostat): $123.10, OEM: 15-11125G
- 88866309 (Battery): $216.33, OEM: 48GHRA
- 19367762 (Touch-up Paint): $31.18, OEM: 19367762

**Final Database Counts**: 793 total records, 657 fitment records
**Success Rate**: 100% (5/5 parts), **Zero crashes**, **Unicode-safe**

### ✅ RockAuto Scraper

**Status**: ✅ **ENHANCED & READY FOR TESTING** - DOM price/category extraction, multiple listings, fitment from URL, OEM parsing, unicode safety applied
**Site Details**: Chrome-based, bot detection bypass working

**Enhanced Features Implemented**:
- ✅ DOM-based price extraction (fixed None returns)
- ✅ DOM-based category extraction (fixed "Continue Shopping")
- ✅ Multiple listings per part (unique listing_ids)
- ✅ URL fitment parsing from catalog URLs
- ✅ Enhanced OEM reference parsing via aria-label
- ✅ Multiple product images extraction
- ✅ Warranty/notes capture
- ✅ Unicode safety throughout all functions
- ✅ Database schema updated (listing_id, core_charge, reference_type)
- ✅ Multi-site manager integration for multiple listings

**Backup**: `scraper_local_backup_20260326.py`
**Ready For**: Live testing with 5 verified part numbers

### ⏸️ Moog Scraper

**Status**: ⏸️ **PAUSED** - Shifted to manufacturer sites phase
**Site Details**: `moogparts.com` - No protection detected, accessible

### 🚧 PartsGeek Scraper

**Status**: PENDING - Cloudflare bypass needed
**Site Details**: `partsgeek.com` - Light protection

### ⏸️ Dorman Scraper

**Status**: ⏸️ **PAUSED** - Shifted to daily-use sites priority
**Site Details**: `dormanproducts.com` - ShieldSquare Captcha

### 🚧 ShowMeTheParts Scraper

**Status**: PENDING - Incapsula WAF bypass needed
**Site Details**: `showmetheparts.com` - Incapsula WAF

### ❌ Firecrawl API Scraper

**Status**: ❌ **DEPRECATED** - Do not use for new development
**Details**: Credits exhausted, experimental approach superseded by Chrome/Playwright standard

## Unicode Safety System ✅

**Status**: ✅ **IMPLEMENTED** - Shared protection for all scrapers

**Unicode Utilities** (`unicode_utils.py`):
- **Character Sanitization**: `™→TM`, `®→(R)`, `°→deg`, `—→-`, emojis→text
- **Encoding Safety**: All text tested for cp1252 compatibility
- **Fallback Protection**: ASCII-only fallback for problematic characters
- **Recursive Cleaning**: Sanitizes dictionaries, lists, and nested data structures

**Applied To**:
- ✅ **ACDelco Scraper**: All extracted data sanitized
- ✅ **Multi-Site Manager**: Database storage protected
- ✅ **Console Output**: All printing Unicode-safe
- 🔄 **Future Scrapers**: Automatically inherit Unicode protection

**Benefits**:
- **Zero Crashes**: Eliminates Unicode encoding errors
- **Cross-Platform**: Works on Windows cp1252, Linux UTF-8
- **Database Safe**: Prevents Unicode storage corruption
- **Shared Base**: All future scrapers automatically protected

## Standardized Result Format

All scrapers return standardized results:

```python
{
    'success': bool,              # Scraping operation succeeded
    'found': bool,                # Part data found
    'site_name': str,             # Site identifier
    'part_number': str,           # Original search part number
    'brand': str,                 # Detected/confirmed brand
    'category': str,              # Part category
    'oem_refs': list,             # OEM cross-references
    'price': str,                 # Pricing information
    'image_url': str,             # Primary product image
    'product_url': str,           # Product page URL
    'description': str,           # Product description
    'specs': dict,                # Technical specifications
    'features': list,             # Product features
    'availability': str,          # Stock/availability status
    'stock_quantity': int,        # Quantity if available
    'fitment_data': list,         # Year/make/model fitment records
    'error': str                  # Error message if failed
}
```

## Database Schema Integration

### Tables Populated by Multi-Site System

1. **`parts`**: Main part records (part_number, brand, category, description)
2. **`part_sources`**: Site-specific data (price, availability, product_url, site_name)
3. **`oem_references`**: Cross-reference part numbers (oem_number, source_site)
4. **`part_images`**: Product images (image_url, site_name, image_type)
5. **`part_specs`**: Technical specifications (spec_name, spec_value, site_name)
6. **`fitment`**: Vehicle compatibility (year, make, model, engine, source_site)
7. **`scrape_log`**: Scraping activity logs (site_name, success, duration)
8. **`site_configs`**: Site configuration (rate_limit_delay, is_active)

## Usage Examples

### Single Part Multi-Site Search

```python
from scrapers.multi_site_manager import MultiSiteScraperManager

manager = MultiSiteScraperManager()

# Search across all active sites
results = manager.scrape_part_multi_site(
    part_number="12735811",
    brand="ACDelco",
    sites=["ACDelco", "RockAuto", "Moog"],
    store_results=True
)

print(f"Found on {results['summary']['found_on_sites']} sites")
```

### Get Cross-Site Part Summary

```python
# Get comprehensive part summary
summary = manager.get_multi_site_summary("12735811", "ACDelco")

print(f"Price range: ${summary['price_range']['min']} - ${summary['price_range']['max']}")
print(f"Available on {summary['sites_found']} sites")
print(f"OEM references: {len(summary['oem_references'])}")
print(f"Images available: {len(summary['images'])}")
```

### Direct ACDelco Scraper Usage

```python
from scrapers.acdelco_scraper import ACDelcoScraper

scraper = ACDelcoScraper(headless=True)
result = scraper.scrape_part("12735811", "ACDelco")

print(f"Fitment records: {len(result['fitment_data'])}")
print(f"OEM references: {result['oem_refs']}")
```

## Implementation Status

### Phase 1: Infrastructure ✅ COMPLETE
- ✅ Multi-site coordinator
- ✅ Database schema and integration
- ✅ Standardized scraper interface
- ✅ Rate limiting and error handling
- ✅ RockAuto integration

### Phase 2: ACDelco Implementation ✅ COMPLETE
- ✅ ACDelco scraper with comprehensive data extraction
- ✅ Fitment data parsing (657 fitment records)
- ✅ Multi-site manager integration
- ✅ Database table population (all 6 tables)
- ✅ Unicode safety system implemented
- ✅ 100% success rate on 5 verified parts

### Phase 3: Daily-Use Sites Priority 🚧 **CURRENT PHASE**
**NEW PRIORITY ORDER** - Focus on most heavily used sites:
- ✅ **RockAuto Enhancement COMPLETE** - Ready for live testing in next session
- 🔄 **PartsGeek** (Cloudflare bypass required) **← NEXT TARGET**
- ⏳ **ShowMeTheParts** (Incapsula WAF bypass required)

**Quality Benchmark**: ACDelco standard (all 6 tables, 219+ fitment records, zero crashes, 100% success rate)

### Phase 4: Manufacturer Sites ⏸️ **PAUSED**
- ⏸️ Moog scraper (accessible, paused for daily-use priority)
- ⏸️ Dorman scraper (stealth techniques needed)
- ⏸️ ACDelco expansion (additional part categories)

### Phase 5: Production Deployment ⏳ PLANNED
- ⏳ Daily automated scraping
- ⏳ Site health monitoring
- ⏳ Change detection system
- ⏳ GUI integration enhancements

## Testing Protocol

### ACDelco Scraper Testing

Test with verified parts from pre-code analysis:

```bash
# Test individual ACDelco scraper
uv run python src/scrapers/acdelco_scraper.py

# Test via multi-site manager
uv run python -c "
from scrapers.multi_site_manager import MultiSiteScraperManager
manager = MultiSiteScraperManager()
result = manager.scrape_part_multi_site('12735811', 'ACDelco', ['ACDelco'])
print(result)
"
```

**Verification Checklist**:
- [ ] Part data extraction successful
- [ ] Fitment records > 0 (critical)
- [ ] OEM references populated
- [ ] Product images found
- [ ] Database records created in all 6 tables
- [ ] No scraping errors

### RockAuto Scraper Testing

Test with 5 real verified part numbers from live RockAuto:

```bash
# Test via multi-site manager with enhanced RockAuto
uv run python -c "
from scrapers.multi_site_manager import MultiSiteScraperManager
manager = MultiSiteScraperManager()
result = manager.scrape_part_multi_site('ANCHOR3217', 'SKP', ['RockAuto'])
print(result)
"
```

**Enhanced Features Verification**:
- [ ] DOM price extraction working (not None)
- [ ] DOM category extraction working (not "Continue Shopping")
- [ ] Multiple listings captured per part
- [ ] URL fitment parsing from catalog URLs
- [ ] OEM references from aria-label structure
- [ ] Multiple product images found
- [ ] Warranty/notes captured
- [ ] Unicode safety applied throughout
- [ ] Database records with listing_id and core_charge
- [ ] All 6 tables populated correctly

## Performance Considerations

- **Rate Limiting**: 2-3 second delays between requests
- **Error Handling**: Graceful degradation if sites unavailable
- **Memory Management**: Browser cleanup after each scrape
- **Concurrent Limits**: Sequential site processing to avoid detection

## Future Enhancements

1. **Stealth Techniques**: Shared stealth_base.py for protected sites
2. **Cross-Site Matching**: Part number normalization across sites
3. **Price Tracking**: Historical price monitoring
4. **Availability Alerts**: Stock status notifications
5. **Data Quality**: Confidence scoring and validation

---

**Last Updated**: 2026-03-26
**Status**: RockAuto scraper enhanced and ready for live testing, PartsGeek scraper next priority