# Cypress E2E Commands Reference

## Local Development Commands

```bash
# Navigate to frontend directory
cd frontend

# Open Cypress Test Runner (Interactive GUI)
npm run cy:open

# Run all tests headlessly
npm run cy:run

# Run tests with specific browser
npx cypress run --browser edge
npx cypress run --browser chrome

# Run specific test file
npx cypress run --spec "cypress/e2e/auth/login.cy.ts"

# Run tests matching a pattern
npx cypress run --spec "cypress/e2e/**/*auth*.cy.ts"

# Run with environment variables
CYPRESS_MOCK_API=true npm run cy:run
CYPRESS_baseUrl=http://localhost:4173 npm run cy:run
```

## Full E2E with Server

```bash
# Run dev server + E2E tests (mocked API)
npm run test:e2e

# Run preview build + E2E tests (optimized for CI)
npm run test:e2e:ci

# Manual server + test workflow
npm run dev &          # Start dev server
npm run cy:run          # Run tests against dev server
```

## CI/GitHub Actions Commands

```bash
# Trigger manual workflow
gh workflow run cypress.yml

# Check workflow status
gh run list --workflow=cypress.yml

# View specific run logs
gh run view [RUN_ID]

# Download artifacts (screenshots/videos)
gh run download [RUN_ID]
```

## Verification & Setup

```bash
# Verify Cypress installation
npx cypress verify

# Check Cypress environment info
npx cypress info

# Install Cypress cache (if needed)
npx cypress install

# Clear Cypress cache
npx cypress cache clear
npx cypress cache list
```

## Environment Configuration

Create `frontend/cypress.env.json`:
```json
{
  "MOCK_API": true,
  "baseUrl": "http://localhost:3000",
  "API_URL": "http://localhost:5000",
  "TEST_USER_EMAIL": "testuser@capsight.com",
  "TEST_USER_PASSWORD": "TestPass123!",
  "TEST_ADMIN_EMAIL": "admin@capsight.com",
  "TEST_ADMIN_PASSWORD": "AdminPass123!"
}
```

## Test Structure Overview

```
✅ Authentication Tests
   - Login/logout flows
   - Form validation
   - Error handling
   - Social auth

✅ Protected Routes Tests  
   - Unauthenticated redirects
   - Navigation flows
   - Mobile navigation
   - Admin access control

✅ Dashboard Tests
   - Metrics loading
   - Charts and visualizations
   - Activity feeds
   - Performance tracking
   - Tier-based features

✅ Billing Tests
   - Subscription management
   - Payment method updates
   - Plan upgrades/downgrades
   - Usage limits
   - Tier restrictions

✅ API Fixtures
   - Auth responses
   - User data
   - Properties, opportunities, forecasts
   - Subscription details
   - Analytics data
```

## Key Files Created

```
frontend/cypress/
├── cypress.config.ts              # Main Cypress configuration
├── tsconfig.json                  # TypeScript config for Cypress
├── e2e/
│   ├── auth/
│   │   ├── login.cy.ts           # Login flow tests
│   │   └── logout.cy.ts          # Logout flow tests
│   ├── navigation/
│   │   └── protected-routes.cy.ts # Navigation & route protection
│   ├── dashboard/
│   │   └── dashboard.cy.ts       # Dashboard functionality
│   └── billing/
│       └── subscriptions.cy.ts   # Billing & subscription tests
├── fixtures/ (comprehensive API mocks)
│   ├── auth/
│   ├── users/
│   ├── properties/
│   ├── opportunities/
│   ├── forecasts/
│   ├── subscriptions/
│   ├── billing/
│   └── analytics/
└── support/
    ├── e2e.ts                    # Global setup & config
    └── commands.ts               # Custom commands

.github/workflows/
└── cypress.yml                   # CI/CD pipeline

frontend/
├── CYPRESS_GUIDE.md             # Complete testing guide
└── package.json                 # Updated with Cypress scripts
```

## Ready to Run!

The CapSight Cypress E2E suite is now fully configured and ready to use. All critical user journeys are covered with comprehensive test scenarios and fixtures.

🚀 **Quick Start**: `npm run cy:open` to begin testing!
