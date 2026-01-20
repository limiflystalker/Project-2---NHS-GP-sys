"""
Download and process GP supplier data from NHS Appointments in General Practice

This script downloads NHS appointments data, extracts GP practice information,
and generates a CSV mapping GP ODS codes to their IT system suppliers.

Adapted for 3-layer architecture:
- Uses .tmp/ for intermediate files
- Outputs to execution/data/ for persistent storage
- Enhanced error handling and logging

Usage:
    python execution/download_gpad.py --month 2025-01
    python execution/download_gpad.py --month 2025-01 --zip-file https://files.digital.nhs.uk/[URL]
"""

import argparse
import csv
from datetime import datetime
import logging
import os
from pathlib import Path
import shutil
import sys
import zipfile

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
import requests

# Add execution directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import (
    get_data_file_paths,
    get_main_system_from_value,
    get_month_and_year_from_iso_month,
)

# Configuration
BASE_URL = "https://digital.nhs.uk/data-and-information/publications/statistical/appointments-in-general-practice"
TMP_DIR = ".tmp"

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main(month: str, zip_file: str = None):
    """
    Main execution function for downloading and processing GP supplier data
    
    Args:
        month: ISO month string (e.g. "2025-01")
        zip_file: Optional direct URL to zip file (bypasses NHS website scraping)
    """
    logger.info(f"Starting GP supplier data update for {month}")
    
    try:
        download_gpad_zip_file(month, zip_file)
    except Exception as e:
        logger.error(f"Error downloading zip file: {e}")
        raise e

    try:
        unzip_dir = unzip_gpad_zip_file(month)
    except Exception as e:
        logger.error(f"Error unzipping zip file: {e}")
        raise e

    input_file_paths = get_data_file_paths(unzip_dir, month)
    logger.info(f"Found {len(input_file_paths)} data files")

    if len(input_file_paths) == 0:
        raise Exception(f"No data files found for {month}. Check the extracted zip contents.")

    try:
        data, gp_code_to_name = process_data_files(input_file_paths)
    except Exception as e:
        logger.error(f"Error processing data file: {e}")
        raise e

    try:
        output_file = f"execution/data/gp_suppliers_{month}.csv"
        write_output_file(data, gp_code_to_name, output_file)
    except Exception as e:
        logger.error(f"Error writing output file: {e}")
        raise e

    try:
        remove_tmp_files(month)
    except Exception as e:
        logger.error(f"Error removing temporary files: {e}")
        raise e

    logger.info(f"✓ Completed processing data for {month}")
    logger.info(f"✓ Output written to {output_file}")
    logger.info(f"✓ Total GP practices: {len(data)}")


def download_gpad_zip_file(iso_month: str, zip_file_path: str = None):
    """
    Download the GPAD suppliers zip data for a given month
    from the NHS Digital website
    
    Args:
        iso_month: ISO month string (e.g. "2025-01")
        zip_file_path: Optional direct URL to zip file
    """
    # Ensure tmp directory exists
    os.makedirs(TMP_DIR, exist_ok=True)
    
    month, year = get_month_and_year_from_iso_month(iso_month)
    url = f"{BASE_URL}/{month}-{year}"

    if zip_file_path is None:
        logger.info(f"Finding download link for {iso_month} from {url}")
        response = requests.get(url)
        response.raise_for_status()

        try:
            download_link = get_download_link_from_response(response)
        except Exception as e:
            raise Exception(f"Error getting download link: {e}")
    else:
        logger.info(
            f"Skipping finding download link and using provided zip file path: {zip_file_path}"
        )
        download_link = zip_file_path

    logger.info(f"Downloading zip file from {download_link}")
    response = requests.get(download_link)
    response.raise_for_status()

    zip_path = os.path.join(TMP_DIR, f"{iso_month}.zip")
    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"Downloaded zip file to {zip_path}")


def get_download_link_from_response(response: requests.Response):
    """
    Extract the download link for Annex 1 CSV from NHS Digital page
    
    Args:
        response: HTTP response from NHS Digital website
        
    Returns:
        URL to the zip file
    """
    soup = BeautifulSoup(response.content, "html.parser")
    downloads = soup.select("div.nhsd-m-download-card")

    for download in downloads:
        download_title = download.find("p").text
        if "Annex 1" in download_title and "CSV" in download_title:
            return download.find("a").get("href")

    if len(downloads) == 0:
        raise Exception("No downloads found.")
    else:
        raise Exception(
            f"Found {len(downloads)} downloads. No Annex 1 CSV downloads found."
        )


def unzip_gpad_zip_file(month: str):
    """
    Unzip the downloaded GPAD data file
    
    Args:
        month: ISO month string (e.g. "2025-01")
        
    Returns:
        Path to the unzipped directory
    """
    unzip_dir = os.path.join(TMP_DIR, month)
    if not os.path.exists(unzip_dir):
        os.makedirs(unzip_dir)
    
    zip_path = os.path.join(TMP_DIR, f"{month}.zip")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(unzip_dir)

    logger.info(f"Unzipped zip file to {unzip_dir}")

    return unzip_dir


def process_data_files(input_file_paths: list[str]):
    """
    Process CSV data files to extract GP supplier information
    
    Args:
        input_file_paths: List of paths to CSV files
        
    Returns:
        Tuple of (data dict, gp_code_to_name dict)
    """
    data = {}
    gp_code_to_name = {}

    for input_file_path in input_file_paths:
        logger.info(f"Processing data file: {input_file_path}")
        with open(input_file_path, "r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for index, row in enumerate(reader):
                if index == 0:
                    continue

                # CSV format: [?, GP_ODS_CODE, GP_NAME, APPOINTMENTS_SYSTEMS, ...]
                if len(row) < 4:
                    continue
                    
                gp_code = row[1]
                gp_name = row[2]
                appointments_systems = row[3]
                
                main_system = get_main_system_from_value(appointments_systems)

                if gp_code not in data:
                    data[gp_code] = (appointments_systems, main_system)

                if gp_code not in gp_code_to_name:
                    gp_code_to_name[gp_code] = gp_name

    # Sort the data alphabetically by GP code
    # to ensure the output file can be compared more easily over time
    data = dict(sorted(data.items()))

    return data, gp_code_to_name


def write_output_file(data: dict, gp_code_to_name: dict, output_file: str):
    """
    Write the output CSV file with GP supplier mappings

    Args:
        data: A dictionary of GP codes to their appointment systems and main system
        gp_code_to_name: A dictionary of GP codes to their names
        output_file: Path to the output CSV file
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["GP_ODS_CODE", "GP_NAME", "GP_GPAD_SYSTEMS", "GP_SYSTEM"])
        for gp_code, (appointment_systems, main_system) in data.items():
            writer.writerow(
                [gp_code, gp_code_to_name[gp_code], appointment_systems, main_system]
            )
    logger.info(f"Written output file: {output_file}")


def remove_tmp_files(month: str):
    """
    Remove the temporary files for a given month
    
    Args:
        month: ISO month string (e.g. "2025-01")
    """
    zip_file_path = os.path.join(TMP_DIR, f"{month}.zip")
    if os.path.exists(zip_file_path):
        Path(zip_file_path).unlink()
    
    unzip_dir = os.path.join(TMP_DIR, month)
    if os.path.exists(unzip_dir):
        shutil.rmtree(unzip_dir)
    
    logger.info(f"Removed temporary files for {month}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download the Appointments in General Practice data"
    )

    parser.add_argument(
        "--month",
        type=str,
        help="The month to download the data for (e.g. 2025-01)",
    )

    parser.add_argument(
        "--zip-file",
        type=str,
        help="The path to the zip file to download",
        default=None,
        required=False,
    )

    args = parser.parse_args()

    # If no month is provided, use the previous month
    if args.month is None:
        args.month = (datetime.now() - relativedelta(months=1)).strftime("%Y-%m")
        logger.info(f"No month specified, using previous month: {args.month}")

    main(args.month, args.zip_file)
