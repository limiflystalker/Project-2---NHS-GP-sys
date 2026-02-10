# Directive: MCP Server

## Goal

Run the NHS GP IT System data as an MCP server so LLM agents can query GP practice information directly.

## Tools Provided

| Tool | Description |
|------|-------------|
| `gp_lookup_by_ods_code` | Look up a single GP practice by ODS code |
| `gp_search_by_name` | Search practices by name (substring match) |
| `gp_filter_by_system` | List all practices using a given IT system (e.g. TPP, EMIS) |
| `gp_get_statistics` | Get system distribution statistics |
| `gp_update_data` | Download & enrich latest monthly data from NHS Digital |

## Running the Server

### Development / Testing

```bash
# Test in MCP Inspector (interactive browser UI)
mcp dev server.py

# Run directly via stdio
python server.py
```

### Install in Claude Desktop

```bash
mcp install server.py
```

Or manually add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nhs-gp-system": {
      "command": "python",
      "args": ["/full/path/to/Project-2---NHS-GP-sys/server.py"]
    }
  }
}
```

## Prerequisites

- Python 3.10+
- Dependencies installed: `pip install -r requirements.txt`
- For lookup tools: data files must exist in `execution/data/`. Run `gp_update_data` tool if they don't.

## How It Works

- `server.py` imports the existing execution scripts (`gp_lookup.py`, `download_gpad.py`, `enrich_gp_data.py`) directly — no duplication.
- On startup, it sets the working directory to the project root so all relative paths in the execution scripts work correctly.
- The `GPSupplierLookup` instance is lazily loaded on first query and cached. It's invalidated after a data update so subsequent queries use fresh data.

## Edge Cases

- **No data files yet**: Lookup tools return a clear error message directing the user to run `gp_update_data`.
- **CloudFlare blocking**: If `gp_update_data` fails to scrape the NHS website, provide a direct `zip_url` parameter.
- **Long-running enrichment**: First-time enrichment queries the ODS API for all ~6,000 practices (rate-limited at 0.2s each). Subsequent months reuse the cache and only query new practices.

## Related

- [update_gp_suppliers.md](update_gp_suppliers.md) — Data download and processing SOP
- [lookup_gp_supplier.md](lookup_gp_supplier.md) — Query interface SOP
