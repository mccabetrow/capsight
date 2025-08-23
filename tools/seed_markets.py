#!/usr/bin/env python3
"""
Market Data Seeding Tool

Validates CSV files and uploads market data to Supabase with comprehensive
error handling and progress reporting.

Usage:
    python tools/seed_markets.py --market dfw
    python tools/seed_markets.py --all
    python tools/seed_markets.py --market dfw --dry-run
    python tools/seed_markets.py --market dfw --service-url https://xyz.supabase.co --service-key your-key
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import subprocess
import tempfile
import shutil

import requests
from tabulate import tabulate


# Market configuration
SUPPORTED_MARKETS = ['dfw', 'aus', 'hou', 'sat', 'phx', 'ie', 'atl', 'sav']

CSV_COLUMNS = [
    'address', 'market_slug', 'sale_date', 'price_total_usd', 'building_sf',
    'cap_rate_pct', 'property_type', 'year_built', 'noi_annual',
    'latitude', 'longitude'
]

class SeedMarketsError(Exception):
    """Base exception for market seeding operations."""
    pass


class ValidationError(SeedMarketsError):
    """CSV validation failed."""
    pass


class UploadError(SeedMarketsError):
    """Data upload failed.""" 
    pass


class MarketSeeder:
    """Main class for validating and uploading market data."""
    
    def __init__(self, service_url: Optional[str] = None, service_key: Optional[str] = None, 
                 dry_run: bool = False, verbose: bool = False):
        self.service_url = service_url or os.getenv('SUPABASE_URL')
        self.service_key = service_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY') 
        self.anon_key = os.getenv('SUPABASE_ANON_KEY')
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Results tracking
        self.results = []
        
        # Validate environment
        if not self.service_url:
            raise SeedMarketsError("SUPABASE_URL environment variable or --service-url required")
            
        # Use service key for admin operations, fallback to anon for public endpoints
        self.api_key = self.service_key if self.service_key else self.anon_key
        if not self.api_key:
            raise SeedMarketsError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY required")
            
        self.headers = {
            'apikey': self.api_key,
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }

    def validate_csv(self, market: str, csv_path: Path) -> Tuple[bool, str, Dict]:
        """Validate CSV using validate_csv_enhanced.py."""
        
        if not csv_path.exists():
            return False, f"CSV file not found: {csv_path}", {}
            
        try:
            # Run the existing validation script
            cmd = [
                sys.executable, 
                'validate_csv_enhanced.py',
                '--file', str(csv_path),
                '--market', market,
                '--quiet'  # Reduce output noise
            ]
            
            if self.verbose:
                print(f"Running validation: {' '.join(cmd)}")
                
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                # Parse validation output for stats
                lines = result.stdout.strip().split('\n')
                stats = {'rows_validated': 0, 'errors': 0, 'warnings': 0}
                
                for line in lines:
                    if 'rows processed' in line.lower():
                        try:
                            stats['rows_validated'] = int(line.split()[-1])
                        except (ValueError, IndexError):
                            pass
                    elif 'error' in line.lower() and 'count' in line.lower():
                        try:
                            stats['errors'] = int(line.split()[-1])
                        except (ValueError, IndexError):
                            pass
                            
                return True, "Validation passed", stats
                
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"Validation failed: {error_msg}", {}
                
        except FileNotFoundError:
            return False, "validate_csv_enhanced.py not found in current directory", {}
        except Exception as e:
            return False, f"Validation error: {str(e)}", {}

    def load_csv_data(self, csv_path: Path) -> List[Dict]:
        """Load CSV data into memory."""
        
        data = []
        
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            # Validate columns
            if not all(col in reader.fieldnames for col in CSV_COLUMNS):
                missing = [col for col in CSV_COLUMNS if col not in reader.fieldnames]
                raise ValidationError(f"Missing columns: {missing}")
                
            for row_num, row in enumerate(reader, 1):
                try:
                    # Type conversion and validation
                    processed_row = {
                        'address': row['address'].strip(),
                        'market_slug': row['market_slug'].strip().lower(),
                        'sale_date': row['sale_date'].strip(),
                        'price_total_usd': int(float(row['price_total_usd'])),
                        'building_sf': int(float(row['building_sf'])),
                        'cap_rate_pct': float(row['cap_rate_pct']),
                        'property_type': row['property_type'].strip(),
                        'year_built': int(float(row['year_built'])) if row['year_built'].strip() else None,
                        'noi_annual': int(float(row['noi_annual'])) if row['noi_annual'].strip() else None,
                        'latitude': float(row['latitude']) if row['latitude'].strip() else None,
                        'longitude': float(row['longitude']) if row['longitude'].strip() else None,
                    }
                    data.append(processed_row)
                    
                except (ValueError, KeyError) as e:
                    raise ValidationError(f"Row {row_num}: {str(e)}")
                    
        return data

    def upload_to_supabase(self, market: str, data: List[Dict]) -> Tuple[bool, str, Dict]:
        """Upload data to Supabase with upsert logic."""
        
        if self.dry_run:
            return True, f"Dry run: Would upload {len(data)} records", {'uploaded': len(data)}
            
        try:
            # Use the comps table (assuming this is the target)
            url = urljoin(self.service_url, '/rest/v1/comps')
            
            # Batch upload in chunks to avoid payload limits
            chunk_size = 1000
            total_uploaded = 0
            
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i + chunk_size]
                
                if self.verbose:
                    print(f"Uploading chunk {i//chunk_size + 1}/{(len(data)-1)//chunk_size + 1} ({len(chunk)} records)")
                
                # Use upsert to handle duplicates
                response = requests.post(
                    url,
                    headers={**self.headers, 'Prefer': 'resolution=merge-duplicates'},
                    json=chunk,
                    timeout=30
                )
                
                if response.status_code not in [200, 201, 204]:
                    error_detail = ""
                    try:
                        error_data = response.json()
                        error_detail = error_data.get('message', str(error_data))
                    except:
                        error_detail = response.text[:500]
                        
                    return False, f"Upload failed (HTTP {response.status_code}): {error_detail}", {}
                    
                total_uploaded += len(chunk)
                
                # Brief pause between chunks
                if i + chunk_size < len(data):
                    time.sleep(0.5)
                    
            return True, f"Successfully uploaded {total_uploaded} records", {
                'uploaded': total_uploaded,
                'chunks': (len(data) - 1) // chunk_size + 1
            }
            
        except requests.exceptions.Timeout:
            return False, "Upload timeout - try reducing batch size", {}
        except requests.exceptions.ConnectionError:
            return False, "Connection error - check SUPABASE_URL", {}
        except Exception as e:
            return False, f"Upload error: {str(e)}", {}

    def find_csv_file(self, market: str) -> Optional[Path]:
        """Find CSV file for a market in common locations."""
        
        # Common patterns and locations
        patterns = [
            f"data/{market}_comps.csv",
            f"data/{market.upper()}_comps.csv", 
            f"backend/data/{market}_comps.csv",
            f"backend/data/{market.upper()}_comps.csv",
            f"{market}_comps.csv",
            f"{market.upper()}_comps.csv",
            f"comps_{market}.csv",
            f"comps_{market.upper()}.csv",
        ]
        
        for pattern in patterns:
            path = Path(pattern)
            if path.exists():
                return path
                
        return None

    def process_market(self, market: str) -> Dict:
        """Process a single market: validate CSV and upload data."""
        
        market = market.lower()
        if market not in SUPPORTED_MARKETS:
            return {
                'market': market,
                'status': 'error',
                'message': f"Unsupported market. Supported: {', '.join(SUPPORTED_MARKETS)}",
                'rows': 0,
                'time_seconds': 0
            }
            
        start_time = time.time()
        
        # Find CSV file
        csv_path = self.find_csv_file(market)
        if not csv_path:
            return {
                'market': market,
                'status': 'error', 
                'message': 'CSV file not found',
                'rows': 0,
                'time_seconds': time.time() - start_time
            }
            
        if self.verbose:
            print(f"\nProcessing {market.upper()}: {csv_path}")
            
        # Step 1: Validate CSV
        try:
            valid, message, stats = self.validate_csv(market, csv_path)
            if not valid:
                return {
                    'market': market,
                    'status': 'validation_error',
                    'message': message,
                    'rows': 0,
                    'time_seconds': time.time() - start_time
                }
        except Exception as e:
            return {
                'market': market,
                'status': 'validation_error',
                'message': f"Validation exception: {str(e)}",
                'rows': 0,
                'time_seconds': time.time() - start_time
            }
            
        # Step 2: Load CSV data
        try:
            data = self.load_csv_data(csv_path)
            if not data:
                return {
                    'market': market,
                    'status': 'error',
                    'message': 'No data found in CSV',
                    'rows': 0,
                    'time_seconds': time.time() - start_time
                }
        except Exception as e:
            return {
                'market': market,
                'status': 'load_error',
                'message': str(e),
                'rows': 0,
                'time_seconds': time.time() - start_time
            }
            
        # Step 3: Upload to Supabase
        try:
            success, message, upload_stats = self.upload_to_supabase(market, data)
            status = 'success' if success else 'upload_error'
            
            return {
                'market': market,
                'status': status,
                'message': message,
                'rows': upload_stats.get('uploaded', len(data)),
                'time_seconds': time.time() - start_time
            }
            
        except Exception as e:
            return {
                'market': market,
                'status': 'upload_error',
                'message': f"Upload exception: {str(e)}",
                'rows': len(data),
                'time_seconds': time.time() - start_time
            }

    def seed_markets(self, markets: List[str]) -> bool:
        """Seed multiple markets and return success status."""
        
        print(f"🌱 Seeding {len(markets)} market(s): {', '.join(markets)}")
        if self.dry_run:
            print("🔍 DRY RUN MODE - No data will be uploaded")
        print()
        
        # Process each market
        for market in markets:
            result = self.process_market(market)
            self.results.append(result)
            
            # Show progress
            status_emoji = {
                'success': '✅',
                'validation_error': '❌',
                'load_error': '❌',  
                'upload_error': '❌',
                'error': '❌'
            }
            
            emoji = status_emoji.get(result['status'], '⚠️')
            print(f"{emoji} {result['market'].upper()}: {result['message']}")
            
        # Summary table
        self._print_summary()
        
        # Check for any failures
        failed_results = [r for r in self.results if r['status'] != 'success']
        
        if failed_results:
            print(f"\n❌ {len(failed_results)} market(s) failed. Aborting on partial failures.")
            return False
            
        print(f"\n✅ All {len(markets)} market(s) processed successfully!")
        return True

    def _print_summary(self):
        """Print a neat summary table."""
        
        if not self.results:
            return
            
        print("\n" + "="*80)
        print("📊 SEEDING SUMMARY")
        print("="*80)
        
        # Prepare table data
        table_data = []
        total_rows = 0
        total_time = 0.0
        
        for result in self.results:
            status_display = {
                'success': '✅ Success',
                'validation_error': '❌ Validation Failed',
                'load_error': '❌ Load Failed',
                'upload_error': '❌ Upload Failed', 
                'error': '❌ Error'
            }
            
            table_data.append([
                result['market'].upper(),
                status_display.get(result['status'], '⚠️ Unknown'),
                f"{result['rows']:,}",
                f"{result['time_seconds']:.1f}s",
                result['message'][:50] + ('...' if len(result['message']) > 50 else '')
            ])
            
            if result['status'] == 'success':
                total_rows += result['rows']
            total_time += result['time_seconds']
            
        # Print table
        headers = ['Market', 'Status', 'Rows', 'Time', 'Message']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Summary stats
        success_count = len([r for r in self.results if r['status'] == 'success'])
        
        print(f"\n📈 TOTALS:")
        print(f"   Markets Processed: {len(self.results)}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {len(self.results) - success_count}")
        print(f"   Rows Uploaded: {total_rows:,}")
        print(f"   Total Time: {total_time:.1f}s")


def main():
    """Main CLI entry point."""
    
    parser = argparse.ArgumentParser(
        description="Validate and seed market data to Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --market dfw                              # Seed Dallas market
  %(prog)s --all                                     # Seed all markets
  %(prog)s --market dfw --dry-run                    # Validate only, no upload
  %(prog)s --market dfw --verbose                    # Detailed output
  %(prog)s --all --service-url https://xyz.supabase.co --service-key your-key
        """
    )
    
    # Market selection (mutually exclusive)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--market', choices=SUPPORTED_MARKETS,
                      help='Market to seed')
    group.add_argument('--all', action='store_true',
                      help='Seed all supported markets')
    
    # Configuration
    parser.add_argument('--service-url', 
                       help='Supabase URL (or set SUPABASE_URL env var)')
    parser.add_argument('--service-key',
                       help='Supabase service role key (or set SUPABASE_SERVICE_ROLE_KEY env var)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Validate only, do not upload')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Detailed output')
    
    args = parser.parse_args()
    
    try:
        # Create seeder
        seeder = MarketSeeder(
            service_url=args.service_url,
            service_key=args.service_key, 
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        # Determine markets to process
        if args.all:
            markets = SUPPORTED_MARKETS
        else:
            markets = [args.market]
            
        # Process markets
        success = seeder.seed_markets(markets)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except SeedMarketsError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
