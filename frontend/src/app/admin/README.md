# CapSight Admin Console

The admin console provides operational oversight for the CapSight valuation system.

## Access

The admin console is protected by an `ADMIN_TOKEN` environment variable. Access it at `/admin` with the token as:

1. Query parameter: `/admin?token=your-admin-token`
2. Header: `X-Admin-Token: your-admin-token`
3. Cookie (set automatically after first auth)

## Environment Variables

```bash
# Required
ADMIN_TOKEN=your-secret-admin-token-here

# Database (inherited from main app)
DATABASE_URL=your-supabase-connection-string
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## Features

### 1. Accuracy Dashboard
- **Real-time SLA monitoring** across all markets
- **Per-market cards** showing MAPE, RMSE, Coverage, sample size
- **Status indicators**: Green (SLA met), Amber (warning), Red (critical)
- **Sparkline charts** for trend visualization (last 30 days when available)
- **Quick actions** to investigate accuracy issues

### 2. Market Management
- **Market status control** - enable/disable markets with reasons
- **Data refresh controls** - manually trigger materialized view refresh
- **Market health overview** with last update timestamps
- **Bulk operations** for multiple markets

### 3. Review Queue Management
- **Flagged transactions** requiring manual review
- **Approve/Reject workflow** with audit comments
- **Priority sorting** by issue type and severity
- **Bulk review actions** for efficiency

## Security

- **Server-side only**: No service role keys exposed to browser
- **Server actions**: All mutations go through Next.js server actions
- **Audit logging**: All admin actions are logged with timestamps
- **Token-based auth**: Simple but effective protection

## Database Dependencies

The admin console expects these database objects:

```sql
-- Views (should exist)
CREATE VIEW latest_accuracy AS ...
CREATE VIEW review_queue_view AS ...

-- Tables for admin actions
CREATE TABLE review_queue_actions (
  id BIGSERIAL PRIMARY KEY,
  review_id BIGINT NOT NULL,
  action TEXT NOT NULL, -- 'approve' | 'reject'
  comment TEXT,
  admin_user TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market status (should exist)
CREATE TABLE market_status (
  market_slug TEXT PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT true,
  reason TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Usage

1. **Daily monitoring**: Check accuracy dashboard for SLA compliance
2. **Market issues**: Disable problematic markets with clear reasons
3. **Data quality**: Process review queue items flagged by validation
4. **Performance**: Manually refresh materialized views if needed

## Development

To run locally:

1. Set `ADMIN_TOKEN` in your `.env.local`
2. Ensure database connection is configured
3. Navigate to `/admin?token=your-token`

## Security Notes

- Admin console is protected by middleware
- All mutations use server actions (no client-side DB access)
- CSP headers prevent XSS attacks
- Admin actions are audited and logged
