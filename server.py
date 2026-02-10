"""
NHS GP IT System MCP Server

Exposes GP practice IT supplier data as MCP tools for use by LLM agents.
Wraps the existing execution scripts (gp_lookup, download_gpad, enrich_gp_data)
without modifying them.

Usage:
    python server.py                  # Run via stdio
    mcp dev server.py                 # Run in MCP Inspector
    mcp install server.py             # Install in Claude Desktop
"""

import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Resolve project root and set working directory so existing scripts'
# relative paths (execution/data/, .tmp/) work correctly.
PROJECT_ROOT = Path(__file__).parent.resolve()
os.chdir(PROJECT_ROOT)

# Add execution/ to Python path for imports
sys.path.insert(0, str(PROJECT_ROOT / "execution"))

from gp_lookup import GPSupplierLookup
import download_gpad
import enrich_gp_data

# --- Server setup ---

mcp = FastMCP(
    "nhs-gp-system",
    instructions=(
        "NHS GP IT System server. Provides lookup and search tools for "
        "~6,000 GP practices in England, including their IT system supplier "
        "(TPP, EMIS, etc.) and ICB commissioner. Use the lookup/search tools "
        "for queries. Use the update tool to download fresh monthly data from NHS Digital."
    ),
)

# --- Lazy-loaded lookup instance ---

_lookup_instance: GPSupplierLookup | None = None
_lookup_month: str | None = None

DATA_DIR = str(PROJECT_ROOT / "execution" / "data")


def _find_data_file(month: str | None = None) -> str:
    """Find the appropriate data CSV file."""
    if month:
        path = os.path.join(DATA_DIR, f"icb_gp_suppliers_{month}.csv")
        if os.path.exists(path):
            return path
        raise FileNotFoundError(
            f"No data file for month {month}. "
            f"Available files: {_list_available_months()}"
        )

    files = glob.glob(os.path.join(DATA_DIR, "icb_gp_suppliers_*.csv"))
    if files:
        return max(files)  # Latest by lexicographic sort (YYYY-MM)

    raise FileNotFoundError(
        "No GP supplier data files found. "
        "Run the gp_update_data tool to download and process data first."
    )


def _list_available_months() -> str:
    """List available data months."""
    files = glob.glob(os.path.join(DATA_DIR, "icb_gp_suppliers_*.csv"))
    if not files:
        return "none"
    months = [Path(f).stem.replace("icb_gp_suppliers_", "") for f in sorted(files)]
    return ", ".join(months)


def _get_lookup(month: str | None = None) -> GPSupplierLookup:
    """Get or create a cached GPSupplierLookup instance."""
    global _lookup_instance, _lookup_month
    if _lookup_instance is None or month != _lookup_month:
        data_file = _find_data_file(month)
        _lookup_instance = GPSupplierLookup(data_file=data_file)
        _lookup_month = month
    return _lookup_instance


def _invalidate_cache():
    """Invalidate the cached lookup so next call reloads fresh data."""
    global _lookup_instance, _lookup_month
    _lookup_instance = None
    _lookup_month = None


def _format_practice(row: dict) -> str:
    """Format a single GP practice record as markdown."""
    lines = [
        f"**{row['GP_NAME']}** (`{row['GP_ODS_CODE']}`)",
        f"- IT System: {row['GP_SYSTEM']}",
        f"- Raw Systems: {row.get('GP_GPAD_SYSTEMS', 'N/A')}",
    ]
    if row.get("ICB Sub location"):
        lines.append(f"- ICB Sub Location: {row['ICB Sub location']}")
    return "\n".join(lines)


# --- MCP Tools ---


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def gp_lookup_by_ods_code(ods_code: str, month: str | None = None) -> str:
    """Look up a GP practice by its ODS code (e.g. A81001).

    Returns the practice name, IT system supplier, and ICB commissioner.

    Args:
        ods_code: The ODS code of the GP practice (e.g. "A81001", "Y00050")
        month: Optional data month in YYYY-MM format. Defaults to latest available.
    """
    try:
        lookup = _get_lookup(month)
        result = lookup.lookup_by_ods_code(ods_code)

        if result is None:
            return f"No GP practice found with ODS code `{ods_code.upper()}`."

        return _format_practice(result)
    except FileNotFoundError as e:
        return str(e)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def gp_search_by_name(
    name: str, exact: bool = False, month: str | None = None
) -> str:
    """Search for GP practices by name (case-insensitive substring match).

    Args:
        name: Search term to match against practice names (e.g. "DENSHAM", "PARK MEDICAL")
        exact: If true, only return exact name matches instead of substring matches
        month: Optional data month in YYYY-MM format. Defaults to latest available.
    """
    try:
        lookup = _get_lookup(month)
        results = lookup.search_by_name(name, exact=exact)

        if not results:
            return f"No GP practices found matching '{name}'."

        lines = [f"Found **{len(results)}** practices matching '{name}':\n"]
        for i, row in enumerate(results, 1):
            lines.append(f"{i}. {_format_practice(row)}")
            lines.append("")  # blank line between results

            if i >= 50:
                lines.append(
                    f"*... and {len(results) - 50} more results. "
                    f"Try a more specific search term.*"
                )
                break

        return "\n".join(lines)
    except FileNotFoundError as e:
        return str(e)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def gp_filter_by_system(system: str, month: str | None = None) -> str:
    """Get all GP practices using a specific IT system.

    Common systems: TPP, EMIS, CEGEDIM (Vision), MICROTEST

    Args:
        system: IT system name (e.g. "TPP", "EMIS")
        month: Optional data month in YYYY-MM format. Defaults to latest available.
    """
    try:
        lookup = _get_lookup(month)
        results = lookup.filter_by_system(system)

        if not results:
            return (
                f"No GP practices found using system '{system.upper()}'. "
                f"Common systems: TPP, EMIS, CEGEDIM, MICROTEST."
            )

        # Group by ICB Sub location for a useful summary
        by_icb: dict[str, int] = {}
        for row in results:
            icb = row.get("ICB Sub location", "Unknown")
            by_icb[icb] = by_icb.get(icb, 0) + 1

        lines = [
            f"**{len(results)}** practices use **{system.upper()}**\n",
            "### Breakdown by ICB Sub Location\n",
            "| ICB Sub Location | Count |",
            "|---|---|",
        ]
        for icb, count in sorted(by_icb.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {icb} | {count} |")

        return "\n".join(lines)
    except FileNotFoundError as e:
        return str(e)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def gp_get_statistics(month: str | None = None) -> str:
    """Get statistics about GP IT system distribution across England.

    Returns total practice count and breakdown by IT system with percentages.

    Args:
        month: Optional data month in YYYY-MM format. Defaults to latest available.
    """
    try:
        lookup = _get_lookup(month)
        stats = lookup.get_statistics()

        lines = [
            f"## GP IT System Statistics\n",
            f"**Total practices:** {stats['total_practices']}\n",
            f"**Available months:** {_list_available_months()}\n",
            "| System | Count | Percentage |",
            "|---|---|---|",
        ]
        for system, info in stats["systems"].items():
            lines.append(f"| {system} | {info['count']} | {info['percentage']}% |")

        return "\n".join(lines)
    except FileNotFoundError as e:
        return str(e)


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
def gp_update_data(month: str | None = None, zip_url: str | None = None) -> str:
    """Download and process the latest GP supplier data from NHS Digital.

    This is a long-running operation that:
    1. Downloads monthly NHS appointments data (or uses a provided zip URL)
    2. Extracts GP ODS codes and their IT systems
    3. Enriches with ICB commissioner data via NHS ODS API

    The enrichment step queries the NHS ODS API for each unknown practice
    (rate-limited, may take several minutes on first run).

    Args:
        month: Month to download in YYYY-MM format. Defaults to previous month.
        zip_url: Optional direct URL to the NHS zip file (bypasses website scraping if CloudFlare blocks access)
    """
    from dateutil.relativedelta import relativedelta

    if month is None:
        month = (datetime.now() - relativedelta(months=1)).strftime("%Y-%m")

    lines = [f"## Updating GP data for {month}\n"]

    # Step 1: Download and process
    try:
        lines.append("### Step 1: Download & Process")
        download_gpad.main(month, zip_url)
        lines.append(f"- Downloaded and processed GP supplier data for {month}")
    except Exception as e:
        lines.append(f"- **Error downloading data:** {e}")
        return "\n".join(lines)

    # Step 2: Enrich with ICB data
    try:
        lines.append("\n### Step 2: Enrich with ICB Data")
        # enrich_gp_data.main() uses argparse (reads sys.argv) and may
        # call sys.exit(1) on error, so we temporarily override argv
        # and catch SystemExit.
        original_argv = sys.argv
        sys.argv = ["enrich_gp_data", "--month", month]
        try:
            enrich_gp_data.main()
        except SystemExit as e:
            if e.code != 0:
                raise RuntimeError(f"Enrichment exited with code {e.code}")
        finally:
            sys.argv = original_argv
        lines.append(f"- Enriched data with ICB commissioner codes")
    except Exception as e:
        lines.append(f"- **Error enriching data:** {e}")
        return "\n".join(lines)

    # Invalidate cache so next query picks up fresh data
    _invalidate_cache()

    lines.append(f"\n### Complete")
    lines.append(f"Data for {month} is now available. Use the lookup tools to query it.")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
