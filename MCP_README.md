# NHS GP IT System — MCP Server

An MCP (Model Context Protocol) server that gives LLM agents direct access to NHS GP practice data — IT system suppliers, commissioner mappings, and practice search across 6,000+ GP practices in England.

Built on the [FastMCP](https://github.com/modelcontextprotocol/python-sdk) Python SDK, wrapping the existing extraction and lookup scripts.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run in the MCP Inspector (for testing)

```bash
mcp dev server.py
```

This opens an interactive browser UI where you can call each tool and inspect responses.

### 3. Install in Claude Desktop

```bash
mcp install server.py
```

Or manually add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nhs-gp-system": {
      "command": "python3",
      "args": ["/absolute/path/to/Project-2---NHS-GP-sys/server.py"]
    }
  }
}
```

### 4. Load data

On first use, there are no data files yet. Ask the agent to call `gp_update_data`, or run the pipeline manually:

```bash
python execution/download_gpad.py --month 2025-01
python execution/enrich_gp_data.py --month 2025-01
```

---

## Tools

### `gp_lookup_by_ods_code`

Look up a single GP practice by its ODS code.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ods_code` | string | Yes | ODS code (e.g. `A81001`) |
| `month` | string | No | Data month `YYYY-MM`. Defaults to latest. |

**Example response:**
```
**THE DENSHAM SURGERY** (`A81001`)
- IT System: TPP
- Raw Systems: TPP
- ICB Sub Location: 16C
```

---

### `gp_search_by_name`

Search for GP practices by name (case-insensitive substring match).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Search term (e.g. `PARK MEDICAL`) |
| `exact` | boolean | No | Exact match only. Default `false`. |
| `month` | string | No | Data month `YYYY-MM`. Defaults to latest. |

Returns up to 50 results. Suggests narrowing the search if more exist.

---

### `gp_filter_by_system`

List all practices using a specific IT system, grouped by ICB Sub Location.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `system` | string | Yes | IT system name (`TPP`, `EMIS`, `CEGEDIM`, `MICROTEST`) |
| `month` | string | No | Data month `YYYY-MM`. Defaults to latest. |

**Example response:**
```
**3,500** practices use **TPP**

### Breakdown by ICB Sub Location

| ICB Sub Location | Count |
|---|---|
| 16C | 85 |
| 15E | 72 |
| ... | ... |
```

---

### `gp_get_statistics`

Get IT system distribution statistics across all practices.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `month` | string | No | Data month `YYYY-MM`. Defaults to latest. |

**Example response:**
```
## GP IT System Statistics

**Total practices:** 6,200

| System | Count | Percentage |
|---|---|---|
| TPP | 3,500 | 56.45% |
| EMIS | 2,400 | 38.71% |
| CEGEDIM | 250 | 4.03% |
```

---

### `gp_update_data`

Download and process the latest GP supplier data from NHS Digital. This is a long-running operation.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `month` | string | No | Month to download `YYYY-MM`. Defaults to previous month. |
| `zip_url` | string | No | Direct URL to NHS zip file (bypasses CloudFlare). |

**What it does:**
1. Downloads the monthly NHS Appointments in General Practice zip
2. Extracts GP ODS codes and their IT system from the CSV data
3. Enriches each practice with ICB commissioner data via the NHS ODS API

The enrichment step is rate-limited (0.2s per API call). First-time runs query all ~6,000 practices; subsequent months reuse the cache and only query new ones.

---

## Architecture

```
server.py                    FastMCP entry point — defines tools, manages state
  ├── execution/gp_lookup.py     GPSupplierLookup class (imported directly)
  ├── execution/download_gpad.py Data download & processing (imported directly)
  ├── execution/enrich_gp_data.py ICB enrichment pipeline (imported directly)
  └── execution/data/            CSV data files
       ├── icb_gp_suppliers_YYYY-MM.csv   Enriched data (queried by tools)
       ├── gp_suppliers_YYYY-MM.csv       Raw extracted data
       └── GP to ICB Sub location - Map.csv  ODS→ICB cache
```

The server imports the existing Python modules directly — no code duplication. It sets the working directory to the project root on startup so all relative paths in the execution scripts resolve correctly.

The `GPSupplierLookup` instance is lazily loaded on first query and cached in memory. It's invalidated after a `gp_update_data` call so subsequent queries use fresh data.

---

## Data Sources

| Source | URL | Auth |
|--------|-----|------|
| NHS Appointments in General Practice | [digital.nhs.uk](https://digital.nhs.uk/data-and-information/publications/statistical/appointments-in-general-practice) | None (public) |
| NHS ODS API | [directory.spineservices.nhs.uk](https://directory.spineservices.nhs.uk/ORD/2-0-0/) | None (public) |

Data is published monthly by NHS Digital and subject to [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

---

## Troubleshooting

**"No GP supplier data files found"** — Run `gp_update_data` or the manual pipeline to download data first.

**CloudFlare blocks the download** — Pass a `zip_url` parameter to `gp_update_data`. To get the URL: open the [NHS Appointments page](https://digital.nhs.uk/data-and-information/publications/statistical/appointments-in-general-practice), find "Annex 1 - Practice Level Crosstab (CSV)", right-click, copy link.

**Enrichment takes a long time** — Expected on first run (~20 min for 6,000 API calls at 0.2s each). The ODS→ICB cache (`GP to ICB Sub location - Map.csv`) speeds up future runs.

---

## Requirements

- Python 3.10+
- Dependencies: `pip install -r requirements.txt`
- Internet access (for data download and ODS API enrichment)
