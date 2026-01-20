"""
GP Supplier Lookup Utility

Provides command-line and programmatic access to GP supplier data.
Allows querying by ODS code, GP name, or IT system.

Usage:
    python execution/gp_lookup.py --ods-code A81001
    python execution/gp_lookup.py --name "DENSHAM SURGERY"
    python execution/gp_lookup.py --system TPP
    python execution/gp_lookup.py --system EMIS --output json
"""

import argparse
import csv
import glob
import json
import os
import sys


# Default data file pattern
DATA_DIR = "execution/data"
DATA_FILE_PATTERN = "icb_gp_suppliers_*.csv"


class GPSupplierLookup:
    """Class for looking up GP supplier information"""
    
    def __init__(self, data_file=None):
        """
        Initialize the lookup with data from CSV file
        
        Args:
            data_file: Path to the GP suppliers CSV file
        """
        self.data_file = data_file
        self.data = []
        self.load_data()
    
    def load_data(self):
        """Load GP supplier data from CSV file"""
        if not self.data_file or not os.path.exists(self.data_file):
            raise FileNotFoundError(
                f"GP supplier data file not found: {self.data_file}\n"
                f"Run the update scripts to download and enrich the data first."
            )
        
        with open(self.data_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.data = list(reader)
    
    def lookup_by_ods_code(self, ods_code: str):
        """
        Look up GP practice by ODS code
        
        Args:
            ods_code: GP ODS code (e.g. "A81001")
            
        Returns:
            Dict with GP information or None if not found
        """
        for row in self.data:
            if row["GP_ODS_CODE"] == ods_code.upper():
                return row
        return None
    
    def search_by_name(self, name: str, exact=False):
        """
        Search for GP practices by name
        
        Args:
            name: GP practice name or partial name
            exact: If True, only return exact matches
            
        Returns:
            List of matching GP practices
        """
        results = []
        search_term = name.upper()
        
        for row in self.data:
            gp_name = row["GP_NAME"].upper()
            if exact:
                if gp_name == search_term:
                    results.append(row)
            else:
                if search_term in gp_name:
                    results.append(row)
        
        return results
    
    def filter_by_system(self, system: str):
        """
        Get all GP practices using a specific IT system
        
        Args:
            system: IT system name (e.g. "TPP", "EMIS")
            
        Returns:
            List of GP practices using the specified system
        """
        results = []
        search_term = system.upper()
        
        for row in self.data:
            if row["GP_SYSTEM"] == search_term:
                results.append(row)
        
        return results
    
    def get_statistics(self):
        """
        Get statistics about GP IT systems
        
        Returns:
            Dict with system counts and percentages
        """
        system_counts = {}
        total = len(self.data)
        
        for row in self.data:
            system = row["GP_SYSTEM"]
            system_counts[system] = system_counts.get(system, 0) + 1
        
        # Calculate percentages
        stats = {
            "total_practices": total,
            "systems": {}
        }
        
        for system, count in sorted(system_counts.items(), key=lambda x: x[1], reverse=True):
            stats["systems"][system] = {
                "count": count,
                "percentage": round((count / total) * 100, 2)
            }
        
        return stats


def format_output(data, output_format="text"):
    """
    Format output data for display
    
    Args:
        data: Data to format (dict, list, or None)
        output_format: "text" or "json"
        
    Returns:
        Formatted string
    """
    if output_format == "json":
        return json.dumps(data, indent=2)
    
    # Text format
    if data is None:
        return "No results found."
    
    if isinstance(data, dict):
        # Single result
        if "GP_ODS_CODE" in data:
            return (
                f"ODS Code: {data['GP_ODS_CODE']}\n"
                f"Name: {data['GP_NAME']}\n"
                f"Systems: {data['GP_GPAD_SYSTEMS']}\n"
                f"Main System: {data['GP_SYSTEM']}"
            )
        else:
            # Statistics or other dict
            output = []
            for key, value in data.items():
                if isinstance(value, dict):
                    output.append(f"{key}:")
                    for k, v in value.items():
                        output.append(f"  {k}: {v}")
                else:
                    output.append(f"{key}: {value}")
            return "\n".join(output)
    
    if isinstance(data, list):
        # Multiple results
        if len(data) == 0:
            return "No results found."
        
        output = [f"Found {len(data)} results:\n"]
        for i, row in enumerate(data, 1):
            output.append(f"{i}. {row['GP_NAME']} ({row['GP_ODS_CODE']}) - {row['GP_SYSTEM']}")
        
        return "\n".join(output)
    
    return str(data)


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Look up GP supplier information"
    )
    
    parser.add_argument(
        "--ods-code",
        type=str,
        help="Look up by ODS code (e.g. A81001)"
    )
    
    parser.add_argument(
        "--name",
        type=str,
        help="Search by GP practice name (partial match)"
    )
    
    parser.add_argument(
        "--system",
        type=str,
        help="Filter by IT system (e.g. TPP, EMIS)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show statistics about GP IT systems"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--month",
        type=str,
        help="The month of the data to query (e.g. 2025-01). Defaults to latest."
    )
    
    args = parser.parse_args()

    # Determine which data file to use
    if args.month:
        data_file = os.path.join(DATA_DIR, f"icb_gp_suppliers_{args.month}.csv")
    else:
        # Find the latest file
        files = glob.glob(os.path.join(DATA_DIR, "icb_gp_suppliers_*.csv"))
        if not files:
            # Fallback to the non-suffixed one if it exists (legacy)
            legacy_file = os.path.join(DATA_DIR, "icb_gp_suppliers.csv")
            if os.path.exists(legacy_file):
                data_file = legacy_file
            else:
                print(f"Error: No GP supplier data files found in {DATA_DIR}", file=sys.stderr)
                sys.exit(1)
        else:
            data_file = max(files)  # Lexicographical sort works for YYYY-MM
    
    # Check if at least one search parameter is provided
    if not any([args.ods_code, args.name, args.system, args.stats]):
        parser.print_help()
        sys.exit(1)
    
    try:
        lookup = GPSupplierLookup(data_file=data_file)
        
        if args.stats:
            result = lookup.get_statistics()
        elif args.ods_code:
            result = lookup.lookup_by_ods_code(args.ods_code)
        elif args.name:
            result = lookup.search_by_name(args.name)
        elif args.system:
            result = lookup.filter_by_system(args.system)
        else:
            result = None
        
        print(format_output(result, args.output))
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
