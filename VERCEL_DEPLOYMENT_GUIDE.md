# 🔐 VERCEL ENVIRONMENT VARIABLES SETUP

## Required Environment Variables for Production

Copy these to your Vercel dashboard at: https://vercel.com/your-username/capsight/settings/environment-variables

### 🗄️ Database Configuration
```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

### 📊 Data Sources
```bash
# FRED API for macro data (register at https://fred.stlouisfed.org/docs/api/api_key.html)
FRED_API_KEY=your-fred-api-key-here
```

### 🔗 Webhook Configuration
```bash
# n8n webhook endpoint
N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/capsight

# Webhook security (generate strong secret)
WEBHOOK_SECRET=your-webhook-secret-key-256-bit

# Your tenant identifier
TENANT_ID=capsight-production
```

### 🏗️ Application Configuration
```bash
NODE_ENV=production
```

## 🚀 Vercel Deployment Steps

### 1. Connect GitHub Repository
1. Go to https://vercel.com/new
2. Import your GitHub repository: `mccabetrow/capsight`
3. Configure project settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: `./` (root)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)
   - **Development Command**: `npm run dev` (default)

### 2. Set Environment Variables
In Vercel dashboard → Settings → Environment Variables:

| Variable | Value | Environment |
|----------|-------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://your-project.supabase.co` | Production, Preview, Development |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `your-anon-key` | Production, Preview, Development |
| `SUPABASE_SERVICE_ROLE_KEY` | `your-service-key` | Production, Preview, Development |
| `FRED_API_KEY` | `your-fred-key` | Production, Preview, Development |
| `N8N_WEBHOOK_URL` | `https://your-n8n.com/webhook/capsight` | Production, Preview, Development |
| `WEBHOOK_SECRET` | `your-256-bit-secret` | Production, Preview, Development |
| `TENANT_ID` | `capsight-production` | Production, Preview, Development |
| `NODE_ENV` | `production` | Production |

### 3. Deploy
- Vercel will automatically deploy when you push to `main` branch
- First deployment URL: `https://capsight-git-main-your-username.vercel.app`
- Production URL: `https://capsight.vercel.app` (if you have a custom domain)

## 🔧 Environment Variable Sources

### Supabase Keys
1. Go to https://app.supabase.com/project/your-project/settings/api
2. Copy:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public** → `NEXT_PUBLIC_SUPABASE_ANON_KEY` 
   - **service_role secret** → `SUPABASE_SERVICE_ROLE_KEY`

### FRED API Key
1. Register at https://fred.stlouisfed.org/docs/api/fred/
2. Request API key (free)
3. Copy key → `FRED_API_KEY`

### n8n Webhook
1. Create webhook endpoint in your n8n instance
2. Copy webhook URL → `N8N_WEBHOOK_URL`
3. Generate strong secret (e.g., `openssl rand -hex 32`) → `WEBHOOK_SECRET`

## ✅ Verification Checklist

After setting environment variables:
- [ ] All variables show in Vercel dashboard
- [ ] No variables marked as "undefined"
- [ ] Production, Preview, Development environments all set
- [ ] Redeploy triggered automatically
- [ ] Build succeeds without errors
- [ ] Environment validation passes

## 🚨 Security Notes

- **Never commit** `.env` files to git
- **Use strong secrets** (256-bit recommended)
- **Rotate keys** regularly in production
- **Limit API key permissions** where possible
- **Monitor usage** of external APIs (FRED rate limits)

## 📞 Support

If you encounter issues:
1. Check Vercel Function Logs
2. Verify all environment variables are set
3. Test individual API endpoints
4. Review build logs for errors
