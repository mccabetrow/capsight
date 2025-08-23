# Demo Mode

Demo mode allows users to explore the CapSight valuation platform without accessing live data or making any network requests. This is useful for demonstrations, training, and showcasing the platform's capabilities.

## Overview

When demo mode is enabled:
- ✅ **UI interactions remain identical** - All buttons, forms, and workflows function normally
- ✅ **Valuation logic preserved** - Same calculation displays and confidence intervals  
- ✅ **Realistic data** - Pre-generated valuations based on actual market patterns
- 🚫 **Network writes disabled** - No data is sent to servers or databases
- 🔒 **Privacy protected** - All addresses are masked (e.g., "****5 Legacy Dr, Dallas")
- 🎭 **Visual indicator** - Demo ribbon clearly identifies the mode

## Activation

### URL Parameter
Add `?demo=1` to any URL to enable demo mode:
```
https://capsight.com/?demo=1
https://capsight.com/valuation?demo=1&market=dfw
```

### Development Toggle
In development environments, a toggle button appears in the UI to easily switch demo mode on/off.

### Persistence
Demo mode persists across navigation within the session. To exit, remove the `?demo=1` parameter or use the development toggle.

## Demo Dataset

### Coverage
The demo includes pre-generated valuations for:
- **Markets**: DFW, Austin, San Antonio
- **Property Sizes**: 100k SF, 180k SF, 250k SF
- **NOI Ranges**: $525k - $1.95M annually

### Data Structure
Each demo valuation includes:
- Complete valuation results with confidence intervals
- Top 5 comparable sales with masked addresses
- Calculation methodology and adjustments
- Fallback reasons when applicable
- Market condition indicators

### File Location
Demo data is stored in `/public/demo/*.json`:
```
/public/demo/
  ├── dfw-250k-sf.json
  ├── aus-180k-sf.json
  └── sat-100k-sf.json
```

## Implementation Details

### Client-Side Detection
```javascript
// Check for demo mode
const isDemoMode = new URLSearchParams(window.location.search).get('demo') === '1';

// Load demo data instead of API call
if (isDemoMode) {
  const demoData = await fetch('/demo/dfw-250k-sf.json').then(r => r.json());
  return demoData;
}
```

### Demo Data Selection
Demo responses are selected based on input parameters:
- **Market + Size matching**: Exact match when available
- **Fallback logic**: Closest size match within market
- **Default response**: DFW 250k SF for unknown combinations

### Network Request Blocking
```javascript
// Prevent writes in demo mode
if (isDemoMode && isWriteOperation) {
  console.log('Demo mode: Write operation blocked');
  return { success: true }; // Simulate success
}
```

## Visual Indicators

### Demo Ribbon
A prominent banner appears at the top of the page:
- **Color**: Orange/amber for high visibility
- **Text**: "DEMO MODE - Sample Data Only"
- **Position**: Fixed top, always visible
- **Dismissible**: No - ensures awareness throughout session

### Address Masking
All property addresses show as:
- Format: `****[digit] [Street Name], [City]`
- Example: `****5 Legacy Dr, Dallas`
- Consistency: Same masking pattern across all demo data

## Use Cases

### Sales Demonstrations
- Show platform capabilities without exposing real client data
- Demonstrate various market scenarios and edge cases
- Present consistent results across multiple demos

### Training & Onboarding
- Allow new users to explore features safely
- Practice workflows without affecting live data
- Learn the interface with realistic scenarios

### Development & Testing
- Test UI components with consistent data
- Validate calculation displays and formatting
- Develop new features without database dependencies

## Technical Considerations

### Performance
- Demo data served statically from CDN
- No database queries or API calls
- Instant response times for better UX

### Data Privacy
- No real property addresses or sensitive information
- Masked identifiers protect confidentiality
- Safe for public demonstrations

### Maintenance
- Demo data periodically updated to reflect current market conditions
- JSON files versioned alongside application releases
- Automated tests validate demo data structure

## Development

### Adding New Demo Data
1. Create new JSON file in `/public/demo/`
2. Follow existing naming convention: `{market}-{size}-sf.json`
3. Include all required fields (see existing files for schema)
4. Update demo selection logic to include new combinations

### Testing Demo Mode
```bash
# Start development server
npm run dev

# Test with demo mode
open http://localhost:3000?demo=1

# Verify network requests are blocked
# Check browser DevTools Network tab - should show no API calls
```

### Deployment
Demo files are included in production builds automatically. No special configuration required.

---

**Security Note**: Demo mode is purely client-side. Sensitive data should never be included in demo files as they are publicly accessible.
