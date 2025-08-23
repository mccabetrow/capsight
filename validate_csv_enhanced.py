#!/usr/bin/env python3
"""
CapSight CSV Validator - Enhanced
Validates fundamentals and comps CSV files with advanced data quality gates.

Usage:
    python validate_csv.py templates/fundamentals_dfw.csv
    python validate_csv.py templates/comps_dfw.csv --market dfw
"""

import csv
import sys
import argparse
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
import math

# Valid market slugs with geofence boundaries (lat/lng bounding boxes)
MARKET_GEOFENCES = {
    'dfw': {'name': 'Dallas-Fort Worth', 'min_lat': 32.0, 'max_lat': 33.5, 'min_lng': -97.5, 'max_lng': -96.0},
    'ie': {'name': 'Inland Empire', 'min_lat': 33.5, 'max_lat': 34.5, 'min_lng': -118.0, 'max_lng': -116.5},
    'atl': {'name': 'Atlanta', 'min_lat': 33.0, 'max_lat': 34.0, 'min_lng': -85.0, 'max_lng': -84.0},
    'phx': {'name': 'Phoenix', 'min_lat': 33.0, 'max_lat': 34.0, 'min_lng': -113.0, 'max_lng': -111.5},
    'sav': {'name': 'Savannah', 'min_lat': 31.8, 'max_lat': 32.5, 'min_lng': -81.5, 'max_lng': -80.5}
}

# Valid verification statuses
VALID_VERIFICATION_STATUSES = {'verified', 'broker-confirmed', 'pending'}

# Valid tenant statuses
VALID_TENANT_STATUSES = {'leased', 'vacant', 'owner-occupied'}

# Size/age buckets for quality control
SIZE_BUCKETS = [
    (0, 25000, 'small'),
    (25000, 100000, 'medium'),
    (100000, 500000, 'large'),
    (500000, float('inf'), 'xl')
]

AGE_BUCKETS = [
    (0, 5, 'new'),
    (5, 20, 'modern'),
    (20, 40, 'mature'),
    (40, float('inf'), 'vintage')
]

def validate_geofence(lat: float, lng: float, market_slug: str) -> bool:
    """Check if coordinates are within market geofence."""
    if market_slug not in MARKET_GEOFENCES:
        return False
    
    bounds = MARKET_GEOFENCES[market_slug]
    return (bounds['min_lat'] <= lat <= bounds['max_lat'] and 
            bounds['min_lng'] <= lng <= bounds['max_lng'])

def validate_noi_flag(noi_annual: float, cap_rate: float, building_sf: int) -> Tuple[bool, str]:
    """Validate NOI consistency with cap rate and implied rent."""
    try:
        # Calculate implied price/sf from NOI and cap rate
        implied_value = noi_annual / (cap_rate / 100)
        implied_psf = implied_value / building_sf
        
        # Flag if implied rent is unrealistic for industrial
        implied_rent_psf_yr = noi_annual / building_sf
        
        # Industrial rent typically $3-15/sf/yr for our markets
        if implied_rent_psf_yr < 2 or implied_rent_psf_yr > 20:
            return False, f"Implied rent ${implied_rent_psf_yr:.2f}/sf/yr outside expected range $2-20"
        
        # Flag if cap rate/NOI relationship seems off
        if cap_rate < 3 or cap_rate > 15:
            return False, f"Cap rate {cap_rate}% outside expected range 3-15%"
            
        return True, ""
    except:
        return False, "Error calculating NOI consistency"

def get_size_bucket(building_sf: int) -> str:
    """Get size bucket for building."""
    for min_sf, max_sf, bucket in SIZE_BUCKETS:
        if min_sf <= building_sf < max_sf:
            return bucket
    return 'unknown'

def get_age_bucket(year_built: int, current_year: int = None) -> str:
    """Get age bucket for building."""
    if current_year is None:
        current_year = datetime.now().year
    
    age = current_year - year_built
    for min_age, max_age, bucket in AGE_BUCKETS:
        if min_age <= age < max_age:
            return bucket
    return 'unknown'

def needs_manual_review(row: Dict[str, str]) -> Tuple[bool, str]:
    """Determine if comp needs manual review based on quality flags."""
    reasons = []
    
    try:
        # Price outlier check (rough)
        price_psf = float(row.get('price_per_sf_usd', 0))
        if price_psf < 20 or price_psf > 300:
            reasons.append(f"Price/SF ${price_psf} unusual")
        
        # Cap rate outlier check
        cap_rate = float(row.get('cap_rate_pct', 0))
        if cap_rate < 3 or cap_rate > 12:
            reasons.append(f"Cap rate {cap_rate}% unusual")
        
        # Very old or very new
        year_built = int(row.get('year_built', 0))
        current_year = datetime.now().year
        if year_built < 1950 or year_built > current_year - 1:
            reasons.append(f"Year built {year_built} unusual")
        
        # Missing critical fields
        critical_fields = ['noi_annual', 'building_sf', 'cap_rate_pct']
        for field in critical_fields:
            if not row.get(field) or row[field].strip() == '':
                reasons.append(f"Missing {field}")
    except:
        reasons.append("Data parsing error")
    
    return len(reasons) > 0, "; ".join(reasons)

def validate_fundamentals(file_path: str) -> List[str]:
    """Validate fundamentals CSV file."""
    errors = []
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check required headers
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
            
            for row_num, row in enumerate(reader, start=2):
                # Validate market_slug
                market_slug = row.get('market_slug', '').lower()
                if market_slug not in MARKET_GEOFENCES:
                    errors.append(f"Row {row_num}: Invalid market_slug '{market_slug}'. Must be one of: {', '.join(MARKET_GEOFENCES.keys())}")
                
                # Validate as_of_date
                try:
                    as_of_date = datetime.strptime(row['as_of_date'], '%Y-%m-%d')
                    # Check if date is reasonable (not too old, not future)
                    days_old = (datetime.now() - as_of_date).days
                    if days_old > 365:
                        errors.append(f"Row {row_num}: as_of_date is over 1 year old")
                    elif days_old < 0:
                        errors.append(f"Row {row_num}: as_of_date is in the future")
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid as_of_date format. Use YYYY-MM-DD")
                
                # Validate numeric ranges
                numeric_validations = [
                    ('vacancy_rate_pct', 0, 50, 'Vacancy rate'),
                    ('avg_asking_rent_psf_yr_nnn', 1, 50, 'Average asking rent'),
                    ('yoy_rent_growth_pct', -50, 100, 'YoY rent growth'),
                    ('cap_rate_stabilized_median_pct', 2, 15, 'Stabilized cap rate')
                ]
                
                for field, min_val, max_val, desc in numeric_validations:
                    try:
                        val = float(row.get(field, 0))
                        if not (min_val <= val <= max_val):
                            errors.append(f"Row {row_num}: {desc} {val} outside expected range {min_val}-{max_val}")
                    except ValueError:
                        errors.append(f"Row {row_num}: {desc} must be numeric")
                
    except Exception as e:
        errors.append(f"Error reading file: {str(e)}")
    
    return errors

def validate_comps(file_path: str, market_slug: Optional[str] = None) -> List[str]:
    """Validate comps CSV file with enhanced quality gates."""
    errors = []
    warnings = []
    review_queue = []
    
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check required headers
            required_headers = {
                'market_slug', 'address', 'city', 'state', 'zip_code',
                'lat', 'lng', 'sale_date', 'price_total_usd', 'building_sf',
                'price_per_sf_usd', 'cap_rate_pct', 'noi_annual', 'year_built',
                'property_type', 'submarket', 'tenant_status', 'verification_status',
                'source_name', 'source_url', 'notes'
            }
            
            if not required_headers.issubset(set(reader.fieldnames or [])):
                missing = required_headers - set(reader.fieldnames or [])
                errors.append(f"Missing required headers: {', '.join(missing)}")
                return errors
            
            for row_num, row in enumerate(reader, start=2):
                row_errors = []
                
                # Basic field validation
                comp_market_slug = row.get('market_slug', '').lower()
                
                # Market validation
                if comp_market_slug not in MARKET_GEOFENCES:
                    row_errors.append(f"Invalid market_slug '{comp_market_slug}'")
                elif market_slug and comp_market_slug != market_slug.lower():
                    row_errors.append(f"Market mismatch: expected {market_slug}, got {comp_market_slug}")
                
                # Geofence validation
                try:
                    lat = float(row.get('lat', 0))
                    lng = float(row.get('lng', 0))
                    
                    if not validate_geofence(lat, lng, comp_market_slug):
                        row_errors.append(f"Coordinates ({lat}, {lng}) outside {MARKET_GEOFENCES[comp_market_slug]['name']} geofence")
                except ValueError:
                    row_errors.append("Invalid lat/lng coordinates")
                
                # Date validation
                try:
                    sale_date = datetime.strptime(row['sale_date'], '%Y-%m-%d')
                    days_old = (datetime.now() - sale_date).days
                    if days_old > 1825:  # 5 years
                        warnings.append(f"Row {row_num}: Sale date over 5 years old")
                    elif days_old < 0:
                        row_errors.append("Sale date is in the future")
                except ValueError:
                    row_errors.append("Invalid sale_date format. Use YYYY-MM-DD")
                
                # Numeric validations with wider ranges for data quality
                try:
                    price_total = float(row.get('price_total_usd', 0))
                    building_sf = int(row.get('building_sf', 0))
                    price_psf = float(row.get('price_per_sf_usd', 0))
                    cap_rate = float(row.get('cap_rate_pct', 0))
                    noi_annual = float(row.get('noi_annual', 0))
                    year_built = int(row.get('year_built', 0))
                    
                    # Price validations
                    if not (100000 <= price_total <= 100000000):  # $100K - $100M
                        row_errors.append(f"Price ${price_total:,} outside reasonable range")
                    
                    if not (5000 <= building_sf <= 2000000):  # 5K - 2M SF
                        row_errors.append(f"Building size {building_sf:,} SF outside reasonable range")
                    
                    if not (10 <= price_psf <= 500):  # $10-500/SF
                        row_errors.append(f"Price/SF ${price_psf} outside reasonable range")
                    
                    if not (2 <= cap_rate <= 20):  # 2-20%
                        row_errors.append(f"Cap rate {cap_rate}% outside reasonable range")
                    
                    if not (10000 <= noi_annual <= 10000000):  # $10K - $10M
                        row_errors.append(f"NOI ${noi_annual:,} outside reasonable range")
                    
                    if not (1900 <= year_built <= datetime.now().year):
                        row_errors.append(f"Year built {year_built} outside reasonable range")
                    
                    # NOI consistency check
                    noi_valid, noi_msg = validate_noi_flag(noi_annual, cap_rate, building_sf)
                    if not noi_valid:
                        warnings.append(f"Row {row_num}: {noi_msg}")
                    
                    # Size and age buckets for reporting
                    size_bucket = get_size_bucket(building_sf)
                    age_bucket = get_age_bucket(year_built)
                    
                    # Check if needs manual review
                    needs_review, review_reason = needs_manual_review(row)
                    if needs_review:
                        review_queue.append(f"Row {row_num}: {review_reason}")
                    
                except ValueError as e:
                    row_errors.append(f"Numeric field error: {str(e)}")
                
                # Categorical validations
                if row.get('verification_status') not in VALID_VERIFICATION_STATUSES:
                    row_errors.append(f"Invalid verification_status. Must be one of: {', '.join(VALID_VERIFICATION_STATUSES)}")
                
                if row.get('tenant_status') not in VALID_TENANT_STATUSES:
                    row_errors.append(f"Invalid tenant_status. Must be one of: {', '.join(VALID_TENANT_STATUSES)}")
                
                # Property type validation (should be industrial variants)
                property_type = row.get('property_type', '').lower()
                valid_types = {'warehouse', 'manufacturing', 'distribution', 'flex', 'industrial'}
                if not any(valid_type in property_type for valid_type in valid_types):
                    warnings.append(f"Row {row_num}: Property type '{property_type}' may not be industrial")
                
                # Add row errors to main error list
                for error in row_errors:
                    errors.append(f"Row {row_num}: {error}")
    
    except Exception as e:
        errors.append(f"Error reading file: {str(e)}")
    
    # Print summary
    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  {warning}")
    
    if review_queue:
        print(f"\nMANUAL REVIEW RECOMMENDED ({len(review_queue)} items):")
        for review in review_queue:
            print(f"  {review}")
    
    return errors

def main():
    parser = argparse.ArgumentParser(description='Validate CapSight CSV files')
    parser.add_argument('file', nargs='?', help='Path to CSV file')
    parser.add_argument('--market', help='Expected market slug for comps validation')
    parser.add_argument('--all-markets', action='store_true', help='Validate all market template files')
    parser.add_argument('--strict', action='store_true', help='Strict mode - fail on any warnings')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.all_markets:
        print("🔍 Validating all market template files...")
        total_errors = 0
        total_warnings = 0
        
        # Check for template files
        template_files = []
        markets = ['dfw', 'ie', 'atl', 'phx', 'sav']
        
        for market in markets:
            fund_file = f'templates/fundamentals_{market}.csv'
            comp_file = f'templates/comps_{market}.csv'
            
            if os.path.exists(fund_file):
                template_files.append(('fundamentals', fund_file, market))
            if os.path.exists(comp_file):
                template_files.append(('comps', comp_file, market))
        
        if not template_files:
            print("❌ No template files found. Expected files like templates/comps_dfw.csv")
            sys.exit(1)
        
        for file_type, file_path, market in template_files:
            print(f"\n📋 Validating {file_type} for {market.upper()}: {file_path}")
            
            if file_type == 'fundamentals':
                errors = validate_fundamentals(file_path)
                warnings = []  # Fundamentals don't have separate warnings yet
            else:
                errors = validate_comps(file_path, market)
                warnings = []  # Warnings are printed within validate_comps
            
            if errors:
                print(f"   ❌ {len(errors)} errors in {file_path}")
                for error in errors:
                    print(f"     • {error}")
                total_errors += len(errors)
            else:
                print(f"   ✅ {file_path} passed validation")
        
        print(f"\n📊 SUMMARY: {len(template_files)} files validated")
        print(f"   Total errors: {total_errors}")
        print(f"   Total warnings: {total_warnings}")
        
        if total_errors > 0:
            print("❌ Validation failed - fix errors before deployment")
            sys.exit(1)
        elif args.strict and total_warnings > 0:
            print("❌ Strict mode - warnings present, aborting")
            sys.exit(1)
        else:
            print("✅ All validations passed!")
            sys.exit(0)
    
    if not args.file:
        parser.error("Either --all-markets or file argument is required")
    
    # Single file validation (existing logic)
    filename = args.file.lower()
    if 'fundamentals' in filename:
        print(f"Validating fundamentals file: {args.file}")
        errors = validate_fundamentals(args.file)
    elif 'comps' in filename:
        print(f"Validating comps file: {args.file}")
        errors = validate_comps(args.file, args.market)
    else:
        print("Error: Cannot determine file type. Filename should contain 'fundamentals' or 'comps'")
        sys.exit(1)
    
    if errors:
        print(f"\n{len(errors)} VALIDATION ERRORS:")
        for error in errors:
            print(f"  ❌ {error}")
        sys.exit(1)
    else:
        print("✅ Validation passed!")
        sys.exit(0)

if __name__ == '__main__':
    main()
