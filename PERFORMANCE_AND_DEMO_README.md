# CapSight - Performance Testing Implementation

## 🚀 Performance Testing Overview

This implementation adds comprehensive k6 performance testing to validate API response times, throughput, and reliability under realistic load conditions.

### Key Features Added:

## 📊 k6 Load Testing (`/perf/`)

### Test Coverage
- **Load Pattern**: Ramps 1→50 virtual users over 2 minutes
- **Markets Tested**: DFW, AUS, HOU, SAT, PHX (5 markets)
- **Property Types**: 12 realistic payload variations across different building sizes
- **Thresholds**: 95th percentile <300ms, failure rate <0.5%, rate limits handled gracefully

### Quick Start
```bash
# Run performance tests locally
docker run -i loadimpact/k6 run - < perf/value.js

# Test against staging
docker run -e PERF_BASE_URL=https://staging.capsight.com -i loadimpact/k6 run - < perf/value.js
```

### GitHub Actions Integration
- **Trigger**: Pull requests affecting backend/API code
- **Environment**: Runs against staging environment (`PERF_BASE_URL`)
- **Outputs**: JUnit XML, JSON results, HTML reports
- **PR Integration**: Automated comments with performance summary
- **Failure Handling**: PR blocked if thresholds breached

## 🎭 Demo Mode Implementation

### Overview
Complete demo mode functionality allowing safe exploration without live data access.

### Features
- **URL Activation**: Add `?demo=1` to any URL
- **Visual Indicators**: Orange demo ribbon, development toggle button
- **Data Protection**: All addresses masked (e.g., "****5 Legacy Dr, Dallas")
- **Realistic Data**: Pre-generated valuations based on actual market patterns
- **Network Safety**: All write operations blocked, read operations serve static data

### Demo Dataset
```
/public/demo/
  ├── dfw-250k-sf.json    # Dallas: 250k SF, $28.75M valuation
  ├── aus-180k-sf.json    # Austin: 180k SF, $12.75M valuation  
  └── sat-100k-sf.json    # San Antonio: 100k SF, $8.95M valuation
```

### Usage
```javascript
// Check demo mode
const { isDemoMode, getDemoData } = useDemo()

// Load demo data
if (isDemoMode) {
  const data = await getDemoData(market, buildingSf)
  return data
}
```

## 🔍 "How This Was Calculated" Modal

### Features
- **Method Information**: Algorithm version, confidence levels
- **Adjustment Details**: Time adjustments, outlier removal explanations  
- **Top Comparables**: 5 highest-weighted sales with masked addresses
- **Quality Metrics**: Sample size, dispersion, market conditions
- **Fallback Indicators**: Badge system for low sample, high dispersion, stale data

### Accessibility
- **Keyboard Navigation**: Full tab/shift-tab support with focus trapping
- **ESC to Close**: Standard modal escape behavior  
- **Screen Reader**: Proper ARIA roles and labels
- **Focus Management**: Returns focus to trigger button on close

### Integration
```tsx
const [showModal, setShowModal] = useState(false)

<button onClick={() => setShowModal(true)}>
  How this was calculated
</button>

<CalculationModal
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  data={valuationResult}
/>
```

## 🛠 Technical Architecture

### Frontend Structure
```
src/
├── app/
│   ├── layout.tsx              # Root layout with demo components
│   ├── page.tsx                # Homepage with navigation
│   ├── valuation/page.tsx      # Valuation form and results
│   └── admin/                  # Admin console (existing)
├── components/ui/
│   ├── DemoRibbon.tsx          # Demo mode indicator
│   ├── DemoToggle.tsx          # Development demo toggle
│   └── CalculationModal.tsx    # Calculation details modal
└── hooks/
    └── useDemo.ts              # Demo mode management
```

### Backend Integration
- **Demo Detection**: Client-side URL parameter checking
- **Data Selection**: Intelligent matching based on market + building size
- **Network Blocking**: Write operations prevented in demo mode
- **Fallback Logic**: Graceful degradation when demo files missing

## 🧪 Testing & Quality

### Performance Testing
- **Automated**: Runs on every PR via GitHub Actions
- **Thresholds**: Strict SLA enforcement with PR blocking
- **Reporting**: HTML reports with detailed metrics
- **Staging Validation**: Health checks before test execution

### Demo Mode Testing  
```bash
# Test demo mode locally
npm run dev
open http://localhost:3000/valuation?demo=1

# Verify network calls blocked
# Check DevTools Network tab - should show no API requests
```

### Accessibility Testing
- **Modal Focus**: Tab trapping verified
- **Screen Readers**: ARIA labels and roles tested
- **Keyboard Navigation**: ESC, Tab, Shift-Tab all functional

## 📝 Documentation

### Performance Testing
- **README**: `/perf/README.md` - Local testing, CI/CD setup, troubleshooting
- **CI Configuration**: `.github/workflows/perf.yml` - Full GitHub Actions setup

### Demo Mode
- **Guide**: `/docs/demo_mode.md` - Implementation details, use cases, maintenance
- **Data Structure**: JSON schema documentation for demo files

## 🚀 Deployment

### Environment Variables
```bash
# Performance testing
PERF_BASE_URL=https://staging.capsight.com

# Demo mode (optional)
NODE_ENV=development  # Enables demo toggle in UI
```

### GitHub Actions Setup
1. Set `PERF_BASE_URL` in repository variables
2. Ensure staging environment is accessible
3. Performance tests run automatically on PRs

### Production Considerations
- **Demo Toggle**: Only visible in development
- **Demo Files**: Served statically, included in build
- **Performance**: k6 tests can run against production for monitoring

## 🔄 Future Enhancements

### Performance Testing
- **Load Testing**: Extended duration tests for sustained load validation
- **Spike Testing**: Sudden traffic spike simulation  
- **Stress Testing**: Breaking point identification

### Demo Mode
- **More Markets**: Additional demo data for PHX, HOU markets
- **Property Types**: Retail, industrial, multifamily examples
- **Interactive Tours**: Guided demo flows for sales presentations

### Calculation Modal
- **Historical Trends**: Market appreciation charts
- **Sensitivity Analysis**: Cap rate impact visualization
- **Comparable Maps**: Geographic distribution of sales

---

## 🏃‍♂️ Quick Start Guide

1. **Performance Testing**:
   ```bash
   docker run -i loadimpact/k6 run - < perf/value.js
   ```

2. **Demo Mode**:
   ```
   http://localhost:3000/valuation?demo=1
   ```

3. **Development**:
   ```bash
   npm run dev
   # Demo toggle appears bottom-right in development
   ```

This implementation provides enterprise-grade performance validation, safe demo capabilities, and transparent calculation explanations while maintaining full backward compatibility with existing functionality.
