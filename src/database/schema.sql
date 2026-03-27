-- Parts Agent Multi-Site Database Schema
-- Complements existing Excel storage with relational data for multi-site operations

-- Core parts catalog - master list of unique parts
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number VARCHAR(100) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    part_name VARCHAR(500),
    category VARCHAR(200),
    subcategory VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(part_number, brand)
);

-- Site-specific part data - one row per part per site
CREATE TABLE IF NOT EXISTS part_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER REFERENCES parts(id),
    site_name VARCHAR(100) NOT NULL,
    site_part_number VARCHAR(200),
    availability_status VARCHAR(100),
    price DECIMAL(10,2),
    sale_price DECIMAL(10,2),
    stock_quantity INTEGER,
    product_url VARCHAR(1000),
    last_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scrape_success BOOLEAN DEFAULT TRUE,
    scrape_error VARCHAR(500),
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE
);

-- Part images from various sites
CREATE TABLE IF NOT EXISTS part_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER REFERENCES parts(id),
    site_name VARCHAR(100) NOT NULL,
    image_url VARCHAR(1000) NOT NULL,
    image_type VARCHAR(50) DEFAULT 'product', -- product, diagram, installation
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE
);

-- Vehicle fitment data - year/make/model/engine compatibility
CREATE TABLE IF NOT EXISTS fitment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER REFERENCES parts(id),
    year_start INTEGER,
    year_end INTEGER,
    make VARCHAR(100),
    model VARCHAR(200),
    engine VARCHAR(200),
    notes VARCHAR(500),
    source_site VARCHAR(100),
    confidence DECIMAL(3,2), -- 0.00 to 1.00
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE
);

-- OEM reference numbers - cross-reference data
CREATE TABLE IF NOT EXISTS oem_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER REFERENCES parts(id),
    oem_number VARCHAR(200) NOT NULL,
    oem_brand VARCHAR(100),
    source_site VARCHAR(100),
    confidence DECIMAL(3,2) DEFAULT 1.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE
);

-- Site scraping logs and performance tracking
CREATE TABLE IF NOT EXISTS scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name VARCHAR(100) NOT NULL,
    scrape_type VARCHAR(100), -- search, detail, category
    search_term VARCHAR(500),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    rows_collected INTEGER DEFAULT 0,
    rows_failed INTEGER DEFAULT 0,
    duration_seconds DECIMAL(8,2),
    error_message VARCHAR(1000),
    user_agent VARCHAR(500),
    rate_limit_delay DECIMAL(5,2)
);

-- Site configuration and health monitoring
CREATE TABLE IF NOT EXISTS site_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name VARCHAR(100) UNIQUE NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit_delay DECIMAL(5,2) DEFAULT 2.0, -- seconds between requests
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 30,
    success_rate DECIMAL(5,2) DEFAULT 0.00, -- calculated success rate
    last_successful_scrape TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active', -- active, disabled, blocked, maintenance
    notes VARCHAR(1000),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Part specifications and technical data
CREATE TABLE IF NOT EXISTS part_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id INTEGER REFERENCES parts(id),
    site_name VARCHAR(100),
    spec_name VARCHAR(200) NOT NULL,
    spec_value VARCHAR(500),
    spec_unit VARCHAR(50),
    spec_type VARCHAR(100), -- dimension, material, weight, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_parts_brand_number ON parts(brand, part_number);
CREATE INDEX IF NOT EXISTS idx_part_sources_site ON part_sources(site_name);
CREATE INDEX IF NOT EXISTS idx_part_sources_part_id ON part_sources(part_id);
CREATE INDEX IF NOT EXISTS idx_fitment_year_make ON fitment(year_start, make);
CREATE INDEX IF NOT EXISTS idx_oem_references_number ON oem_references(oem_number);
CREATE INDEX IF NOT EXISTS idx_scrape_log_site_timestamp ON scrape_log(site_name, timestamp);

-- Views for common queries
CREATE VIEW IF NOT EXISTS parts_with_sources AS
SELECT
    p.id as part_id,
    p.part_number,
    p.brand,
    p.part_name,
    p.category,
    ps.site_name,
    ps.price,
    ps.availability_status,
    ps.product_url,
    ps.last_scraped
FROM parts p
LEFT JOIN part_sources ps ON p.id = ps.part_id
ORDER BY p.brand, p.part_number, ps.site_name;

CREATE VIEW IF NOT EXISTS site_performance AS
SELECT
    sc.site_name,
    sc.is_active,
    sc.success_rate,
    sc.last_successful_scrape,
    sc.consecutive_failures,
    sc.status,
    COUNT(sl.id) as total_scrapes,
    SUM(CASE WHEN sl.success = 1 THEN 1 ELSE 0 END) as successful_scrapes,
    AVG(sl.duration_seconds) as avg_duration,
    SUM(sl.rows_collected) as total_rows_collected
FROM site_configs sc
LEFT JOIN scrape_log sl ON sc.site_name = sl.site_name
    AND sl.timestamp >= datetime('now', '-7 days')
GROUP BY sc.site_name;