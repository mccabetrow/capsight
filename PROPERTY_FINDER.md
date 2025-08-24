# 🏢 Property Finder Feature

## Overview

The Property Finder feature allows users to input a city name and receive AI-powered recommendations for the top 5 commercial real estate investment opportunities in that market.

## How It Works

1. **City Input**: User enters a city name (e.g., "Dallas", "Atlanta", "Phoenix")
2. **Market Mapping**: System maps the city to one of our 5 pilot markets
3. **Data Analysis**: Retrieves market fundamentals and comparable sales data
4. **AI Scoring**: Uses ML algorithms to score and rank properties
5. **Results Display**: Shows top 5 properties with detailed investment metrics

## API Endpoints

### POST /api/predict-properties

**Request Body:**
```json
{
  "city": "Dallas",
  "investment_criteria": {
    "min_sf": 75000,
    "max_sf": 500000,
    "target_cap_rate": 7.0
  }
}
```

**Response:**
```json
{
  "success": true,
  "city": "Dallas",
  "market": "Dallas-Fort Worth",
  "recommendations": [
    {
      "id": "prop-dfw-1",
      "address": "1234 Commerce Blvd",
      "building_sf": 185000,
      "predicted_value": 22500000,
      "cap_rate": 8.2,
      "noi_annual": 1845000,
      "confidence_score": 0.89,
      "investment_score": 85,
      "reasoning": [
        "Strong 8.2% cap rate",
        "Institutional-grade size (185,000 SF)",
        "Hot market with 6.1% rent growth"
      ]
    }
  ],
  "market_insights": {
    "avg_cap_rate": 7.8,
    "vacancy_rate": 6.2,
    "rent_growth_yoy": 5.4,
    "market_trend": "hot"
  }
}
```

## React Components

### PropertyFinder

Main component for the property search interface:
- City input field with validation
- Loading states and error handling
- Results display with market insights
- Investment scoring and reasoning

### Usage

```tsx
import { PropertyFinder } from '../components/PropertyFinder'

export default function PropertyPage() {
  return (
    <div>
      <h1>Find Investment Properties</h1>
      <PropertyFinder />
    </div>
  )
}
```

## Features

### 🎯 Smart City Mapping
- Maps any city to our 5 pilot markets
- Handles variations (Dallas, DFW, Fort Worth → dfw)
- Fallback to Dallas market if city not recognized

### 📊 Market Analysis
- Real-time market fundamentals
- Vacancy rates and rent growth trends
- Comparable sales analysis

### 🤖 AI Scoring Algorithm
- **Investment Score** (0-100): Overall investment attractiveness
- **Confidence Score** (0-1): Prediction reliability
- **Cap Rate Analysis**: Market-adjusted returns
- **Size Premium**: Institutional-grade property preference

### 📈 Investment Reasoning
- Automated reasoning for each property recommendation
- Market trend analysis
- Risk/reward explanations

## Supported Markets

1. **Dallas-Fort Worth (DFW)**
   - Cities: Dallas, Fort Worth, Plano, Frisco, Irving
   
2. **Atlanta (ATL)**
   - Cities: Atlanta, Marietta, Alpharetta, Sandy Springs
   
3. **Phoenix (PHX)**
   - Cities: Phoenix, Scottsdale, Tempe, Chandler
   
4. **Inland Empire (IE)**
   - Cities: Riverside, San Bernardino, Ontario
   
5. **Savannah (SAV)**
   - Cities: Savannah, Pooler

## Investment Scoring Factors

| Factor | Weight | Description |
|--------|---------|-------------|
| Cap Rate | High | Higher cap rates score better (8%+ = premium) |
| Building Size | Medium | Institutional preference (150k+ SF) |
| Market Growth | High | Rent growth trends (5%+ = hot market) |
| Vacancy Rate | Medium | Lower vacancy = better score |
| Confidence | Medium | Model prediction reliability |

## Error Handling

- **Invalid City**: Returns 404 with suggestion
- **No Data**: Graceful fallback with explanation
- **API Errors**: Development mode shows details
- **Loading States**: User-friendly indicators

## Testing

```bash
# Test the API directly
curl -X POST http://localhost:3000/api/predict-properties \
  -H "Content-Type: application/json" \
  -d '{"city":"Dallas","investment_criteria":{"min_sf":100000}}'

# Test in browser
npm run dev
# Navigate to: http://localhost:3000/properties
```

## Deployment Notes

- ✅ Vercel compatible
- ✅ No external dependencies
- ✅ Supabase integration for live data
- ✅ TypeScript strict mode
- ✅ Error boundaries and fallbacks
