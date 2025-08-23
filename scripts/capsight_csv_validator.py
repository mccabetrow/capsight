import csv
import os
import sys
import re
from datetime import datetime
from typing import List, Tuple

def check_float(val: str, minv: float, maxv: float) -> bool:
    """Check if value is a valid float within range."""
    if not val.strip():
        return True  # Allow empty values
    try:
        f = float(val)
        return minv <= f <= maxv
    except ValueError:
        return False

def check_date(val: str, fmt: str) -> bool:
    """Check if value is a valid date in specified format."""
    if not val.strip():
        return True  # Allow empty dates
    try:
        datetime.strptime(val, fmt)
        return True
    except ValueError:
        return False

def check_integer(val: str) -> bool:
    """Check if value is a valid integer (can be negative)."""
    if not val.strip():
        return True  # Allow empty values
    return re.match(r'^-?\d+$', val.strip()) is not None

def validate_fundamentals(path: str, issues: List[Tuple[str, int, str, str]]) -> None:
    """Validate fundamentals CSV file."""
    try:
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            expected_cols = [
                'market', 'as_of_date', 'vacancy_rate_pct', 'avg_asking_rent_psf_yr_nnn',
                'yoy_rent_growth_pct', 'new_supply_sf_ytd', 'under_construction_sf',
                'net_absorption_sf_ytd', 'cap_rate_stabilized_median_pct',
                'source_name', 'source_url', 'source_date', 'notes'
            ]
            
            # Check headers
            if reader.fieldnames != expected_cols:
                issues.append((path, 1, 'headers', f'Expected {expected_cols}, got {reader.fieldnames}'))
                return
            
            for row_num, row in enumerate(reader, start=2):
                # Required fields
                if not row.get('market', '').strip():
                    issues.append((path, row_num, 'market', 'Missing required field'))
                
                if not row.get('source_url', '').strip():
                    issues.append((path, row_num, 'source_url', 'Missing required field'))
                
                # Date validation - must be YYYY-MM-01 format
                as_of = row.get('as_of_date', '').strip()
                if as_of and not check_date(as_of, '%Y-%m-%d'):
                    issues.append((path, row_num, 'as_of_date', 'Invalid date format, expected YYYY-MM-DD'))
                elif as_of and not as_of.endswith('-01'):
                    issues.append((path, row_num, 'as_of_date', 'Must be first day of month (YYYY-MM-01)'))
                
                if row.get('source_date') and not check_date(row['source_date'], '%Y-%m-%d'):
                    issues.append((path, row_num, 'source_date', 'Invalid date format'))
                
                # Numeric range checks
                if not check_float(row.get('vacancy_rate_pct', ''), 0, 50):
                    issues.append((path, row_num, 'vacancy_rate_pct', 'Must be 0-50'))
                
                if not check_float(row.get('avg_asking_rent_psf_yr_nnn', ''), 1, 50):
                    issues.append((path, row_num, 'avg_asking_rent_psf_yr_nnn', 'Must be 1-50'))
                
                if not check_float(row.get('yoy_rent_growth_pct', ''), -50, 50):
                    issues.append((path, row_num, 'yoy_rent_growth_pct', 'Must be -50 to 50'))
                
                if not check_float(row.get('cap_rate_stabilized_median_pct', ''), 2, 15):
                    issues.append((path, row_num, 'cap_rate_stabilized_median_pct', 'Must be 2-15'))
                
                # Integer checks
                for col in ['new_supply_sf_ytd', 'under_construction_sf', 'net_absorption_sf_ytd']:
                    if row.get(col) and not check_integer(row[col]):
                        issues.append((path, row_num, col, 'Must be integer'))
                
                # Market slug validation
                valid_slugs = ['dfw', 'ie', 'atl', 'phx', 'sav']
                if row.get('market') and row['market'] not in valid_slugs:
                    issues.append((path, row_num, 'market', f'Must be one of: {valid_slugs}'))
    
    except Exception as e:
        issues.append((path, 0, 'file', f'Error reading file: {str(e)}'))

def validate_comps(path: str, issues: List[Tuple[str, int, str, str]]) -> None:
    """Validate sales comps CSV file."""
    try:
        seen_ids = set()
        seen_combos = set()
        
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            expected_cols = [
                'sale_id', 'market', 'address', 'city', 'state', 'zip', 'county',
                'submarket', 'sale_date', 'price_total_usd', 'building_sf',
                'land_acres', 'cap_rate_pct', 'price_per_sf_usd', 'year_built',
                'clear_height_ft', 'tenant_status', 'buyer', 'seller', 'brokerage',
                'data_source_name', 'data_source_url', 'verification_status', 'notes'
            ]
            
            # Check headers
            if reader.fieldnames != expected_cols:
                issues.append((path, 1, 'headers', f'Expected {expected_cols}, got {reader.fieldnames}'))
                return
            
            for row_num, row in enumerate(reader, start=2):
                # Required fields
                required = ['sale_id', 'market', 'address', 'data_source_url']
                for field in required:
                    if not row.get(field, '').strip():
                        issues.append((path, row_num, field, 'Missing required field'))
                
                # Unique sale_id
                sale_id = row.get('sale_id', '').strip()
                if sale_id:
                    if sale_id in seen_ids:
                        issues.append((path, row_num, 'sale_id', 'Duplicate sale_id'))
                    seen_ids.add(sale_id)
                
                # Unique address/date combo
                addr = row.get('address', '').strip()
                date = row.get('sale_date', '').strip()
                combo = (addr, date)
                if addr and date:
                    if combo in seen_combos:
                        issues.append((path, row_num, 'address/sale_date', 'Duplicate address/date combination'))
                    seen_combos.add(combo)
                
                # Date validation
                if date and not check_date(date, '%Y-%m-%d'):
                    issues.append((path, row_num, 'sale_date', 'Invalid date format'))
                
                # Numeric validations
                price = row.get('price_total_usd', '').strip()
                if price and (not price.isdigit() or int(price) <= 0):
                    issues.append((path, row_num, 'price_total_usd', 'Must be positive integer'))
                
                sf = row.get('building_sf', '').strip()
                if sf and (not sf.isdigit() or int(sf) <= 0):
                    issues.append((path, row_num, 'building_sf', 'Must be positive integer'))
                
                if not check_float(row.get('cap_rate_pct', ''), 2, 15):
                    issues.append((path, row_num, 'cap_rate_pct', 'Must be 2-15 if present'))
                
                # Price per SF validation
                if price and sf and row.get('price_per_sf_usd'):
                    try:
                        calc_ppsf = float(price) / float(sf)
                        actual_ppsf = float(row['price_per_sf_usd'])
                        if abs(calc_ppsf - actual_ppsf) > 0.5:
                            issues.append((path, row_num, 'price_per_sf_usd', 
                                         f'Mismatch: calculated {calc_ppsf:.2f}, stated {actual_ppsf:.2f}'))
                    except (ValueError, ZeroDivisionError):
                        pass
                
                # Enum validations
                tenant_status = row.get('tenant_status', '').strip()
                if tenant_status and tenant_status not in ['leased', 'vacant', 'partial']:
                    issues.append((path, row_num, 'tenant_status', 'Must be: leased, vacant, or partial'))
                
                verification = row.get('verification_status', '').strip()
                if verification and verification not in ['unverified', 'verified', 'broker-confirmed']:
                    issues.append((path, row_num, 'verification_status', 
                                 'Must be: unverified, verified, or broker-confirmed'))
                
                # Market slug validation
                valid_slugs = ['dfw', 'ie', 'atl', 'phx', 'sav']
                market = row.get('market', '').strip()
                if market and market not in valid_slugs:
                    issues.append((path, row_num, 'market', f'Must be one of: {valid_slugs}'))
    
    except Exception as e:
        issues.append((path, 0, 'file', f'Error reading file: {str(e)}'))

def main(folder_path: str) -> None:
    """Main validation function."""
    if not os.path.exists(folder_path):
        print(f"Error: Folder {folder_path} does not exist")
        sys.exit(1)
    
    issues = []
    files_processed = 0
    
    # Process all CSV files in folder
    for filename in os.listdir(folder_path):
        if not filename.endswith('.csv'):
            continue
            
        filepath = os.path.join(folder_path, filename)
        files_processed += 1
        
        if filename.startswith('fundamentals_') or filename == 'fundamentals_template.csv':
            validate_fundamentals(filepath, issues)
        elif filename.startswith('comps_') or filename == 'comps_template.csv':
            validate_comps(filepath, issues)
        else:
            print(f"Warning: Skipping unknown CSV format: {filename}")
    
    # Write results
    report_file = 'validation_report.csv'
    with open(report_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['file', 'row', 'field', 'problem'])
        for issue in issues:
            writer.writerow(issue)
    
    # Summary
    summary = f"""CapSight CSV Validation Summary
=====================================
Files processed: {files_processed}
Issues found: {len(issues)}
Report saved to: {report_file}

"""
    
    if issues:
        summary += "Most common issues:\n"
        issue_counts = {}
        for _, _, field, problem in issues:
            key = f"{field}: {problem}"
            issue_counts[key] = issue_counts.get(key, 0) + 1
        
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            summary += f"  {count}x {issue}\n"
        
        summary += f"\n❌ Validation failed with {len(issues)} issues. Check {report_file} for details."
    else:
        summary += "✅ All files passed validation!"
    
    with open('validation_summary.txt', 'w', encoding='utf-8') as f:
        f.write(summary)
    
    print(summary)
    
    # Exit code for CI
    sys.exit(1 if issues else 0)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python capsight_csv_validator.py /path/to/csv/folder')
        print('Example: python capsight_csv_validator.py ./data/templates')
        sys.exit(1)
    
    main(sys.argv[1])
