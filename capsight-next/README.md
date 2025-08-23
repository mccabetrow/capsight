# CapSight Frontend - Production Next.js Application

A pixel-perfect, production-ready Next.js + Tailwind UI for CapSight industrial CRE valuations.

## 🚀 Features

- **Fast & Responsive**: Built with Next.js 14 App Router and Tailwind CSS
- **Accessible**: WCAG 2.1 AA compliant with semantic HTML and ARIA labels
- **Real-time Data**: SWR for efficient data fetching and caching
- **Secure**: Read-only access using Supabase anon key only
- **Production Ready**: TypeScript strict mode, ESLint, comprehensive testing

## 📋 Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS 3.3
- **Data Fetching**: SWR for caching and revalidation
- **Database**: Supabase (read-only via views)
- **Testing**: Playwright (e2e), Jest (unit)
- **Performance**: Lighthouse CI integration

## 🛠 Setup Instructions

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Supabase project with schema deployed

### Installation

1. **Install dependencies:**
   ```bash
   cd capsight-next
   npm install
   ```

2. **Environment setup:**
   ```bash
   # Copy .env.local and fill in your Supabase credentials
   NEXT_PUBLIC_SUPABASE_URL=https://azwkiifefkwewruyplcj.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=[your-anon-key]
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000)

### 🏗 Build & Deploy

**Local build:**
```bash
npm run build
npm start
```

**Vercel deployment:**
1. Connect your GitHub repo to Vercel
2. Set environment variables in Vercel dashboard
3. Deploy automatically on push to main

## 🧪 Testing

**End-to-end tests:**
```bash
npm run test:e2e      # Run Playwright tests
npm run test:e2e:ui   # Run with UI
```

**Unit tests:**
```bash
npm run test          # Run Jest tests
npm run test:watch    # Watch mode
```

**Lighthouse performance:**
```bash
npm run lighthouse    # Performance audit
```

## 📊 Performance Targets

- **Performance**: ≥95
- **Accessibility**: ≥95  
- **SEO**: ≥90
- **Bundle size**: <200KB gzipped

## 🎨 Design System

### Colors
- **Primary**: Blue (#2563eb)
- **Text**: Gray scale (900, 700, 600, 500)
- **Background**: Gray-50

### Typography
- **Font**: Inter (system fallback)
- **Sizes**: text-4xl (hero), text-xl (section), text-sm (table)

### Components
- **Cards**: rounded-2xl, shadow-card, p-5
- **Buttons**: focus-ring, transition-colors
- **Forms**: focus-ring, proper labels

## 📖 Component Architecture

```
src/
├── app/
│   ├── layout.tsx          # Root layout with header
│   └── page.tsx            # Main valuation screen
├── components/
│   ├── MarketSelect.tsx    # Market dropdown
│   ├── NoiInput.tsx        # NOI input with formatting
│   ├── ValuationCard.tsx   # Results display
│   ├── BandBar.tsx         # Visual range indicator
│   ├── FundamentalsCard.tsx# Market metrics
│   ├── CompsTable.tsx      # Comparable sales
│   ├── EmptyState.tsx      # No data states
│   ├── ErrorState.tsx      # Error handling
│   ├── LoadingSkeleton.tsx # Loading states
│   └── Kpi.tsx             # Metric display
├── lib/
│   ├── supabaseClient.ts   # Supabase config
│   ├── fetchFundamentals.ts# Market data
│   ├── fetchComps.ts       # Comparable sales
│   ├── fetchValuation.ts   # API integration
│   ├── format.ts           # Formatting utilities
│   └── types.ts            # TypeScript types
└── styles/
    └── globals.css         # Tailwind + custom styles
```

## 🔌 API Integration

### Valuation Endpoint
```typescript
GET /api/value?market_slug=dfw&noi_annual=1200000

Response:
{
  "cap_rate_mid": 6.2,
  "cap_rate_band_bps": 50,
  "value_low": 18032786,
  "value_mid": 19672131,
  "value_high": 21505376,
  "n": 12
}
```

### Supabase Views (Read-only)
- `v_market_fundamentals_latest` - Market metrics
- `v_verified_sales_18mo` - Comparable sales

## ♿ Accessibility Features

- **Semantic HTML**: Proper heading hierarchy, form labels
- **ARIA**: Labels, descriptions, live regions
- **Keyboard Navigation**: Tab order, Enter/Space handlers
- **Screen Reader**: Alt text, meaningful labels
- **Focus Management**: Visible focus rings, proper tabindex

## 📱 Responsive Design

- **Mobile**: Single column, sticky CTA
- **Tablet**: Responsive grid, touch-friendly
- **Desktop**: 12-column grid, hover states

## 🔍 SEO Optimizations

- **Meta tags**: Title, description, OG image
- **Structured data**: JSON-LD for real estate
- **Performance**: Code splitting, image optimization
- **Lighthouse**: Automated SEO scoring

## 🚨 Error Handling

- **Network errors**: Retry buttons, user feedback
- **Validation**: Form validation with clear messages  
- **Loading states**: Skeleton components, progress indicators
- **Empty states**: Helpful messaging, alternative actions

## 📈 Analytics Events

```typescript
// Stub implementation included
track('valuation_submit', { market, noi })
track('valuation_success', { market, noi, result })
track('valuation_error', { market, error })
```

## 🔒 Security

- **No service keys**: Browser uses anon key only
- **Read-only access**: Views with RLS policies
- **Input validation**: Sanitized user inputs
- **CSRF protection**: Next.js built-in

## 📝 Testing Strategy

### E2E Tests (Playwright)
- Form submission flow
- Valuation display
- Error states
- Responsive layout

### Unit Tests (Jest)
- Formatting functions
- Component rendering
- Data fetching hooks

## 🚀 Production Checklist

- [ ] Environment variables configured
- [ ] Supabase schema deployed
- [ ] API endpoint accessible
- [ ] Lighthouse scores met
- [ ] E2E tests passing
- [ ] Error monitoring setup
- [ ] Analytics integration
- [ ] CDN configuration

## 📚 Key Files Summary

This Next.js application provides a complete, production-ready frontend for CapSight with:

1. **Modern React patterns** (hooks, context, error boundaries)
2. **Accessibility-first design** (WCAG 2.1 AA compliance)
3. **Performance optimization** (SWR caching, code splitting)
4. **Comprehensive testing** (unit + e2e coverage)
5. **Production deployment** (Vercel-ready configuration)

The application reads market data from secure Supabase views, calls the valuation API, and presents results in an intuitive, accessible interface suitable for professional CRE users.

---

**Ready for production deployment with proper environment configuration.**
