---
name: Update GP Suppliers Data
description: Download and process latest NHS appointments data to update GP-to-IT-supplier mappings
---

# Update GP Suppliers Data

## Goal

Download the latest NHS Appointments in General Practice data and process it to create/update a CSV file mapping GP practice ODS codes to their IT system suppliers (TPP, EMIS, etc.).

## When to Use

- **Monthly**: NHS Digital publishes new appointments data monthly
- **On-demand**: When you need the latest GP supplier information
- **Initial setup**: First time setting up the GP supplier database

## Inputs

- **Month** (optional): ISO format month string (e.g. `2025-01`, `2024-12`)
  - If not provided, defaults to previous month
- **Zip File URL** (optional): Direct link to NHS data zip file
  - Use this to bypass CloudFlare blocking issues
  - Find URLs at: https://digital.nhs.uk/data-and-information/publications/statistical/appointments-in-general-practice

## Tools

- `execution/download_gpad.py` - Main script for downloading and processing data

## Outputs

- `execution/data/gp_suppliers_YYYY-MM.csv` - Updated CSV file with columns:
  - `GP_ODS_CODE` - Unique GP practice identifier
  - `GP_NAME` - GP practice name
  - `GP_GPAD_SYSTEMS` - All appointment systems used (may include multiple)
  - `GP_SYSTEM` - Primary IT system (TPP, EMIS, etc.)
- `execution/data/icb_gp_suppliers_YYYY-MM.csv` - Enriched CSV file with ICB Sub location:
  - `ICB Sub location` - The commissioner/ICB code (added first)
  - All columns from `gp_suppliers_YYYY-MM.csv`

## Process

### Standard Update (with direct URL)

1. Find the latest data URL from NHS Digital website
2. Run the download script with the URL:
   ```powershell
   python execution/download_gpad.py --month 2025-01 --zip-file https://files.digital.nhs.uk/[URL]
   ```

### Automatic Update (may fail due to CloudFlare)

1. Run the download script without URL (will attempt to scrape NHS website):
   ```powershell
   python execution/download_gpad.py --month 2025-01
   ```

### Default to Previous Month

1. Run without specifying month:
   ```powershell
   python execution/download_gpad.py
   ```

2. Run the enrichment script to add ICB Sub location data (specify same month if needed):
   ```powershell
   python execution/enrich_gp_data.py --month 2025-01
   ```

## Edge Cases

### CloudFlare Blocking

**Issue**: NHS Digital website uses CloudFlare protection which may block automated requests.

**Solution**: Use the `--zip-file` parameter with a direct URL to the zip file.

**How to find URL**:
1. Visit https://digital.nhs.uk/data-and-information/publications/statistical/appointments-in-general-practice/[month]-[year]
2. Look for "Annex 1 - Practice Level Crosstab" CSV download
3. Right-click and copy the download link
4. Use this URL with `--zip-file` parameter

### Missing Data Files

**Issue**: Extracted zip doesn't contain expected CSV files.

**Symptoms**: Error message "No data files found for [month]"

**Solution**: 
- Verify the month format is correct (YYYY-MM)
- Check that the zip file contains "Practice_Level_Crosstab_*_[Mon]_[YY].csv" files
- Ensure you're downloading the correct Annex 1 file (not Annex 2 or other variants)

### Data Format Changes

**Issue**: NHS Digital changes the CSV format or column positions.

**Symptoms**: Missing data, incorrect mappings, or parsing errors

**Solution**:
- Review the CSV structure in `.tmp/[month]/` before cleanup
- Update `execution/download_gpad.py` line 220-225 to match new column positions
- Update `execution/helpers.py` if system identification logic changes

### Multiple Systems per Practice

**Issue**: Some GP practices use multiple IT systems (e.g. "EVERGREENLIFE/TPP")

**Handling**: The `get_main_system_from_value()` function in `helpers.py` filters out EVERGREENLIFE and returns the primary system.

## Verification

After running the update:

1. **Check files exist**:
   ```powershell
   Test-Path "execution\data\gp_suppliers_2025-01.csv"
   Test-Path "execution\data\icb_gp_suppliers_2025-01.csv"
   ```

2. **Verify row count** (should be 6000+):
   ```powershell
   (Get-Content "execution\data\icb_gp_suppliers_2025-01.csv" | Measure-Object -Line).Lines
   ```

3. **Check a sample record**:
   *Note: gp_lookup.py should be updated locally if it still expects a static filename.*
   ```powershell
   python execution/gp_lookup.py --ods-code A81001
   ```

4. **View statistics**:
   ```powershell
   python execution/gp_lookup.py --stats
   ```

## Automation

To automate monthly updates, you could:
- Set up a scheduled task (Windows Task Scheduler)
- Use a cron job (if running on Linux)
- Create a GitHub Action workflow

**Note**: Due to CloudFlare blocking, fully automated updates may require additional setup (e.g., using a headless browser or manual URL provision).

## Related Directives

- `lookup_gp_supplier.md` - How to query the GP supplier data
