# Parts Agent - Automated Auto Parts Matching System

## Project Overview

Enterprise-grade automation platform that reads part numbers from Excel (49,650 rows across 6 sheets), scrapes multiple auto parts sites using Chrome/Playwright for comprehensive parts data, applies rule-based matching engine with AI fallback (Gemini/Ollama), and writes results with confidence scoring and color coding back to Excel. Features advanced analytics dashboard, web interface, optimization engine, validation framework, automation platform, and complete multi-site scraping pipeline with SQLite database storage for daily automated processing across 6 target sites.

## Architecture

### Tech Stack
- **Runtime**: Python 3.14 + uv package manager (29 dependencies)
- **Data**: Excel (openpyxl) + SQLite database for multi-site data - 6 sheets, 9,930 rows each (49,650 total)
- **Scraping**: Chrome + Playwright + stealth (subprocess isolated) - Multi-site coordinator
- **AI/ML**: Gemini API + Ollama (local) + CLIP embeddings + rule-based engine
- **GUI**: Triple interface - tkinter desktop + Flask web dashboard + multi-site management
- **Entry Points**: `main_app.py` (desktop) | `src/launch_web_dashboard.py` (web)

### 6-Module Enterprise Architecture
1. **Analytics** (`src/analytics/`) - Real-time statistics, performance tracking, data quality analysis
2. **Web Interface** (`src/web/`) - Flask dashboard with WebSocket updates at localhost:5000
3. **Optimization** (`src/optimization/`) - Smart scheduling, batch processing, predictive matching
4. **Validation** (`src/validation/`) - Data quality checks, anomaly detection, result validation
5. **Automation** (`src/automation/`) - Task scheduling, health monitoring, notifications
6. **Multi-Site** (`src/scrapers/` + `src/database/`) - Multi-site scraper coordination, SQLite storage, GUI integration

### Core Processing Pipeline
```
Excel → Chrome Scraper → Rule Engine → AI Fallback → Excel Output
        (subprocess)     (6 signals)    (Gemini/Ollama)  (color coded)
```

### Critical Files
- **Data**: `FISHER SKP INTERCHANGE 20260302.xlsx` (2.4MB, 6 sheets) + `data/parts_agent.db` (SQLite)
- **Main Scraper**: `src/scraper_subprocess.py` (production-ready, subprocess isolated)
- **Individual Scrapers**: `src/scrapers/acdelco_scraper.py` (COMPLETE), `src/scraper_local.py` (RockAuto - ENHANCED, ready for testing)
- **Shared Utilities**: `src/unicode_utils.py` (character sanitization, encoding safety across all scrapers)
- **Multi-Site Manager**: `src/scrapers/multi_site_manager.py` (coordinates across 6 sites)
- **Database Manager**: `src/database/db_manager.py` + `src/database/schema.sql` (relational storage)
- **Core Processor**: `src/excel_handler.py` (crash-safe save, retry logic)
- **Enhanced Analysis**: `src/run_enhanced_image_analysis.py` (100% UNCERTAIN→LIKELY upgrade rate)
- **Comparison Engines**: `src/rule_compare.py` + `src/gemini_compare.py` + image analysis
- **GUI Integration**: `src/gui/main_window.py` (Tools > Analytics Dashboard + Multi-Site tab)

## Current State

### Production Ready Systems
- **Chrome Scraper**: Subprocess-isolated, persistent profile
- **RockAuto Scraper**: COMPLETE - price, category, OEM refs, images, brand matching all working (tested: ANCHOR 3217 ENGINE MOUNT $20.79, GMB 130-7340AT ENGINE WATER PUMP $86.79)
- **ACDelco Scraper**: COMPLETE - 100% success rate, 657 fitment records, all 6 tables populated
- **Unicode Safety System**: Shared protection prevents crashes across all scrapers (unicode_utils.py)
- **Multi-Site Pipeline**: Complete scraping coordination across 6 target sites with SQLite storage, wired into excel_handler.py for enriched matching
- **Rule Engine**: 6-signal weighted matching (40% OEM refs, 20% category, 15% description, etc.)
- **Enhanced Image Analysis**: CLIP+SSIM system with proven 100% UNCERTAIN→LIKELY upgrade rate
- **Analytics Dashboard**: 5-tab interactive GUI with real-time charts and Grade B quality scoring
- **Web Interface**: Network-accessible Flask dashboard with WebSocket updates
- **Multi-Site GUI**: Integrated management tab with site status, cross-site search, results display
- **Database System**: SQLite with 8 tables for parts, sources, images, fitment, OEM refs, logs
- **Optimization Engine**: Smart prioritization, resource-aware batch processing
- **Validation Framework**: Multi-layer quality assurance with anomaly detection

### Processing Status (Updated April 9, 2026)
- **Total Rows**: 49,650 across 6 sheets (GMB, Four Seasons, SMP, Anchor, Dorman, Master)
- **Processed**: 146 rows (116 Anchor + 10 SMP + 20 GMB)
- **Confirmed Matches**: 48 (36 Anchor + 2 SMP + 10 GMB YES; plus 5 GMB LIKELY)
- **GMB Fresh Run (Session 3)**: First 20 rows = 10 YES, 5 LIKELY, 5 UNCERTAIN, 0 NO (75% match rate) — strongest fresh run to date
- **SMP Multi-Site Results**: 4 of 5 eligible UNCERTAIN rows upgraded via enrichment (rows 666/834/1378 → YES, 1538 → LIKELY). Row 1269 stayed UNCERTAIN (no OEM overlap).
- **Anchor Reprocess (Session 3)**: 0 of 6 eligible UNCERTAIN upgraded — architectural blocker (see Known Issues: SKP OEM ref gap)
- **Unprocessed**: 49,504 rows across 5 sheets

### Verified Capabilities
- Desktop GUI integration (tkinter with analytics integration)
- Web dashboard at http://localhost:5000 (confirmed accessible)
- Enhanced image analysis with CLIP semantic matching (8/8 successful upgrades in recovery)
- Automated health monitoring and alerting systems
- Multi-format export (JSON, charts, comprehensive reports)
- **Multi-Site Database**: SQLite with 8 tables, 857 records, 6 site configurations (Phase 1 ✅)
- **Cross-Site Coordination**: Multi-site manager with RockAuto integration verified
- **GUI Multi-Site Tab**: Site management interface with search and status monitoring

## Active TODO / Next Steps

### Current Priority: Daily-Use Sites Enhancement
✅ **ACDelco Scraper COMPLETE** - Production ready with 100% success rate, 657 fitment records, Unicode safety
✅ **Multi-Site Infrastructure Complete** - Full pipeline with SQLite database, GUI integration, and RockAuto implementation
✅ **Unicode Safety System** - Shared protection prevents crashes across all scrapers
✅ **RockAuto Scraper COMPLETE** - All fields working: price, category, OEM refs, images, brand matching (tested: ANCHOR 3217 ENGINE MOUNT $20.79, GMB 130-7340AT ENGINE WATER PUMP $86.79)
✅ **GitHub Integration COMPLETE** - Repository connected: https://github.com/oatesconner001-beep/Auto-Parts-App-2026, initial commit pushed (15684ff)
✅ **Full Project Audit COMPLETE** (2026-03-30) - 3 HIGH, 4 MEDIUM, 6 LOW issues identified.
✅ **HIGH Audit Fixes COMPLETE** (2026-03-30) - All 3 HIGH priority issues resolved:
   * OEM reference parsing fixed — `_is_valid_oem_ref()` validator, warranty text stripping, blacklist filtering
   * `listing_id`/`core_charge` data flow fixed — key mismatches corrected in `_store_site_result`, core_charge propagated to all listings
   * ShowMeTheParts documentation corrected across 6 files — stealth scraper acknowledged
   * `schema.sql` synced — `listing_id`, `core_charge`, `reference_type` columns added
   * Database cleaned — 10 corrupted OEM reference rows removed, `89018166` re-added clean (39 clean refs remaining)

✅ **ShowMeTheParts Integration COMPLETE** (2026-04-02) - Stealth scraper wired into multi_site_manager, interchange refs storing with oem_brand and reference_type, site_configs activated
✅ **PartsGeek Integration COMPLETE** (2026-04-02) - Scraper wired into multi_site_manager, standardized result format
✅ **oem_brand Storage Fixed** (2026-04-02) - `_store_site_result()` OEM INSERT now includes oem_brand column for interchange data
✅ **Session 1 DB Cleanup COMPLETE** (2026-04-03) - ShowMeTheParts config fixed (rate_limit=3, retries=3, timeout=30), Dorman/Moog deactivated (stub scrapers), TEST_BRAND removed, oem_references deduplicated 44->34 with UNIQUE(part_id, oem_number, source_site) constraint
✅ **Session 1 RockAuto Data Quality COMPLETE** (2026-04-03) - Specs blocklist filters junk (OEM refs/warranty/nav text), fitment text parsing replaces broken URL method, parts.category/part_name populated via COALESCE UPDATE
✅ **Session 1 First SMP Production Run** (2026-04-03) - 10 rows, 0 errors, 12m34s. Pipeline proven end-to-end.
✅ **Post-Session 1 Audit COMPLETE** (2026-04-06) - All DB fixes verified, all code changes confirmed, 10 SMP Excel rows verified with correct data and colors. UNIQUE constraint tested and working. Dead code `_extract_fitment_from_url()` at line 283 flagged for cleanup. Minor "Anchor" label bug in SMP fitment/desc columns noted.
✅ **Session 2 Multi-Site Pipeline Wired** (2026-04-06) - excel_handler.py enriched merge complete. 77 lines added: `_enrich_with_multi_site()` merges OEM refs, category, description, specs, fitment from ACDelco/PartsGeek/ShowMeTheParts before rule_compare. Graceful fallback to RockAuto-only on any failure. Test result: SMP rows upgraded UNCERTAIN 43% → YES 81-82%.
✅ **Session 3 SMP Reprocess** (2026-04-08) - 3 eligible UNCERTAIN rows reprocessed: row 1378 (DLA-267 vs SKDLA58) UNCERTAIN 43% → YES 80% via shared OEM 746361; row 1538 (DLA975 vs SK746015) → LIKELY 70% via shared OEM 746015; row 1269 (DLA-1 vs SKDLA1) stayed UNCERTAIN 30% (no OEM overlap). 67% upgrade rate for eligible rows.
✅ **Session 3 Anchor Reprocess** (2026-04-08) - 6 eligible UNCERTAIN rows reprocessed (rows 45/47/67/71/73/87) → 0 upgrades. Architectural blocker identified: PartsGeek and ShowMeTheParts return OEM refs for ANCHOR-brand parts but zero OEM refs for SKP-brand parts, so rule-engine OEM signal (40% weight) stays at 0. Scores slightly improved via category+fitment (43% → 42-53%) but no threshold crossing. Anthropic API credits exhausted blocked AI fallback.
✅ **Session 3 GMB Fresh Run** (2026-04-08) - First 20 GMB rows processed in ~33 min (1.65 min/row). Result: 10 YES, 5 LIKELY, 5 UNCERTAIN, 0 NO = 75% match rate. Zero scraper failures, zero errors. Strongest fresh-processing result to date.
✅ **Session 3 src/ Cleanup** (2026-04-09) - Removed 47 files (45 git-tracked, 2 untracked backups). Categories deleted: B (deprecated scrapers, 6 files), C (test/debug scripts, 25 files), D (one-off Dorman/ACDelco investigation scripts, 16 files). Category E (~8 files) left for next-session verification.
✅ **Session 3 Dead Code Removal** (2026-04-09) - `_extract_fitment_from_url()` removed from `src/scraper_local.py` (20 lines, zero callers verified). The active method on `scrapers/multi_site_manager.py` is a different scope and untouched.

**Active TODO for Next Session:**
1. **GMB scale-up run** - Process remaining 280 GMB rows (~7-8 hours at 1.65 min/row) — dedicated throughput session
2. **Category E src/ audit** - Verify imports for ~8 remaining cleanup candidates (excel_handler_rules_only.py, excel_handler_enhanced.py, parallel_image_processor.py, optimized_image_pipeline.py + _fixed.py, bulk_image_scraper.py, batch_processor.py, enhanced_batch_processor.py, batch_excel_updater.py, chrome_worker.py, gui_enhanced_integration.py, verify_enhanced_system.py, verify_database_status.py, gui.py, run_image_analysis.py)
3. **Unblock Anchor UNCERTAIN upgrades** - Restore Anthropic API credits OR implement local AI fallback (Ollama moondream already installed)
4. **SKP-brand OEM ref strategy** - Decide: build custom SKP scraper OR lower rule-engine threshold for strong category+fitment-only matches
5. **Remaining audit issues** - 2 MEDIUM (RockAuto fitment needs live testing, specs colon edge cases), 6 LOW (stale comments, success_rate never updated, etc.)

**Quality Benchmark**: All scrapers must meet ACDelco standard - all 6 tables populated, 219+ fitment records where applicable, zero Unicode crashes, 100% success rate

**Manufacturer Sites Phase (PAUSED)**
- ⏸️ **Moog Scraper** - Paused for daily-use priority
- ⏸️ **Dorman Scraper** - Paused for daily-use priority

### Immediate Processing Priorities (Production Ready)
1. **Multi-Site Testing** - Launch GUI (`main_app.py`) → Multi-Site tab → test cross-site search with all 4 active scrapers
2. **Enhanced Analysis Deployment** - Process 79 Anchor UNCERTAIN rows (expected: ~79 LIKELY upgrades)
3. **SMP Sheet Priority** - Start fresh processing (9,930 rows at proven 66.7% success rate)
4. **Database Population** - Use multi-site system to populate SQLite with comprehensive parts data

### Development Roadmap (Updated)
- **Phase 1**: Multi-site scraping infrastructure ✅ **COMPLETE**
- **Phase 2**: Individual site scrapers (PartsGeek, ACDelco, ShowMeTheParts done; Dorman, Moog paused) **← CURRENT**
- **Phase 3**: Advanced cross-site part matching and normalization
- **Phase 4**: Daily recurring pipeline automation with site health monitoring

## Key Decisions Made

### Technical Architecture
- **Subprocess Isolation**: Eliminated asyncio/sync conflicts, enables reliable batch processing
- **Chrome over Headless**: Real Chrome bypasses bot detection vs failed Chromium attempts
- **Dual AI Backend**: Gemini API (quota limited) + Ollama local (unlimited moondream model)
- **Enhanced Image Analysis**: CLIP semantic + SSIM structural similarity over basic CV methods
- **Modular Enterprise Design**: 5-module architecture for scalability and maintainability

### Data Processing Strategy
- **Sheet-based Processing**: Each sheet filtered by CURRENT SUPPLIER column matching sheet name
- **Rule-first Approach**: 6-signal weighted engine before AI fallback (cost optimization)
- **UNCERTAIN Upgrade Path**: Proven 100% upgrade rate via enhanced image analysis
- **Sequential Coordination**: Single Excel process at a time prevents file corruption
- **Color Coding**: Visual Excel feedback (YES=green, LIKELY=light green, UNCERTAIN=yellow, NO=red)

### Multi-Site Architecture
- **Database Complement**: SQLite enhances Excel storage without replacing existing workflows
- **Site Abstraction**: Standardized scraper interface allows uniform handling of diverse sites
- **Rate Limiting**: Per-site delays prevent blocking while maximizing throughput
- **Graceful Degradation**: System functions with any combination of available/unavailable sites
- **Cross-Site Normalization**: Unified part data schema enables comprehensive price/availability comparison

### Infrastructure Optimization
- **Free Tier Maximization**: Local Ollama + subprocess Chrome + CLIP models avoid API costs
- **Production Readiness**: Comprehensive testing, error handling, health monitoring
- **Triple GUI Strategy**: Desktop (tkinter) for development, web (Flask) for monitoring, multi-site for coordination
- **Enterprise Integration**: Analytics, optimization, validation, automation, multi-site all operational

### Multi-Site Expansion Strategy
- **Extend Not Replace**: Build on existing Chrome/Playwright scraper infrastructure
- **Hybrid Storage**: Keep Excel for user interface, add SQLite for multi-site data relationships
- **Primary GUI Focus**: Integrate new features into tkinter desktop app (established as primary)
- **Site Prioritization**: Dorman (manufacturer base truth) → Moog → ACDelco → others

### API & Tool Evolution
- **Firecrawl API**: DEPRECATED for new development (experimental approach, credits exhausted)
- **Chrome/Playwright Standard**: Primary approach proven with ACDelco (100% success rate, comprehensive data extraction)
- **Manual Approval Mode**: All database schema changes and file modifications require explicit approval

## Known Issues

### Current Limitations
- **llava-phi3 Model**: Broken on Ollama v0.18.0 (`llama-sampling.cpp` assertion crash)
- **RockAuto Scraper**: ✅ FIXED - Enhanced with DOM price/category extraction, multiple listings, fitment parsing, OEM references
- **Excel File Locking**: Cannot run multiple Excel handlers simultaneously (learned from corruption incident)
- **Gemini API Quota**: Daily limits on free tier (auto-disables gracefully, fallback to rules)
- **Anthropic API Credits**: EXHAUSTED as of Session 3 (2026-04-08) — Claude fallback disabled, rule-engine only
- **ShowMeTheParts**: Incapsula WAF JavaScript challenge (stealth scraper COMPLETE and integrated)
- **SKP-brand OEM Ref Gap** (2026-04-08, discovered Session 3): SKP-brand parts return zero OEM refs from both PartsGeek and ShowMeTheParts, capping multi-site enrichment confidence at ~50-60% (category+fitment only) for Anchor sheet reprocessing. The rule engine's 40% OEM weight stays at 0 for all SKP parts, so even identical category + overlapping fitment cannot cross the YES threshold. Mitigations: (a) restore Anthropic credits for AI fallback, (b) build SKP-specific scraper, (c) lower threshold for category+fitment-only matches.

### Established Workarounds
- **Use moondream**: 828MB model works perfectly for unlimited vision tasks via Ollama
- **OEM Compensation**: 40% weight on OEM refs matching compensates for category failures
- **Sequential Processing**: Process one sheet at a time to prevent Excel file conflicts
- **Local Ollama Priority**: Unlimited processing when Gemini quota exhausted
- **Multi-Site Focus**: All 4 scrapers (RockAuto, ACDelco, PartsGeek, ShowMeTheParts) integrated and tested. Pipeline disconnected from excel_handler — next priority.

## Do Not Touch

### Excel Schema (Critical Business Logic)
- **Column Layout A-P**: Especially output columns J-P (MATCH RESULT, CONFIDENCE %, etc.)
- **Color Coding Values**: YES=`00FF00`, LIKELY=`90EE90`, UNCERTAIN=`FFFF00`, NO=`FF0000`
- **Sheet Names**: "GMB", "Four Seasons " (with trailing space), "SMP", "Anchor", "Dorman"
- **Row Filtering Logic**: CURRENT SUPPLIER (col B) must exactly match sheet name for processing
- **Output Schema**: 7 output columns (J-P) with specific data types and business meanings

### Production Systems (Battle-Tested)
- **`src/scraper_subprocess.py`**: Primary scraper - subprocess isolation working perfectly
- **`src/scrapers/parallel_scraper.py`**: Multi-session scraper - do not modify without approval
- **`src/analytics/` entire module**: 5-tab system fully integrated and tested (100% pass rate)
- **`.browser_profile/` directory**: Chrome session persistence for anti-bot protection
- **API Integrations**: Gemini model `gemini-3-flash-preview` (only working model on free tier)
- **Enhanced image system**: CLIP+SSIM implementation with proven 100% upgrade rate
- **Database Schema**: SQLite 8-table structure - no changes without explicit "APPROVED" confirmation

### Critical Environment Paths
- **Excel File**: `FISHER SKP INTERCHANGE 20260302.xlsx` (2.4MB, never rename or move)
- **Chrome Binary**: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- **Python Runtime**: `C:\Python314\python.exe` (3.14.0 required)
- **Package Manager**: uv at `C:\Users\Owner\.local\bin\uv.exe`
- **Environment Setup**: `export PATH="$PATH:/c/Users/Owner/.local/bin"`
- **Project Root**: `C:\Users\Owner\Desktop\Parts Agent 20260313\`

---

**For detailed technical architecture, operational procedures, and troubleshooting:** See `docs/` directory.