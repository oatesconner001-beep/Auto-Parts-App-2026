-- Database Migration: Add Warehouse and Reference Type Support
-- For RockAuto comprehensive enhancement
-- Date: 2026-03-26

-- Add warehouse support to part_sources table
ALTER TABLE part_sources ADD COLUMN warehouse_id VARCHAR(100);
ALTER TABLE part_sources ADD COLUMN warehouse_name VARCHAR(200);
ALTER TABLE part_sources ADD COLUMN shipping_info TEXT;

-- Add reference type support to oem_references table
ALTER TABLE oem_references ADD COLUMN reference_type VARCHAR(50) DEFAULT 'oem';

-- Create indexes for new fields
CREATE INDEX IF NOT EXISTS idx_part_sources_warehouse ON part_sources(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_oem_references_type ON oem_references(reference_type);

-- Update site_configs with RockAuto entry if not exists
INSERT OR IGNORE INTO site_configs (
    site_name,
    base_url,
    is_active,
    rate_limit_delay,
    status,
    notes
) VALUES (
    'RockAuto',
    'https://www.rockauto.com',
    1,
    2.0,
    'active',
    'Enhanced scraper with warehouse pricing, fitment data, and buyer guide support'
);

-- Comments for reference types:
-- 'oem' - Original Equipment Manufacturer reference
-- 'aftermarket' - Aftermarket equivalent reference
-- 'competitor' - Competitor cross-reference
-- 'supersedes' - This part replaces the referenced part
-- 'superseded_by' - This part is replaced by the referenced part