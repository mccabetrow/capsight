# Supabase CORS Configuration Guide

## Step 1: Access Supabase Dashboard

1. Go to [supabase.com](https://supabase.com) and sign in
2. Select your project: `azwkiifefkwewruyplcj`
3. Go to **Settings** → **API** (in the left sidebar)

## Step 2: Configure CORS Origins

Scroll down to the **CORS Origins** section and add your production domains:

### Production Domains to Add:
```
https://your-app-name.vercel.app
https://*.vercel.app
https://app.capsight.ai
https://capsight.ai
http://localhost:3000
http://localhost:3001
```

### How to Add CORS Origins:

1. **Find CORS Configuration**:
   - In Supabase Dashboard → Settings → API
   - Scroll to "CORS Origins" section

2. **Add Each Domain**:
   - Click "Add a new CORS origin"
   - Enter each URL from the list above
   - Click "Save" after each entry

3. **Wildcard Support**:
   - `https://*.vercel.app` covers all your Vercel preview deployments
   - `https://app.capsight.ai` for your custom domain (if you have one)

## Step 3: Verify CORS Settings

After adding domains, your CORS origins should include:
- Your production Vercel URL
- Preview deployment URLs (*.vercel.app)
- Local development (localhost:3000, localhost:3001)
- Any custom domains you plan to use

## Alternative: SQL Method (Advanced)

If you need to configure CORS programmatically:

```sql
-- Connect to your Supabase SQL Editor
-- Settings → SQL Editor → New Query

-- View current CORS settings
SELECT * FROM pg_settings WHERE name LIKE '%cors%';

-- Note: CORS is typically managed through the Supabase Dashboard
-- The SQL method is mainly for viewing current settings
```

## Step 4: Test CORS Configuration

After setting up CORS origins, test with:

```javascript
// Test in browser console on your production site
fetch('https://azwkiifefkwewruyplcj.supabase.co/rest/v1/', {
  headers: {
    'apikey': 'your-anon-key',
    'Authorization': 'Bearer your-anon-key'
  }
})
.then(response => console.log('CORS OK:', response.status))
.catch(error => console.error('CORS Error:', error));
```

## Troubleshooting CORS Issues

If you get CORS errors:

1. **Check Origins**: Ensure exact domain match (https vs http)
2. **Wait**: CORS changes can take a few minutes to propagate
3. **Clear Cache**: Clear browser cache and try again
4. **Check Logs**: Supabase Dashboard → Logs for CORS rejection messages

## Security Notes

- Never add `*` as a CORS origin (security risk)
- Use specific domains only
- Remove localhost entries before production (optional security measure)
