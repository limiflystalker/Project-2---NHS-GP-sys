---
name: Lookup GP Supplier
description: Query GP practice IT system supplier information by ODS code, name, or system type
---

# Lookup GP Supplier

## Goal

Look up GP practice information including their IT system supplier (TPP, EMIS, etc.) using various search criteria.

## When to Use

- **Validation**: Verify a GP practice exists and get their IT system
- **Enrichment**: Add IT system information to existing GP data
- **Reporting**: Generate lists of practices by IT system
- **Integration**: Programmatically access GP supplier data from other scripts

## Inputs

Choose one of the following search methods:

- **ODS Code**: Exact GP practice ODS code (e.g. `A81001`)
- **Name**: GP practice name (partial match supported)
- **System**: IT system type (e.g. `TPP`, `EMIS`)
- **Statistics**: Get overview of all IT systems

## Tools

- `execution/gp_lookup.py` - Lookup utility script

## Outputs

Results can be formatted as:
- **Text** (default): Human-readable format
- **JSON**: Machine-readable format for integration

## Process

### Lookup by ODS Code

Find a specific GP practice by their ODS code:

```powershell
python execution/gp_lookup.py --ods-code A81001
```

**Output**:
```
ODS Code: A81001
Name: THE DENSHAM SURGERY
Systems: TPP
Main System: TPP
```

### Search by Name

Find GP practices by name (partial match):

```powershell
python execution/gp_lookup.py --name "DENSHAM"
```

**Output**:
```
Found 1 results:

1. THE DENSHAM SURGERY (A81001) - TPP
```

### Filter by IT System

Get all practices using a specific IT system:

```powershell
python execution/gp_lookup.py --system TPP
```

**Output**:
```
Found 3847 results:

1. THE DENSHAM SURGERY (A81001) - TPP
2. QUEENS PARK MEDICAL CENTRE (A81002) - TPP
3. ACKLAM MEDICAL CENTRE (A81004) - TPP
...
```

### Get Statistics

View distribution of IT systems across all GP practices:

```powershell
python execution/gp_lookup.py --stats
```

**Output**:
```
total_practices: 6154
systems:
  TPP:
    count: 3847
    percentage: 62.51
  EMIS:
    count: 2307
    percentage: 37.49
```

### JSON Output

Get results in JSON format for programmatic use:

```powershell
python execution/gp_lookup.py --ods-code A81001 --output json
```

**Output**:
```json
{
  "GP_ODS_CODE": "A81001",
  "GP_NAME": "THE DENSHAM SURGERY",
  "GP_GPAD_SYSTEMS": "TPP",
  "GP_SYSTEM": "TPP"
}
```

## Programmatic Usage

You can also import and use the lookup class in your own Python scripts:

```python
from execution.gp_lookup import GPSupplierLookup

# Initialize lookup
lookup = GPSupplierLookup()

# Lookup by ODS code
practice = lookup.lookup_by_ods_code("A81001")
print(f"{practice['GP_NAME']} uses {practice['GP_SYSTEM']}")

# Search by name
results = lookup.search_by_name("MEDICAL CENTRE")
print(f"Found {len(results)} practices")

# Filter by system
tpp_practices = lookup.filter_by_system("TPP")
print(f"TPP is used by {len(tpp_practices)} practices")

# Get statistics
stats = lookup.get_statistics()
print(f"Total practices: {stats['total_practices']}")
```

## Edge Cases

### Data File Not Found

**Issue**: GP supplier data hasn't been downloaded yet.

**Error**: `FileNotFoundError: GP supplier data file not found`

**Solution**: Run the update directive first:
```powershell
python execution/download_gpad.py
```

### No Results Found

**Issue**: Search criteria doesn't match any practices.

**Output**: `No results found.`

**Solutions**:
- Check spelling of GP name
- Try partial name search (e.g. "MEDICAL" instead of "MEDICAL CENTRE")
- Verify ODS code is correct (check NHS Digital website)
- Ensure IT system name is uppercase (TPP, EMIS, not tpp, emis)

### Multiple Results for Name Search

**Issue**: Name search returns many results.

**Solution**: 
- Use more specific search terms
- Use exact ODS code if known
- Filter results programmatically in your script

### Case Sensitivity

**Note**: All searches are case-insensitive. "tpp", "TPP", and "Tpp" will all work.

## Use Cases

### Validate GP Practice

Check if a GP practice exists and get their details:
```powershell
python execution/gp_lookup.py --ods-code Y00001 --output json
```

### Generate Report by System

Get all practices using EMIS and save to file:
```powershell
python execution/gp_lookup.py --system EMIS --output json > emis_practices.json
```

### Integration with Systeme.io Workflow

Use in your approval workflow to enrich GP data:
```python
from execution.gp_lookup import GPSupplierLookup

lookup = GPSupplierLookup()

# When processing a user submission with GP ODS code
gp_code = user_data.get('gp_ods_code')
gp_info = lookup.lookup_by_ods_code(gp_code)

if gp_info:
    # Add IT system to user record
    user_data['gp_it_system'] = gp_info['GP_SYSTEM']
    user_data['gp_name'] = gp_info['GP_NAME']
```

## Related Directives

- `update_gp_suppliers.md` - How to update the GP supplier data
