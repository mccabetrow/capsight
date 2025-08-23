# Tools Directory

This directory contains command-line tools for CapSight data management and operations.

## Files

- **`seed_markets.py`** - CLI tool for validating and seeding market data to Supabase
- **`requirements.txt`** - Python dependencies for tools
- **`README.md`** - This file

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_KEY=your-service-role-key

# Dry-run validation (safe)
python seed_markets.py --all --dry-run

# Seed all markets
python seed_markets.py --all --verbose
```

## Market Data Seeding CLI (`seed_markets.py`)

### Purpose
Provides robust, auditable market data seeding with comprehensive validation and error handling.

### Features
- **CSV Validation**: Strict validation of fundamentals and comparables data
- **Batch Operations**: Process all markets (`--all`) or specific ones (`--market dfw`)
- **Dry-run Mode**: Test validation without making database changes (`--dry-run`)
- **Summary Reporting**: Tabular summary with record counts and validation results
- **Fail-safe**: Aborts on partial failures to maintain data integrity
- **Environment Detection**: Works with both anon keys and service role keys

### Usage Examples

```bash
# Test validation for all markets (no database changes)
python seed_markets.py --all --dry-run

# Seed specific market with verbose output
python seed_markets.py --market dfw --verbose

# Seed all markets (production deployment)
python seed_markets.py --all --verbose

# Using environment variables for different environments
SUPABASE_URL=https://staging.supabase.co python seed_markets.py --all --dry-run
```

### CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--market {dfw,ie,atl,phx,sav}` | Seed specific market | `--market dfw` |
| `--all` | Process all 5 markets | `--all` |
| `--dry-run` | Validate only, no upload | `--dry-run` |
| `--verbose` | Detailed logging and summary | `--verbose` |
| `--help` | Show help message | `--help` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | For upload | Service role key (required for actual upload) |
| `SUPABASE_ANON_KEY` | Alternative | Anonymous key (read-only validation) |

### Expected CSV Files

The tool looks for these files in the `../templates/` directory:

**Fundamentals Files:**
- `fundamentals_dfw.csv`
- `fundamentals_ie.csv`
- `fundamentals_atl.csv`
- `fundamentals_phx.csv`
- `fundamentals_sav.csv`

**Comparables Files:**
- `comps_dfw.csv`
- `comps_ie.csv`
- `comps_atl.csv`
- `comps_phx.csv`
- `comps_sav.csv`

### Output Example

```
🏢 CapSight Market Data Seeder
=====================================

📊 MARKET SEEDING SUMMARY
=====================================
┌────────┬─────┬──────┬──────┬────────────────────────┬────────────────┐
│ Market │ Fund│ Comp │ Total│ Validation             │ Upload         │
├────────┼─────┼──────┼──────┼────────────────────────┼────────────────┤
│ DFW    │   12│   45 │   57 │ ✅ PASSED              │ ✅ SUCCESS     │
│ IE     │   15│   38 │   53 │ ✅ PASSED              │ ✅ SUCCESS     │
│ ATL    │   18│   42 │   60 │ ✅ PASSED              │ ✅ SUCCESS     │
│ PHX    │   14│   33 │   47 │ ✅ PASSED              │ ✅ SUCCESS     │
│ SAV    │   10│   25 │   35 │ ✅ PASSED              │ ✅ SUCCESS     │
├────────┼─────┼──────┼──────┼────────────────────────┼────────────────┤
│ TOTAL  │   69│  183 │  252 │ 5/5 PASSED             │ 5/5 SUCCESS    │
└────────┴─────┴──────┴──────┴────────────────────────┴────────────────┘

✅ All markets processed successfully!
```

### Error Handling

The tool implements comprehensive error handling:

- **Validation Errors**: Shows specific CSV validation failures
- **Partial Failures**: Aborts entire operation if any market fails
- **Network Errors**: Clear error messages for Supabase connectivity issues
- **File Errors**: Reports missing or unreadable CSV files

### Integration

This tool is integrated into:
- **`../deploy-enhanced.sh`** - Automated deployment script
- **CI/CD pipelines** - For staging environment data seeding
- **Production deployment** - Robust data migration workflows

### Support

For issues or questions:
1. Check the output summary table for validation details
2. Run with `--dry-run` first to test validation
3. Verify CSV file formats match templates
4. Confirm environment variables are set correctly
