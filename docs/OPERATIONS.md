# Parts Agent - Operations Guide

## Environment Setup

### Required Environment
```bash
# Windows 11 Home 10.0.26200
# Python 3.14.0 at C:\Python314\python.exe
# UV 0.10.10 at C:\Users\Owner\.local\bin\uv.exe

# Standard environment setup (run before all commands)
export PATH="$PATH:/c/Users/Owner/.local/bin"
cd "c:/Users/Owner/Desktop/Parts Agent 20260313"
```

### Virtual Environment Management
```bash
# Environment is automatically managed by uv
# Located at: .venv/ (uv-managed, 29 dependencies)

# Check environment status
uv --version

# Install/update dependencies (if needed)
uv sync

# Check Python version
uv run python --version
```

## Core Application Launch

### Desktop GUI (Primary Interface)
```bash
# Launch main desktop application
uv run python main_app.py

# Features available:
# - Multi-panel interface with tabs
# - Real-time Excel viewer/editor
# - Job queue management with progress tracking
# - Analytics dashboard integration (Tools > Analytics Dashboard)
# - Configuration wizard
# - Live logging and statistics
```

### Web Dashboard (Secondary Interface)
```bash
# Launch web interface
uv run python src/launch_web_dashboard.py

# Access at: http://localhost:5000
# Features:
# - Network-accessible dashboard
# - Real-time WebSocket updates
# - Mobile-responsive design
# - Processing control and monitoring
# - Data export capabilities
```

### Analytics Integration
```bash
# Test analytics dashboard
uv run python src/test_analytics_dashboard.py

# Test GUI analytics integration
uv run python src/test_gui_analytics_integration.py

# Direct analytics access
uv run python -c "from src.analytics import Analytics; a = Analytics(); print(a.get_comprehensive_report())"
```

## Multi-Site Operations (Phase 1 Complete)

### Database Management
```bash
# Initialize multi-site database (run once)
uv run python src/database/db_manager.py

# Verify database status and show table counts
uv run python src/verify_database_status.py

# Test integration (all components)
uv run python src/test_multi_site_integration.py
```

### Multi-Site Scraping
```bash
# Test multi-site manager with single part
uv run python src/scrapers/multi_site_manager.py

# Launch GUI with Multi-Site tab
uv run python main_app.py
# -> Navigate to Multi-Site tab
# -> Enter part number + brand (e.g., ANCHOR 3217)
# -> Select sites to search (RockAuto currently active)
# -> Click "Search All Sites"
```

### Site Configuration Management
```bash
# View current site configurations
uv run python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
configs = db.get_site_configs()
for cfg in configs:
    status = 'ACTIVE' if cfg['is_active'] else 'INACTIVE'
    print(f'{cfg[\"site_name\"]:12} - {status} (delay: {cfg[\"rate_limit_delay\"]}s)')
"

# Enable/disable sites (done via GUI Multi-Site tab)
# Toggle site status by selecting site and clicking "Toggle Site"
```

### Database Queries
```bash
# Show parts with multi-site data
uv run python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
parts = db.get_parts_with_sources(limit=10)
for part in parts:
    if part['site_name']:
        print(f'{part[\"brand\"]} {part[\"part_number\"]} - {part[\"site_name\"]} ({part[\"price\"]})')
"

# Show site performance metrics
uv run python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
perf = db.get_site_performance()
for site in perf:
    print(f'{site[\"site_name\"]:12} - {site[\"success_rate\"]:5.1f}% success, {site[\"total_scrapes\"]} scrapes')
"
```

## Data Processing Operations

### Quick Status Check
```bash
# Get comprehensive processing status across all sheets
uv run python src/count_results.py

# Expected output format:
# Sheet: [Name] | Processed: [N] | YES+LIKELY: [N] | UNCERTAIN: [N] | NO: [N]
# Grand Total: [processed]/[total] rows, [matches] confirmed matches
```

### Main Processing (Sequential - One Sheet at a Time)
```bash
# CRITICAL: Only process ONE sheet at a time to prevent Excel file corruption

# SMP Sheet (Highest ROI - 66.7% proven success rate)
uv run python src/excel_handler.py SMP --limit 200

# GMB Sheet (65.7% estimated success rate)
uv run python src/excel_handler.py GMB --limit 100

# Anchor Sheet
uv run python src/excel_handler.py Anchor --limit 100

# Dorman Sheet
uv run python src/excel_handler.py Dorman --limit 100

# Four Seasons Sheet (note: trailing space in name)
uv run python src/excel_handler.py "Four Seasons " --limit 50

# Test runs (smaller batches)
uv run python src/excel_handler.py SMP --limit 10
```

### Enhanced Image Analysis (UNCERTAIN Upgrade System)
```bash
# Process UNCERTAIN rows with 100% proven upgrade rate

# Enhanced analysis on specific sheets
uv run python src/run_enhanced_image_analysis.py Anchor --limit 50
uv run python src/run_enhanced_image_analysis.py Dorman --limit 50
uv run python src/run_enhanced_image_analysis.py GMB --limit 50

# Test with dry-run mode
uv run python src/run_enhanced_image_analysis.py Anchor --limit 5 --dry-run

# Process all UNCERTAIN rows on a sheet
uv run python src/run_enhanced_image_analysis.py Anchor --process-all-uncertain
```

### Background Processing (Production Mode)
```bash
# Run processes in background with logging

# Main processing (background)
PYTHONUNBUFFERED=1 uv run python -u src/excel_handler.py SMP --limit 200 > output/smp_batch.txt 2>&1 &

# Enhanced analysis (background)
PYTHONUNBUFFERED=1 uv run python -u src/run_enhanced_image_analysis.py Anchor --limit 50 > output/anchor_enhanced.txt 2>&1 &

# Monitor progress
tail -f output/smp_batch.txt
tail -f output/anchor_enhanced.txt

# Check background processes
ps aux | grep python | grep -v grep
```

## System Integration Operations

### Enterprise Systems Testing
```bash
# Test all 5 enhancement systems (expect 100% pass rate)
uv run python src/test_analytics_system.py      # Analytics module
uv run python src/test_web_interface.py         # Web interface
uv run python src/test_optimization_system.py   # Optimization engine
uv run python src/test_validation_system.py     # Validation framework
uv run python src/test_automation_system.py     # Automation platform
```

### Optimization Engine Usage
```bash
# Smart priority scheduling
uv run python src/optimization/priority_scheduler.py SMP --generate-schedule --target-rows 200

# Batch optimization analysis
uv run python src/optimization/batch_optimizer.py GMB --analyze-remaining --recommend-batch-size

# Predictive matching pre-screening
uv run python src/optimization/predictive_matching.py Dorman --analyze-remaining
```

### Analytics and Reporting
```bash
# Generate comprehensive analytics report
uv run python -c "
from src.analytics import Analytics
a = Analytics()
report = a.get_comprehensive_report()
print('Processing Status:', report['processing_status'])
print('Quality Score:', report['quality_analysis']['overall_grade'])
"

# Performance metrics
uv run python src/analytics/performance_metrics.py --system-check

# Data quality analysis
uv run python src/analytics/data_quality.py --generate-report --focus-areas processing_accuracy,system_performance
```

## Monitoring and Health Checks

### System Health Monitoring
```bash
# Deploy health monitoring
uv run python src/automation/health_monitor.py --start-monitoring --check-interval 300

# Check system resource usage
uv run python -c "
from src.analytics.performance_metrics import PerformanceTracker
p = PerformanceTracker()
print('CPU Usage:', p.get_cpu_usage())
print('Memory Usage:', p.get_memory_usage())
print('Chrome Processes:', p.count_chrome_processes())
"

# Network connectivity test
curl -s http://localhost:5000 > /dev/null && echo "Web dashboard accessible" || echo "Web dashboard not accessible"
```

### Process Management
```bash
# Clean shutdown of all processes (Windows)
taskkill //im python.exe //f 2>/dev/null || echo "No Python processes"
taskkill //im chrome.exe //f 2>/dev/null || echo "No Chrome processes"

# Check active processes
ps aux | grep -E "(python|chrome)" | grep -v grep | wc -l

# Clear browser locks (if needed)
rm -rf .browser_profile*/.tmp* 2>/dev/null || echo "No browser locks to clear"
```

### Log Monitoring
```bash
# Monitor various system logs
tail -f output/enhanced_analysis.log        # Enhanced image analysis
tail -f output/smp_batch.txt               # SMP processing
tail -f output/web_dashboard.log           # Web dashboard
tail -f output/chrome_scraper_debug.log    # Chrome scraper issues

# Check for error patterns
grep -i error output/*.txt | head -10
grep -i "failed" output/*.txt | head -10
```

## Data Backup and Recovery

### Excel File Management
```bash
# Create backup before major processing
cp "FISHER SKP INTERCHANGE 20260302.xlsx" "FISHER SKP INTERCHANGE 20260302.BACKUP.$(date +%Y%m%d_%H%M).xlsx"

# Emergency backup
cp "FISHER SKP INTERCHANGE 20260302.xlsx" "FISHER SKP INTERCHANGE 20260302.EMERGENCY.$(date +%H%M).xlsx"

# Restore from backup (if corruption occurs)
cp "FISHER SKP INTERCHANGE 20260302.BACKUP.xlsx" "FISHER SKP INTERCHANGE 20260302.xlsx"

# Verify file integrity
uv run python -c "
import openpyxl
try:
    wb = openpyxl.load_workbook('FISHER SKP INTERCHANGE 20260302.xlsx', read_only=True)
    print('Excel file is readable')
    print('Sheets:', wb.sheetnames)
except Exception as e:
    print('Excel file corrupted:', e)
"
```

### Data Validation
```bash
# Validate Excel schema
uv run python src/validation/data_validator.py --validate-schema --file "FISHER SKP INTERCHANGE 20260302.xlsx"

# Check data consistency
uv run python src/validation/result_validator.py --check-consistency --full-validation

# Detect anomalies
uv run python src/validation/anomaly_detector.py --scan-all-sheets --report-threshold 0.05
```

## Chrome Browser Management

### Browser Profile Maintenance
```bash
# Browser profile location: .browser_profile/
# NEVER DELETE - contains session cookies for anti-bot protection

# Check profile size
du -sh .browser_profile/

# Clear only temporary files (safe)
rm -rf .browser_profile/.tmp* 2>/dev/null

# Force browser restart (if hanging)
taskkill //im chrome.exe //f
# Profile will automatically recreate on next scraper run
```

### Scraper Testing
```bash
# Test Chrome scraper directly
uv run python -c "
from src.scraper_subprocess import scrape_rockauto_subprocess as scrape_rockauto
result = scrape_rockauto('3217', 'ANCHOR')
print('Found:', result['found'])
print('Category:', result.get('category', 'N/A'))
print('OEM Refs:', result.get('oem_refs', []))
"

# Test with known working part
uv run python -c "
from src.scraper_subprocess import scrape_rockauto_subprocess as scrape_rockauto
result = scrape_rockauto('SKM3217', 'SKP')
print('SKP Result:', result['found'], result.get('category', 'N/A'))
"
```

## Performance Optimization

### Optimized Processing Strategies
```bash
# Use optimized image pipeline (5-10x speed improvement)
uv run python src/optimized_image_pipeline_fixed.py Anchor --workers 4 --limit 50

# Performance estimation before processing
uv run python src/optimized_image_pipeline_fixed.py Dorman --estimate --limit 100

# Resource-aware batch processing
uv run python src/optimization/batch_optimizer.py SMP --optimize-batch-size --target-memory 80

# Dry-run mode for testing
uv run python src/optimized_image_pipeline_fixed.py Anchor --workers 4 --limit 25 --dry-run
```

### Memory and Resource Management
```bash
# Monitor resource usage during processing
uv run python -c "
import psutil
print('CPU Usage:', psutil.cpu_percent())
print('Memory Usage:', psutil.virtual_memory().percent)
print('Available Memory:', psutil.virtual_memory().available // (1024**3), 'GB')
"

# Chrome process monitoring
uv run python -c "
import psutil
chrome_procs = [p for p in psutil.process_iter() if 'chrome' in p.name().lower()]
print('Chrome Processes:', len(chrome_procs))
total_memory = sum(p.memory_info().rss for p in chrome_procs) // (1024**2)
print('Chrome Memory Usage:', total_memory, 'MB')
"
```

## Automation and Scheduling

### Automated Task Management
```bash
# Setup automated scheduling
uv run python src/automation/scheduler.py --configure --schedule "daily_processing" --time "02:00"

# Task queue management
uv run python src/automation/scheduler.py --list-tasks
uv run python src/automation/scheduler.py --run-task "enhanced_analysis" --sheet "Anchor"

# Notification system setup
uv run python src/automation/notification_system.py --configure --channels email,log --batch-completion-alerts
```

### Health Monitoring Automation
```bash
# Start continuous health monitoring
uv run python src/automation/health_monitor.py --start-daemon --alert-thresholds cpu:80,memory:85

# Manual health check
uv run python src/automation/health_monitor.py --health-check --report

# Alert testing
uv run python src/automation/notification_system.py --test-alert --message "System health check"
```

## Development and Testing

### Test Suite Execution
```bash
# Run comprehensive test suites
uv run python -m pytest src/test_*.py -v

# Individual system tests
uv run python src/test_enhanced_comparison.py    # Enhanced image system
uv run python src/test_analytics_system.py      # Analytics module
uv run python src/test_web_interface.py         # Web dashboard
```

### Debug Mode Operations
```bash
# Enable debug logging
export DEBUG=true
uv run python src/excel_handler.py SMP --limit 10

# Chrome scraper with debug output
uv run python -c "
import os
os.environ['DEBUG'] = 'true'
from src.scraper_subprocess import scrape_rockauto_subprocess as scrape
result = scrape('3217', 'ANCHOR')
"

# Performance profiling
uv run python -c "
import time
from src.analytics.performance_metrics import PerformanceTracker
p = PerformanceTracker()
start = time.time()
# ... run operation ...
end = time.time()
print('Processing time:', end - start)
"
```

## Emergency Procedures

### System Recovery
```bash
# Complete system reset (emergency)
1. Stop all processes: taskkill //im python.exe //f; taskkill //im chrome.exe //f
2. Restore Excel: cp BACKUP.xlsx ORIGINAL.xlsx
3. Clear temp files: rm -rf .browser_profile/.tmp*
4. Restart: uv run python main_app.py

# File corruption recovery
1. Detect: uv run python src/count_results.py (will error if corrupted)
2. Backup: cp current.xlsx corrupted_$(date +%H%M).xlsx
3. Restore: cp BACKUP.xlsx current.xlsx
4. Verify: uv run python src/count_results.py
```

### Common Issues Resolution
```bash
# Excel file locked
lsof "FISHER SKP INTERCHANGE 20260302.xlsx" || echo "File not locked"
# Solution: Stop all Python processes, wait 10 seconds, retry

# Chrome hanging
ps aux | grep chrome | grep -v grep
# Solution: taskkill //im chrome.exe //f

# Memory exhaustion
free -h  # Check available memory
# Solution: Reduce batch size, restart system if needed

# API quota exceeded (Gemini)
grep "429" output/*.txt
# Solution: Use local Ollama, wait for daily reset
```

This operations guide covers all essential commands and procedures for running and maintaining the Parts Agent system in production.