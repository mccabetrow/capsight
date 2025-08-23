# CapSight - Industrial CRE Valuation Platform

CapSight is a lightweight, accurate valuation tool for industrial commercial real estate assets. It provides AI-powered valuations with confidence intervals for 5 pilot markets: Dallas-Fort## 🔄 Data Updates

To update market data:

**Option 1: CLI Tool (Recommended)**
1. Place new CSV files in `templates/`
2. Run: `cd tools && python seed_markets.py --all --verbose`

**Option 2: Manual Process**
1. Export new data to CSV format
2. Validate using `validate_csv.py`
3. Import via Supabase dashboard
4. Verify via the frontend UIDFW), Inland Empire (IE), Atlanta (ATL), Phoenix (PHX), and Savannah (SAV).

## �️ Architecture

- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Backend**: Next.js API routes
- **Database**: Supabase (PostgreSQL) with Row Level Security (RLS)
- **Deployment**: Vercel-ready with environment variables

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Supabase account
- Vercel account (for deployment)

### 1. Environment Setup

Create `.env.local` file:
```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 2. Database Setup

1. Create a new Supabase project
2. Run the schema setup:
   ```bash
   psql -h your-db-host -U postgres -d postgres -f schema/schema.sql
   ```
   Or copy/paste the contents of `schema/schema.sql` into the Supabase SQL Editor

### 3. Data Import

Import sample data using the CSV templates:

```bash
# Validate CSV files first
python validate_csv.py templates/fundamentals_dfw.csv
python validate_csv.py templates/comps_dfw.csv --market dfw

# Import via Supabase dashboard or use the import scripts
```

### 4. Frontend Setup

```bash
npm install
npm run dev
```

Visit `http://localhost:3000` to see the application.

## 📊 Data Templates

CSV templates are provided for all 5 markets:

### Fundamentals Data
- `templates/fundamentals_dfw.csv`
- `templates/fundamentals_ie.csv` 
- `templates/fundamentals_atl.csv`
- `templates/fundamentals_phx.csv`
- `templates/fundamentals_sav.csv`

### Comparable Sales Data
- `templates/comps_dfw.csv`
- `templates/comps_ie.csv`
- `templates/comps_atl.csv`
- `templates/comps_phx.csv`
- `templates/comps_sav.csv`

## 🔍 Data Validation

Use the Python validator before importing:

```bash
python validate_csv.py templates/fundamentals_dfw.csv
python validate_csv.py templates/comps_dfw.csv --market dfw
```

The validator checks:
- Required headers and data types
- Value ranges and constraints
- Cross-field consistency (cap rates, price per sq ft)
- Market slug validation
- Date formats and enums

## 🛠️ Market Data Management CLI

The `tools/seed_markets.py` CLI provides robust market data seeding and validation with comprehensive error handling and auditability.

### Features
- **Validate & Upload**: CSV validation with automatic upsert to Supabase
- **Batch Operations**: Process all markets or specific ones
- **Dry-run Mode**: Test validation without making changes  
- **Audit Logging**: Comprehensive summary with record counts and error details
- **Fail-safe**: Aborts on partial failures to maintain data integrity
- **Environment Detection**: Automatic staging/production environment handling

### Setup
```bash
cd tools
pip install -r requirements.txt
```

### Usage Examples
```bash
# Dry-run validation (recommended first step)
python seed_markets.py --all --dry-run

# Seed specific market
python seed_markets.py --market dfw --verbose

# Seed all markets with summary
python seed_markets.py --all --verbose

# Production deployment (with service key)
SUPABASE_URL=https://xxx.supabase.co SUPABASE_SERVICE_KEY=xxx python seed_markets.py --all
```

### CLI Options
- `--market {dfw,ie,atl,phx,sav}`: Seed specific market
- `--all`: Process all markets
- `--dry-run`: Validate without uploading
- `--verbose`: Detailed logging and summary table
- `--help`: Show all options

### Environment Variables
```bash
SUPABASE_URL=https://your-project.supabase.co        # Required
SUPABASE_SERVICE_KEY=your-service-role-key           # Required for upload
```

### Integration
The CLI is integrated into `deploy-enhanced.sh` for automated staging deployment and validation.

## � Market Coverage

| Market | Code | Coverage Area |
|--------|------|---------------|
| Dallas-Fort Worth | `dfw` | Dallas, Fort Worth, Irving, Plano |
| Inland Empire | `ie` | Riverside, San Bernardino, Ontario |
| Atlanta | `atl` | Atlanta metro, Marietta, Lawrenceville |
| Phoenix | `phx` | Phoenix, Tempe, Chandler, Scottsdale |
| Savannah | `sav` | Savannah, Pooler, Richmond Hill |

## 🔐 Security Features

- **Row Level Security (RLS)**: Database-level access control
- **Public Views**: Safe data access for frontend
- **Service Role Key**: Backend-only for sensitive operations
- **Environment Variables**: No hardcoded secrets
- **Input Validation**: Comprehensive data validation

## 🎯 API Endpoints

### POST /api/value
Property valuation endpoint

**Request:**
```json
{
  "market_slug": "dfw",
  "noi_annual": 1500000,
  "building_sf": 100000
}
```

**Response:**
```json
{
  "valuation_usd": 25000000,
  "confidence_interval": [23750000, 26250000],
  "cap_rate_pct": 6.0,
  "price_per_sf_usd": 250,
  "methodology": "weighted_median_cap_rate",
  "comp_count": 8
}
```
## 🧪 Testing

Run the validation on sample data:

```bash
# Test all market templates
python validate_csv.py templates/fundamentals_dfw.csv
python validate_csv.py templates/fundamentals_ie.csv
python validate_csv.py templates/fundamentals_atl.csv
python validate_csv.py templates/fundamentals_phx.csv
python validate_csv.py templates/fundamentals_sav.csv

python validate_csv.py templates/comps_dfw.csv --market dfw
python validate_csv.py templates/comps_ie.csv --market ie
python validate_csv.py templates/comps_atl.csv --market atl
python validate_csv.py templates/comps_phx.csv --market phx
python validate_csv.py templates/comps_sav.csv --market sav
```

## 🚢 Deployment

### Vercel Deployment

1. Connect your GitHub repository to Vercel
2. Set environment variables in Vercel dashboard:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
3. Deploy automatically on git push

### Manual Deployment

```bash
npm run build
npm run start
```

## 📁 Project Structure

```
├── pages/
│   ├── api/
│   │   └── value.ts          # Valuation API endpoint
│   └── index.tsx             # Main UI
├── schema/
│   └── schema.sql            # Database schema with RLS
├── templates/
│   ├── fundamentals_*.csv    # Market fundamentals data
│   └── comps_*.csv          # Comparable sales data
├── tools/
│   ├── seed_markets.py       # CLI for market data management
│   └── requirements.txt      # Tools dependencies
├── validate_csv.py           # Data validation script
└── README.md                # This file
```

## � Data Updates

To update market data:

1. Export new data to CSV format
2. Validate using `validate_csv.py`
3. Import via Supabase dashboard
4. Verify via the frontend UI

## 📈 Accuracy Monitoring

The system includes built-in accuracy monitoring:
- MAPE (Mean Absolute Percentage Error) tracking
- Confidence interval coverage analysis  
- Automated alerts for data quality issues
- Monthly accuracy reports

## 🆘 Troubleshooting

### Common Issues

1. **Database connection errors**: Check Supabase URL and keys
2. **RLS policy errors**: Ensure anon key has proper grants
3. **Import errors**: Validate CSV files first
4. **Missing data**: Check that sample data was imported

### Support

For technical issues:
1. Check the browser console for errors
2. Verify environment variables are set
3. Test database connectivity in Supabase dashboard
4. Validate CSV data format

## 🚀 Production Readiness

This MVP includes:
- ✅ Production schema with constraints and indexes
- ✅ Row Level Security (RLS) for data protection
- ✅ Environment variable configuration
- ✅ Input validation and error handling
- ✅ Responsive UI with professional styling
- ✅ CSV templates and validation tools
- ✅ Deployment-ready configuration

Ready for pilot launch and customer demos.

cd backend
pytest

# Frontend tests  
cd frontend
npm test

# Integration tests
npm run test:e2e
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 📞 Support

- **Documentation**: [docs.capsight.ai](https://docs.capsight.ai)
- **Support**: support@capsight.ai
- **Sales**: sales@capsight.ai

---

**⚠️ Legal Disclaimer**: CapSight provides analytical tools for informational purposes only. All predictions and forecasts are estimates based on historical data and should not be considered investment advice. Real estate investments carry inherent risks, and past performance does not guarantee future results. Consult with qualified professionals before making investment decisions.
