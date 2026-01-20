"""
GP Data Enrichment Script

Enriches the GP suppliers data with ICB Sub location information.
1. Reads execution/data/gp_suppliers.csv
2. Checks execution/data/GP to ICB Sub location - Map.csv
3. If missing, queries NHS ODS API for 'Commissioned By' relationship
4. Updates the Map csv
5. Outputs execution/data/icb_gp_suppliers.csv
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
MAP_FILE = "execution/data/GP to ICB Sub location - Map.csv"
ODS_API_URL = "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
RATE_LIMIT_DELAY = 0.2  # Seconds between API calls

def load_map(map_file):
    """Load the GP to ICB map into a dictionary."""
    mapping = {}
    if not os.path.exists(map_file):
        logger.warning(f"Map file {map_file} not found. Starting with empty map.")
        return mapping

    with open(map_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Map file has ICB Sub location,GP_ODS_CODE
            # distinct from the order, we want ODS -> ICB
            if 'GP_ODS_CODE' in row and 'ICB Sub location' in row:
                mapping[row['GP_ODS_CODE']] = row['ICB Sub location']
    return mapping

def append_to_map(map_file, ods_code, icb_code):
    """Append a new mapping to the CSV file."""
    file_exists = os.path.exists(map_file)
    with open(map_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
             writer.writerow(['ICB Sub location', 'GP_ODS_CODE'])
        writer.writerow([icb_code, ods_code])

def get_commissioner_code(ods_code):
    """
    Query NHS ODS API to find the commissioner code for a GP practice.
    Looking for 'Commissioned By' relationship (RE4).
    """
    url = f"{ODS_API_URL}/{ods_code}"
    try:
        response = requests.get(url)
        if response.status_code == 429:
            logger.warning("Rate limit hit. Waiting 5 seconds...")
            time.sleep(5)
            response = requests.get(url)
        
        if response.status_code == 404:
            logger.warning(f"ODS Code {ods_code} not found in API.")
            return None
            
        response.raise_for_status()
        data = response.json()
        
        # Check relationships
        if 'Organisation' in data and 'Rels' in data['Organisation']:
            rels_container = data['Organisation']['Rels']
            
            # The API returns 'Rel' list inside the Rels object
            # But sometimes it might be just a single object if there's only one? 
            # Usually strict JSON structure maintains list, but let's be safe.
            if isinstance(rels_container, dict) and 'Rel' in rels_container:
                relationships = rels_container['Rel']
                
                # Ensure it's a list
                if not isinstance(relationships, list):
                    relationships = [relationships]
                    
                for rel in relationships:
                    # RE4 is "Commissioned By"
                    if rel.get('Status') == 'Active' and rel.get('id') == 'RE4':
                        target = rel.get('Target')
                        if target:
                            org_id = target.get('OrgId', {})
                            if isinstance(org_id, dict):
                                return org_id.get('extension')
        
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"API Request failed for {ods_code}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing API response for {ods_code}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Enrich GP supplier data with ICB information")
    parser.add_argument("--month", type=str, help="The month of the data to process (e.g. 2025-01)")
    args = parser.parse_args()

    # If no month is provided, use the previous month
    if args.month is None:
        args.month = (datetime.now() - relativedelta(months=1)).strftime("%Y-%m")
        logger.info(f"No month specified, using previous month: {args.month}")
    
    month = args.month
    gp_suppliers_file = f"execution/data/gp_suppliers_{month}.csv"
    output_file = f"execution/data/icb_gp_suppliers_{month}.csv"

    logger.info(f"Starting enrichment process for {month}...")
    
    # 1. Load Data
    if not os.path.exists(gp_suppliers_file):
        logger.error(f"{gp_suppliers_file} not found. Ensure the download script has been run for this month.")
        sys.exit(1)
        
    ods_map = load_map(MAP_FILE)
    logger.info(f"Loaded {len(ods_map)} mappings.")
    
    processed_count = 0
    api_calls = 0
    
    new_rows = []
    
    with open(gp_suppliers_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = ['ICB Sub location'] + reader.fieldnames
        
        for row in reader:
            ods_code = row['GP_ODS_CODE']
            icb_code = ods_map.get(ods_code)
            
            if not icb_code:
                logger.info(f"Lookup code for {ods_code}...")
                icb_code = get_commissioner_code(ods_code)
                api_calls += 1
                time.sleep(RATE_LIMIT_DELAY)
                
                if icb_code:
                    logger.info(f"Found code {icb_code} for {ods_code}.")
                    ods_map[ods_code] = icb_code
                    append_to_map(MAP_FILE, ods_code, icb_code)
                else:
                    logger.warning(f"Could not find ICB code for {ods_code}")
                    icb_code = "UNKNOWN"
            
            row['ICB Sub location'] = icb_code
            new_rows.append(row)
            processed_count += 1
            
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count} records...")

    # Output
    logger.info(f"Writing result to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)
        
    logger.info(f"Enrichment complete for {month}.")

if __name__ == "__main__":
    main()
