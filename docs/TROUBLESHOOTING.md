# Parts Agent - Troubleshooting Guide

## Common Issues and Solutions

### Excel File Issues

#### Excel File Corruption
**Symptoms:**
```
zipfile.BadZipFile: Bad magic number for central directory
PermissionError: [WinError 32] The process cannot access the file
```

**Cause:** Multiple processes accessing Excel file simultaneously

**Solution:**
```bash
# 1. Stop all processes
taskkill //im python.exe //f
taskkill //im chrome.exe //f

# 2. Check for backup files
ls -la FISHER\ SKP\ INTERCHANGE*.xlsx

# 3. Restore from backup
cp "FISHER SKP INTERCHANGE 20260302.BACKUP.xlsx" "FISHER SKP INTERCHANGE 20260302.xlsx"

# 4. Verify integrity
uv run python -c "
import openpyxl
wb = openpyxl.load_workbook('FISHER SKP INTERCHANGE 20260302.xlsx', read_only=True)
print('File restored successfully, sheets:', wb.sheetnames)
"
```

**Prevention:**
- **Never run multiple Excel processes simultaneously**
- Always use sequential processing (one sheet at a time)
- Create backups before major operations

#### Excel File Locked
**Symptoms:**
```
[WinError 32] The process cannot access the file because it is being used by another process
```

**Diagnosis:**
```bash
# Check for active Python processes
ps aux | grep python | grep -v grep

# Check for Excel temp files
ls -la *.tmp
```

**Solution:**
```bash
# Stop all Python processes
taskkill //im python.exe //f

# Remove temp files
rm -f *.tmp

# Wait 10 seconds, then retry
sleep 10
uv run python src/count_results.py
```

### Chrome Browser Issues

#### Chrome Processes Hanging
**Symptoms:**
- Scraper timeouts after 45+ seconds
- Multiple Chrome processes accumulating
- High memory usage

**Diagnosis:**
```bash
# Check Chrome process count
ps aux | grep chrome | grep -v grep | wc -l

# Check Chrome memory usage
ps aux | grep chrome | awk '{sum+=$6} END {print sum/1024 " MB"}'
```

**Solution:**
```bash
# Kill all Chrome processes
taskkill //im chrome.exe //f

# Clear browser profile locks
rm -rf .browser_profile/.tmp* 2>/dev/null

# Restart processing (Chrome will auto-restart)
uv run python src/excel_handler.py SMP --limit 10
```

#### Browser Profile Issues
**Symptoms:**
- Chrome fails to start
- "Profile in use" errors
- Scraper immediately fails

**Solution:**
```bash
# Clear profile locks (KEEP the profile directory)
rm -rf .browser_profile/.tmp*
rm -rf .browser_profile/SingletonLock*
rm -rf .browser_profile/lockfile

# DO NOT DELETE the entire .browser_profile/ directory
# It contains accumulated cookies for anti-bot protection
```

### AI/ML Model Issues

#### llava-phi3 Model Broken
**Symptoms:**
```
Assertion failed: found, file llama-sampling.cpp, line 660
```

**Cause:** Known issue with Ollama v0.18.0

**Solution:**
```bash
# Switch to moondream model (already configured)
uv run python -c "
from src.local_vision import check_ollama, compare_images_ollama
status = check_ollama()
print('Ollama status:', status)
print('Preferred model: moondream')
"

# moondream model works perfectly (828MB, unlimited processing)
```

#### Gemini API Quota Exhausted
**Symptoms:**
```
429 Quota exceeded for quota metric 'Generate Content API requests per day'
```

**Automatic Handling:**
- System auto-disables Gemini for rest of session
- Falls back to rule-based results
- Resets daily automatically

**Manual Check:**
```bash
# Check quota status
uv run python -c "
import google.generativeai as genai
try:
    model = genai.GenerativeModel('gemini-3-flash-preview')
    # Test request
    response = model.generate_content('test')
    print('Gemini API working')
except Exception as e:
    print('Gemini quota exhausted:', e)
"
```

### Network and Connectivity Issues

#### RockAuto Website Issues
**Symptoms:**
- "Part not found" for known valid parts
- Scraper timeouts
- Category parsing returns "Continue Shopping"

**Diagnosis:**
```bash
# Test connectivity
curl -s https://www.rockauto.com | head -5

# Test scraper with known working part
uv run python -c "
from src.scraper_subprocess import scrape_rockauto_subprocess as scrape
result = scrape('3217', 'ANCHOR')  # Known working test case
print('Test result:', result['found'], result.get('error', 'No error'))
"
```

**Solutions:**
1. **Wait and Retry:** RockAuto may have temporary issues
2. **Check Internet:** Verify network connectivity
3. **Browser Restart:** Kill Chrome processes and retry
4. **Reduce Batch Size:** Use smaller limits to avoid rate limiting

#### ShowMeTheParts (Stealth Bypass Required)
**Status:** Requires Incapsula WAF stealth bypass — 446-line scraper exists at `src/scrapers/showmetheparts_scraper.py`

**Error Messages (without stealth):**
```
Access denied (16)
Request ID: [various]
```

**Solution:**
- Use stealth scraper at `src/scrapers/showmetheparts_scraper.py` (Playwright stealth with Incapsula bypass)
- Scraper needs testing and validation before production use
- Old `scraper_anchor.py` is deprecated dead code

### Processing Performance Issues

#### Slow Processing Speed
**Symptoms:**
- Processing takes >30 seconds per row
- Chrome hangs frequently
- High resource usage

**Optimization:**
```bash
# Use optimized processing pipeline
uv run python src/optimized_image_pipeline_fixed.py Anchor --workers 4

# Monitor resource usage
uv run python -c "
import psutil
print('CPU:', psutil.cpu_percent(), '%')
print('Memory:', psutil.virtual_memory().percent, '%')
"

# Reduce batch sizes for lower-spec systems
uv run python src/excel_handler.py SMP --limit 25  # Instead of 200
```

#### Memory Exhaustion
**Symptoms:**
```
MemoryError
System becomes unresponsive
Chrome crashes repeatedly
```

**Solution:**
```bash
# Check available memory
uv run python -c "
import psutil
mem = psutil.virtual_memory()
print('Available:', mem.available // (1024**3), 'GB')
print('Usage:', mem.percent, '%')
"

# Immediate fixes:
# 1. Reduce batch sizes
uv run python src/excel_handler.py SMP --limit 10

# 2. Kill unnecessary processes
taskkill //im chrome.exe //f

# 3. Use resource monitoring
uv run python src/analytics/performance_metrics.py --monitor-resources
```

### Image Analysis Issues

#### Image URLs Not Found
**Symptoms:**
- "No images available for comparison"
- Enhanced analysis skipping rows

**Cause:** RockAuto parts don't always have product images

**Expected Behavior:**
- ~60% of parts have images available
- System gracefully handles missing images
- Still processes based on text comparison

**Verification:**
```bash
# Check image availability
uv run python -c "
from src.scraper_subprocess import scrape_rockauto_subprocess as scrape
result = scrape('3217', 'ANCHOR')
print('Image URL:', result.get('image_url', 'Not available'))
"
```

#### CLIP Model Loading Issues
**Symptoms:**
```
RuntimeError: CLIP model failed to load
torch.cuda.CUDAError
```

**Solutions:**
```bash
# 1. Check CLIP installation
uv run python -c "
import clip
import torch
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model, preprocess = clip.load('ViT-B/32', device=device)
print('CLIP loaded successfully on:', device)
"

# 2. Fallback to CPU if CUDA issues
# (Automatically handled in image_compare_enhanced.py)

# 3. Check GPU memory (if using CUDA)
nvidia-smi  # If available
```

### GUI and Interface Issues

#### Desktop GUI Won't Start
**Symptoms:**
```
tkinter.TclError: no display name and no $DISPLAY environment variable
ModuleNotFoundError: No module named 'tkinter'
```

**Solutions:**
```bash
# 1. Check tkinter availability (built-in with Python)
uv run python -c "import tkinter; print('tkinter available')"

# 2. On Windows, ensure proper Python installation
# tkinter should be included with Python 3.14

# 3. Alternative: Use web interface
uv run python src/launch_web_dashboard.py
# Access at http://localhost:5000
```

#### Web Dashboard Not Accessible
**Symptoms:**
- http://localhost:5000 not loading
- Connection refused errors

**Diagnosis:**
```bash
# Check if Flask app is running
ps aux | grep flask
netstat -an | grep :5000
```

**Solution:**
```bash
# Start web dashboard
uv run python src/launch_web_dashboard.py

# Check startup logs
tail -f output/web_dashboard.log

# Test connectivity
curl -s http://localhost:5000 && echo "Dashboard accessible"
```

### Data Quality Issues

#### Inconsistent Results
**Symptoms:**
- Same parts getting different results on different runs
- Confidence scores varying significantly

**Diagnosis:**
```bash
# Run data validation
uv run python src/validation/data_validator.py --check-consistency

# Check for anomalies
uv run python src/validation/anomaly_detector.py --scan-sheet Anchor

# Analyze confidence patterns
uv run python -c "
from src.analytics.data_quality import DataQualityAnalyzer
dqa = DataQualityAnalyzer('FISHER SKP INTERCHANGE 20260302.xlsx')
report = dqa.analyze_confidence_distribution()
print('Confidence analysis:', report)
"
```

#### Low Match Rates
**Symptoms:**
- Success rates <30% on new sheets
- Many UNCERTAIN results
- Few YES/LIKELY matches

**Analysis:**
```bash
# Check rule engine performance
uv run python -c "
from src.analytics.stats_engine import StatsEngine
se = StatsEngine('FISHER SKP INTERCHANGE 20260302.xlsx')
stats = se.get_processing_stats()
for sheet, data in stats.items():
    if data['processed'] > 0:
        success_rate = (data['yes'] + data['likely']) / data['processed'] * 100
        print(f'{sheet}: {success_rate:.1f}% success rate')
"

# Optimize processing parameters
uv run python src/optimization/priority_scheduler.py --analyze-success-patterns
```

## Error Code Reference

### Common Error Codes and Meanings

| Code | Error Type | Meaning | Solution |
|------|------------|---------|----------|
| WinError 32 | File Access | Excel file locked | Stop processes, retry |
| WinError 5 | Permission | Access denied | Run as administrator |
| 429 | API Quota | Gemini quota exceeded | Use local Ollama |
| BadZipFile | Corruption | Excel file corrupt | Restore from backup |
| TimeoutError | Network | Scraper timeout | Reduce batch size |
| MemoryError | Resources | Out of memory | Reduce workers/batch |

### Log File Patterns

#### Success Patterns
```
[OK] Excel updated successfully
-> UPGRADE to LIKELY (score: 0.XX, MEDIUM)
Success rate: 100.0% of processable rows
CLIP model loaded successfully
```

#### Warning Patterns
```
Chrome subprocess timeout
Gemini quota exhausted - falling back to rules
No images available for comparison
Category parsing returned: Continue Shopping
```

#### Error Patterns
```
[ERROR] Failed to update Excel
Chrome failed to start after 3 attempts
Assertion failed: found, file llama-sampling.cpp
Bad magic number for central directory
```

## Recovery Procedures

### Complete System Reset
```bash
# Emergency reset sequence
1. taskkill //im python.exe //f
2. taskkill //im chrome.exe //f
3. rm -rf .browser_profile/.tmp*
4. cp "FISHER SKP INTERCHANGE 20260302.BACKUP.xlsx" "FISHER SKP INTERCHANGE 20260302.xlsx"
5. uv run python src/count_results.py  # Verify
6. uv run python main_app.py  # Restart
```

### Partial Recovery (Processing Issues)
```bash
# For processing hangs/errors
1. Stop current process: Ctrl+C or taskkill
2. Check Excel integrity: uv run python src/count_results.py
3. Clear Chrome: taskkill //im chrome.exe //f
4. Reduce batch size: --limit 10
5. Resume processing
```

### Data Recovery (File Corruption)
```bash
# For Excel corruption
1. Identify corruption: count_results.py fails
2. Create incident backup: cp current.xlsx corrupted_$(date).xlsx
3. Restore clean backup: cp BACKUP.xlsx current.xlsx
4. Verify restoration: count_results.py succeeds
5. Resume from clean state
```

## Performance Tuning

### System Requirements
- **Minimum**: 8GB RAM, 4-core CPU, 10GB disk space
- **Recommended**: 16GB+ RAM, 8-core CPU, RTX GPU for CLIP
- **Optimal**: 32GB RAM (current setup), RTX 2070+ GPU

### Batch Size Guidelines
```bash
# System Resource Based Batch Sizes:
# 8GB RAM:  --limit 10-25
# 16GB RAM: --limit 25-50
# 32GB RAM: --limit 50-200 (current setup)

# Processing Type Based:
# Main processing: --limit 50-200
# Enhanced analysis: --limit 25-50 (more resource intensive)
# Testing: --limit 5-10
```

### Monitoring Commands
```bash
# Real-time resource monitoring
watch -n 2 "ps aux | grep python; echo; free -h; echo; df -h"

# Chrome process monitoring
watch -n 5 "ps aux | grep chrome | wc -l; echo 'Chrome processes'"

# Processing progress monitoring
tail -f output/processing_log.txt | grep -E "(UPGRADE|ERROR|SUCCESS)"
```

## Multi-Site System Issues (Phase 1 Complete)

### Database Issues

#### Database Not Found
**Symptoms:**
```
[ERROR] Database file not found at: C:\Users\Owner\Desktop\Parts Agent 20260313\data\parts_agent.db
```

**Solution:**
```bash
# Initialize database
uv run python src/database/db_manager.py

# Verify creation
uv run python src/verify_database_status.py
```

#### Missing Database Tables
**Symptoms:**
```
sqlite3.OperationalError: no such table: parts
```

**Solution:**
```bash
# Recreate schema
rm -f data/parts_agent.db
uv run python src/database/db_manager.py

# Verify all tables created
uv run python src/verify_database_status.py
```

### Multi-Site Scraper Issues

#### Multi-Site Manager Not Available
**Symptoms:**
```
[ERROR] Multi-site manager not available
Multi-site functionality not available - multi-site features disabled
```

**Diagnosis:**
```bash
# Check imports
uv run python -c "
try:
    from src.scrapers.multi_site_manager import MultiSiteScraperManager
    print('[OK] Multi-site manager imports successfully')
except Exception as e:
    print(f'[ERROR] Import failed: {e}')
"
```

**Solution:**
```bash
# Verify file exists
ls -la src/scrapers/multi_site_manager.py

# Test integration
uv run python src/test_multi_site_integration.py
```

#### Site Configuration Issues
**Symptoms:**
- Sites showing as INACTIVE in GUI
- No sites available for selection
- Rate limiting errors

**Diagnosis:**
```bash
# Check site configurations
uv run python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
configs = db.get_site_configs()
print(f'Found {len(configs)} site configurations')
for cfg in configs:
    print(f'  {cfg[\"site_name\"]}: {\"ACTIVE\" if cfg[\"is_active\"] else \"INACTIVE\"}')
"
```

**Solution:**
```bash
# Reinitialize site configs
uv run python src/database/db_manager.py

# Manually activate sites via GUI Multi-Site tab
# Select site -> Click "Toggle Site"
```

### GUI Integration Issues

#### Multi-Site Tab Not Visible
**Symptoms:**
- Multi-Site tab missing from main GUI
- GUI launches but no multi-site functionality

**Diagnosis:**
```bash
# Check GUI integration
uv run python -c "
from src.gui.main_window import MULTI_SITE_AVAILABLE
print(f'Multi-site available: {MULTI_SITE_AVAILABLE}')
"
```

**Solution:**
```bash
# Verify multi-site tab file
ls -la src/gui/multi_site_tab.py

# Test standalone
uv run python src/gui/multi_site_tab.py

# Restart main GUI
uv run python main_app.py
```

#### Search Not Working
**Symptoms:**
- "Search All Sites" button disabled
- No results returned from multi-site search

**Diagnosis:**
```bash
# Test direct multi-site search
uv run python src/scrapers/multi_site_manager.py

# Check RockAuto integration
uv run python -c "
from src.scraper_subprocess import scrape_rockauto_subprocess
result = scrape_rockauto_subprocess('3217', 'ANCHOR')
print(f'RockAuto test: {result.get(\"found\", False)}')
"
```

**Solution:**
```bash
# Ensure at least one site selected in GUI
# Verify part number and brand entered
# Check Chrome processes not hanging (kill if needed)
taskkill //im chrome.exe //f
```

### Performance Issues

#### Multi-Site Searches Slow
**Symptoms:**
- Long delays during cross-site search
- GUI freezing during multi-site operations

**Optimization:**
```bash
# Reduce number of sites searched simultaneously
# Check rate limiting delays in database:
uv run python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
configs = db.get_site_configs()
for cfg in configs:
    print(f'{cfg[\"site_name\"]}: {cfg[\"rate_limit_delay\"]}s delay')
"

# Increase delays if needed (via database update)
```

#### Database Growing Large
**Symptoms:**
```bash
# Check database size
ls -lh data/parts_agent.db
```

**Maintenance:**
```bash
# Clean up test data
uv run python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
db.execute_query('DELETE FROM parts WHERE part_number LIKE \"TEST%\"')
db.execute_query('DELETE FROM scrape_log WHERE search_term LIKE \"TEST%\"')
"

# Backup database
uv run python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager()
success = db.backup_database()
print(f'Backup created: {success}')
"
```

## Recovery Procedures (Updated for Multi-Site)

### Complete Multi-Site Reset
```bash
# Full multi-site system reset
1. Stop all processes: taskkill //im python.exe //f; taskkill //im chrome.exe //f
2. Backup database: cp data/parts_agent.db data/parts_agent.backup.db
3. Reinitialize: uv run python src/database/db_manager.py
4. Test: uv run python src/test_multi_site_integration.py
5. Launch: uv run python main_app.py
```

This troubleshooting guide covers the most common issues and their solutions based on actual operational experience with the Parts Agent system, including the new multi-site capabilities.