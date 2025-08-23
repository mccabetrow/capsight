# CapSight Production Deployment Guide

## Prerequisites Setup

### 1. Install Docker Desktop
Download and install Docker Desktop from: https://www.docker.com/products/docker-desktop/

### 2. Replace Environment Placeholders

**Backend (.env.production):**
```bash
# Replace these 10 placeholders with your actual keys:
STRIPE_SECRET_KEY=sk_live_[YOUR_LIVE_SECRET_KEY]
STRIPE_WEBHOOK_SECRET=whsec_[YOUR_WEBHOOK_SECRET]
SMTP_PASSWORD=[YOUR_SENDGRID_API_KEY]
MAPBOX_TOKEN=pk.[YOUR_MAPBOX_TOKEN]
MLS_API_KEY=[YOUR_MLS_API_KEY]
ZILLOW_API_KEY=[YOUR_ZILLOW_API_KEY]
RENTSPREE_API_KEY=[YOUR_RENTSPREE_API_KEY]
SENTRY_DSN=[YOUR_SENTRY_DSN]
AWS_ACCESS_KEY_ID=[YOUR_AWS_ACCESS_KEY]
AWS_SECRET_ACCESS_KEY=[YOUR_AWS_SECRET_KEY]
```

**Frontend (.env.production):**
```bash
# Replace these 6 placeholders with your actual keys:
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_[YOUR_LIVE_PUBLISHABLE_KEY]
VITE_MAPBOX_TOKEN=pk.[YOUR_MAPBOX_TOKEN]
VITE_GA_TRACKING_ID=G-[YOUR_GA4_ID]
VITE_SENTRY_DSN=[YOUR_FRONTEND_SENTRY_DSN]
VITE_HOTJAR_ID=[YOUR_HOTJAR_ID]
VITE_INTERCOM_APP_ID=[YOUR_INTERCOM_APP_ID]
```

## Deployment Commands

### Option A: Docker Compose (Recommended)
```powershell
# Deploy backend + database
.\deploy-prod.bat

# Check status
docker-compose -f docker-compose.prod.yml ps

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Option B: Manual Development Server (If no Docker)
```powershell
# Backend
cd backend
pip install -r requirements.txt
set DATABASE_URL=sqlite:///./capsight_prod.db
uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env.production

# Frontend (separate terminal)
cd frontend
npm install
npm run build
npm run preview
```

## Validation Commands

### 1. Health Checks
```powershell
# API health
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ready

# API docs
curl -f http://localhost:8000/openapi.json
```

### 2. Auth Flow Test
```powershell
# Register test user
$registerResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" -Method POST -ContentType "application/json" -Body '{"email":"founder@capsight.ai","password":"CapSight#2025","full_name":"Founder"}'

# Login
$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"founder@capsight.ai","password":"CapSight#2025"}'

$token = $loginResponse.access_token

# Test protected route
$headers = @{"Authorization" = "Bearer $token"}
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users/me" -Headers $headers
```

### 3. ML Pipeline Test
```powershell
# Seed properties
$headers = @{"Authorization" = "Bearer $token"; "Content-Type" = "application/json"}
$property = '{"address":"123 Main St","city":"Austin","state":"TX","zip":"78701","type":"multifamily","units":24,"sqft":22000,"current_rent":145000,"noi":95000,"cap_rate":0.062,"source":"seed"}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/data/properties/ingest" -Method POST -Headers $headers -Body "[$property]"

# Run forecasts
$forecastBody = '{"market":"ALL","asset_type":"ALL","horizon_months":6}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/forecasts/run" -Method POST -Headers $headers -Body $forecastBody

# Generate opportunities
$oppBody = '{"market":"ALL","asset_type":"ALL","horizon_months":6}'
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/opportunities/recompute" -Method POST -Headers $headers -Body $oppBody

# Get opportunities
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/opportunities?limit=10&sort=-arbitrage_score" -Headers $headers
```

## Frontend Build & Deploy

### Local Build
```powershell
cd frontend
npm run build
```

### Deploy to Vercel
1. Install Vercel CLI: `npm install -g vercel`
2. Login: `vercel login`
3. Deploy: `vercel --prod`
4. Set environment variables in Vercel dashboard

### Deploy to Netlify
1. Install Netlify CLI: `npm install -g netlify-cli`
2. Login: `netlify login`
3. Deploy: `netlify deploy --prod --dir=dist`

## Production Domain Setup

### 1. DNS Configuration
```
api.capsight.ai -> Your backend server IP
app.capsight.ai -> Your frontend hosting (Vercel/Netlify)
capsight.ai -> Landing page
```

### 2. SSL/TLS
- Use Cloudflare or similar for SSL termination
- Or configure Let's Encrypt in your reverse proxy

### 3. CORS Update
Update backend `.env.production`:
```bash
CORS_ORIGINS=["https://capsight.ai","https://app.capsight.ai"]
```

## Monitoring Setup

### 1. Error Tracking
- Sign up for Sentry.io
- Add DSN to both backend and frontend env files

### 2. Analytics
- Setup Google Analytics 4
- Add GA4 ID to frontend env

### 3. User Analytics
- Setup Hotjar for user behavior tracking
- Setup Intercom for customer support

## Troubleshooting

### Common Issues
1. **CORS errors**: Check CORS_ORIGINS in backend env
2. **401 errors**: Verify JWT_SECRET is set correctly
3. **Database errors**: Run migrations with alembic
4. **Build errors**: Check node version (16+) and npm install

### Log Commands
```powershell
# Backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Specific service logs
docker-compose -f docker-compose.prod.yml logs postgres redis nginx
```

## Next Steps After Deployment
1. Test all user flows in production
2. Setup monitoring and alerting
3. Configure backup strategy
4. Setup CI/CD pipeline
5. Begin pilot outreach campaign
