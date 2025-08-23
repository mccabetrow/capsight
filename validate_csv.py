#!/usr/bin/env python3
"""
CapSight CSV Validator
Validates fundamentals and comps CSV files before import to Supabase.

Usage:
    python validate_csv.py templates/fundamentals_dfw.csv
    python validate_csv.py templates/comps_dfw.csv --market dfw
"""

import csv
import sys
import argparse
from typing import List, Dict, Optional
from datetime import datetime
import re

# Valid market slugs
VALID_MARKETS = {'dfw', 'ie', 'atl', 'phx', 'sav'}

# Valid verification statuses
VALID_VERIFICATION_STATUSES = {'verified', 'broker-confirmed', 'pending'}

# Valid tenant statuses
VALID_TENANT_STATUSES = {'leased', 'vacant', 'owner-occupied'}

def validate_fundamentals(file_path: str) -> List[str]:
    """Validate fundamentals CSV file."""
    errors = []
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check required headers - match our actual schema
            required_headers = {
                'market_slug', 'as_of_date', 'vacancy_rate_pct', 
                'avg_asking_rent_psf_yr_nnn', 'yoy_rent_growth_pct',
                'new_supply_sf_ytd', 'under_construction_sf', 
                'net_absorption_sf_ytd', 'cap_rate_stabilized_median_pct',
                'source_name', 'source_url', 'source_date', 'notes'
            }
            
            if not required_headers.issubset(set(reader.fieldnames or [])):
                missing = required_headers - set(reader.fieldnames or [])
                errors.append(f"Missing required headers: {', '.join(missing)}")
                return errors
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                # Validate market_slug
                if row['market_slug'] not in VALID_MARKETS:
                    errors.append(f"Row {row_num}: Invalid market_slug '{row['market_slug']}'. Must be one of: {', '.join(VALID_MARKETS)}")
                
                # Validate date format (YYYY-MM-DD)
                try:
                    datetime.strptime(row['as_of_date'], '%Y-%m-%d')
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid as_of_date '{row['as_of_date']}'. Must be YYYY-MM-DD format.")
                
                # Validate percentage fields (0-100)
                pct_fields = ['vacancy_rate_pct', 'yoy_rent_growth_pct']
                for field in pct_fields:
                    if row[field]:  # Allow empty values
                        try:
                            value = float(row[field])
                            if field == 'vacancy_rate_pct' and not (0 <= value <= 50):
                                errors.append(f"Row {row_num}: {field} {value} out of range (0-50)")
                            elif field == 'yoy_rent_growth_pct' and not (-50 <= value <= 50):
                                errors.append(f"Row {row_num}: {field} {value} out of range (-50-50)")
                        except ValueError:
                            errors.append(f"Row {row_num}: Invalid {field} '{row[field]}'. Must be numeric.")
                
                # Validate square footage fields (positive integers)
                sf_fields = ['new_supply_sf_ytd', 'under_construction_sf', 'net_absorption_sf_ytd']
                for field in sf_fields:
                    if row[field]:  # Allow empty values
                        try:
                            value = int(row[field])
                            if field == 'net_absorption_sf_ytd':
                                # Can be negative
                                if abs(value) > 1000000000:
                                    errors.append(f"Row {row_num}: {field} {value} out of reasonable range")
                            elif value < 0:
                                errors.append(f"Row {row_num}: {field} {value} must be non-negative")
                        except ValueError:
                            errors.append(f"Row {row_num}: Invalid {field} '{row[field]}'. Must be integer.")
                
                # Validate rent (positive numeric)
                if row['avg_asking_rent_psf_yr_nnn']:
                    try:
                        rent = float(row['avg_asking_rent_psf_yr_nnn'])
                        if not (1 <= rent <= 50):
                            errors.append(f"Row {row_num}: avg_asking_rent_psf_yr_nnn {rent} out of range (1-50)")
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid avg_asking_rent_psf_yr_nnn '{row['avg_asking_rent_psf_yr_nnn']}'. Must be numeric.")
                
                # Validate cap rate
                if row['cap_rate_stabilized_median_pct']:
                    try:
                        cap_rate = float(row['cap_rate_stabilized_median_pct'])
                        if not (2 <= cap_rate <= 15):
                            errors.append(f"Row {row_num}: cap_rate_stabilized_median_pct {cap_rate} out of range (2-15)")
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid cap_rate_stabilized_median_pct '{row['cap_rate_stabilized_median_pct']}'. Must be numeric.")
                
                # Validate URL format
                if row['source_url']:
                    url_pattern = r'^https?://.+\..+'
                    if not re.match(url_pattern, row['source_url']):
                        errors.append(f"Row {row_num}: Invalid source_url '{row['source_url']}'. Must be valid HTTP/HTTPS URL.")
    
    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except Exception as e:
        errors.append(f"Error reading file: {str(e)}")
    
    return errors

def validate_comps(file_path: str, expected_market: Optional[str] = None) -> List[str]:
    """Validate comps CSV file."""
    errors = []
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check required headers
            required_headers = {
                'sale_id', 'market_slug', 'address', 'city', 'state', 'zip',
                'county', 'submarket', 'sale_date', 'price_total_usd',
                'building_sf', 'cap_rate_pct', 'price_per_sf_usd', 'noi_annual',
                'tenant_status', 'buyer', 'seller', 'brokerage',
                'data_source_name', 'data_source_url', 'verification_status', 'notes'
            }
            
            if not required_headers.issubset(set(reader.fieldnames or [])):
                missing = required_headers - set(reader.fieldnames or [])
                errors.append(f"Missing required headers: {', '.join(missing)}")
                return errors
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                # Validate market_slug
                if row['market_slug'] not in VALID_MARKETS:
                    errors.append(f"Row {row_num}: Invalid market_slug '{row['market_slug']}'. Must be one of: {', '.join(VALID_MARKETS)}")
                
                # Check expected market if provided
                if expected_market and row['market_slug'] != expected_market:
                    errors.append(f"Row {row_num}: Expected market '{expected_market}' but found '{row['market_slug']}'")
                
                # Validate sale_date (YYYY-MM-DD)
                try:
                    datetime.strptime(row['sale_date'], '%Y-%m-%d')
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid sale_date '{row['sale_date']}'. Must be YYYY-MM-DD format.")
                
                # Validate numeric fields
                numeric_fields = {
                    'price_total_usd': (1000, 1000000000),  # $1K to $1B
                    'building_sf': (1000, 10000000),        # 1K to 10M sq ft
                    'cap_rate_pct': (3.0, 15.0),           # 3% to 15%
                    'price_per_sf_usd': (50, 1000),        # $50 to $1K per sq ft
                    'noi_annual': (10000, 50000000)        # $10K to $50M annual NOI
                }
                
                for field, (min_val, max_val) in numeric_fields.items():
                    try:
                        value = float(row[field])
                        if not (min_val <= value <= max_val):
                            errors.append(f"Row {row_num}: {field} {value} out of reasonable range ({min_val}-{max_val})")
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid {field} '{row[field]}'. Must be numeric.")
                
                # Validate ZIP code (5 digits)
                if not re.match(r'^\d{5}$', row['zip']):
                    errors.append(f"Row {row_num}: Invalid zip '{row['zip']}'. Must be 5 digits.")
                
                # Validate state (2 letters)
                if not re.match(r'^[A-Z]{2}$', row['state']):
                    errors.append(f"Row {row_num}: Invalid state '{row['state']}'. Must be 2 uppercase letters.")
                
                # Validate tenant_status
                if row['tenant_status'] not in VALID_TENANT_STATUSES:
                    errors.append(f"Row {row_num}: Invalid tenant_status '{row['tenant_status']}'. Must be one of: {', '.join(VALID_TENANT_STATUSES)}")
                
                # Validate verification_status
                if row['verification_status'] not in VALID_VERIFICATION_STATUSES:
                    errors.append(f"Row {row_num}: Invalid verification_status '{row['verification_status']}'. Must be one of: {', '.join(VALID_VERIFICATION_STATUSES)}")
                
                # Validate URL format
                url_pattern = r'^https?://.+\..+'
                if not re.match(url_pattern, row['data_source_url']):
                    errors.append(f"Row {row_num}: Invalid data_source_url '{row['data_source_url']}'. Must be valid HTTP/HTTPS URL.")
                
                # Cross-validate cap rate vs NOI/price
                try:
                    price = float(row['price_total_usd'])
                    noi = float(row['noi_annual'])
                    cap_rate = float(row['cap_rate_pct'])
                    
                    calculated_cap_rate = (noi / price) * 100
                    if abs(calculated_cap_rate - cap_rate) > 0.5:  # Allow 0.5% tolerance
                        errors.append(f"Row {row_num}: Cap rate {cap_rate}% inconsistent with NOI/price ratio ({calculated_cap_rate:.1f}%)")
                except (ValueError, ZeroDivisionError):
                    pass  # Skip validation if values are invalid (already caught above)
                
                # Cross-validate price per sq ft
                try:
                    price = float(row['price_total_usd'])
                    sf = float(row['building_sf'])
                    price_per_sf = float(row['price_per_sf_usd'])
                    
                    calculated_price_per_sf = price / sf
                    if abs(calculated_price_per_sf - price_per_sf) > 5:  # Allow $5 tolerance
                        errors.append(f"Row {row_num}: Price per sq ft ${price_per_sf} inconsistent with total price/sf ratio (${calculated_price_per_sf:.1f})")
                except (ValueError, ZeroDivisionError):
                    pass  # Skip validation if values are invalid (already caught above)
    
    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except Exception as e:
        errors.append(f"Error reading file: {str(e)}")
    
    return errors

def main():
    parser = argparse.ArgumentParser(description='Validate CapSight CSV files')
    parser.add_argument('file_path', help='Path to CSV file to validate')
    parser.add_argument('--market', choices=VALID_MARKETS, help='Expected market slug for comps files')
    
    args = parser.parse_args()
    
    # Determine file type based on filename
    if 'fundamentals' in args.file_path.lower():
        errors = validate_fundamentals(args.file_path)
    elif 'comps' in args.file_path.lower():
        errors = validate_comps(args.file_path, args.market)
    else:
        print("Error: Cannot determine file type. Filename must contain 'fundamentals' or 'comps'.")
        sys.exit(1)
    
    if errors:
        print(f"❌ Validation failed for {args.file_path}")
        print(f"Found {len(errors)} error(s):")
        for error in errors:
            print(f"  • {error}")
        sys.exit(1)
    else:
        print(f"✅ {args.file_path} passed validation")
        sys.exit(0)

if __name__ == '__main__':
    main()
