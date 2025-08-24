-- ===== SUPABASE INGESTION EVENTS & JOBS SCHEMA =====
-- Run this in your Supabase SQL Editor to add ingestion tracking and job management

-- Enable helpful extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- =========================================================
-- Ingestion events: every upstream write / webhook you accept
-- =========================================================
CREATE TABLE IF NOT EXISTS ingestion_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,                  -- e.g., 'market.fundamentals.upsert', 'comps.upsert'
  tenant_id TEXT NOT NULL DEFAULT 'default',
  payload JSONB NOT NULL,                    -- original request body
  payload_hash TEXT NOT NULL,                -- sha256 hex of payload
  source TEXT NOT NULL,                      -- 'supabase.edge', 'n8n', 'manual', etc.
  status TEXT NOT NULL DEFAULT 'received',   -- 'received' | 'validated' | 'applied' | 'failed'
  error TEXT,                                -- populate on failure
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  validated_at TIMESTAMPTZ,
  applied_at TIMESTAMPTZ,
  processed_records INTEGER DEFAULT 0,
  cache_invalidated TEXT[] DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ing_ev_unique
  ON ingestion_events(tenant_id, event_type, payload_hash);

CREATE INDEX IF NOT EXISTS idx_ing_ev_created ON ingestion_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ing_ev_status ON ingestion_events(status);
CREATE INDEX IF NOT EXISTS idx_ing_ev_event_type ON ingestion_events(event_type);

-- =====================================
-- Jobs: background long-running tasks
-- =====================================
CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id TEXT NOT NULL DEFAULT 'default',
  job_type TEXT NOT NULL,                   -- 'screen.batch', 'backtest.market', 'recompute.mts'
  status TEXT NOT NULL DEFAULT 'queued',    -- 'queued' | 'running' | 'succeeded' | 'failed'
  priority INTEGER NOT NULL DEFAULT 5,     -- 1 high .. 9 low
  request JSONB NOT NULL,                   -- input params
  result JSONB,                             -- outputs / summary
  error TEXT,                               -- message on failure
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  progress JSONB DEFAULT '{"percent": 0, "message": "queued"}'
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type, created_at DESC);

-- =========================================================
-- Cache metrics tracking
-- =========================================================
CREATE TABLE IF NOT EXISTS cache_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_type TEXT NOT NULL,                -- 'hit', 'miss', 'invalidation'
  cache_key TEXT NOT NULL,
  data_source TEXT NOT NULL,               -- 'macro', 'fundamentals', 'comps'
  tenant_id TEXT NOT NULL DEFAULT 'default',
  latency_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cache_metrics_created ON cache_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cache_metrics_source ON cache_metrics(data_source, created_at DESC);

-- =========================================================
-- API request tracking for performance monitoring
-- =========================================================
CREATE TABLE IF NOT EXISTS api_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INTEGER NOT NULL,
  response_time_ms INTEGER NOT NULL,
  tenant_id TEXT NOT NULL DEFAULT 'default',
  data_sources_used TEXT[] DEFAULT '{}',
  cache_hits INTEGER DEFAULT 0,
  cache_misses INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  correlation_id TEXT,
  error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_requests_created ON api_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_requests_endpoint ON api_requests(endpoint, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_requests_performance ON api_requests(response_time_ms DESC, created_at DESC);

-- =========================================================
-- Add CHECK constraints to existing tables for data validation
-- =========================================================

-- Market fundamentals validation
ALTER TABLE market_fundamentals 
ADD CONSTRAINT IF NOT EXISTS chk_vacancy_rate_pct 
CHECK (vacancy_rate_pct BETWEEN 0 AND 40);

ALTER TABLE market_fundamentals 
ADD CONSTRAINT IF NOT EXISTS chk_avg_cap_rate_pct 
CHECK (avg_cap_rate_pct BETWEEN 2 AND 20);

ALTER TABLE market_fundamentals 
ADD CONSTRAINT IF NOT EXISTS chk_yoy_rent_growth_pct 
CHECK (yoy_rent_growth_pct BETWEEN -20 AND 50);

ALTER TABLE market_fundamentals 
ADD CONSTRAINT IF NOT EXISTS chk_avg_asking_rent_psf_yr_nnn 
CHECK (avg_asking_rent_psf_yr_nnn BETWEEN 5 AND 150);

-- Comparables validation (if v_comps_trimmed exists)
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'v_comps_trimmed') THEN
    ALTER TABLE v_comps_trimmed 
    ADD CONSTRAINT IF NOT EXISTS chk_price_per_sf_usd 
    CHECK (price_per_sf_usd BETWEEN 10 AND 1000);
    
    ALTER TABLE v_comps_trimmed 
    ADD CONSTRAINT IF NOT EXISTS chk_cap_rate_pct 
    CHECK (cap_rate_pct BETWEEN 1 AND 25);
    
    ALTER TABLE v_comps_trimmed 
    ADD CONSTRAINT IF NOT EXISTS chk_building_sf 
    CHECK (building_sf BETWEEN 1000 AND 10000000);
    
    ALTER TABLE v_comps_trimmed 
    ADD CONSTRAINT IF NOT EXISTS chk_occupancy_pct 
    CHECK (occupancy_pct BETWEEN 0 AND 100);
  END IF;
END $$;

-- =========================================================
-- RLS (Row Level Security) policies
-- =========================================================

-- Enable RLS on new tables
ALTER TABLE ingestion_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cache_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_requests ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role can do everything on ingestion_events"
  ON ingestion_events FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role can do everything on jobs"
  ON jobs FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role can do everything on cache_metrics"
  ON cache_metrics FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role can do everything on api_requests"
  ON api_requests FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Allow authenticated users read access to jobs (for status checking)
CREATE POLICY "Authenticated users can read their jobs"
  ON jobs FOR SELECT
  TO authenticated
  USING (tenant_id = 'default'); -- Adjust tenant logic as needed

-- =========================================================
-- Functions for metrics and health checks
-- =========================================================

-- Function to calculate cache hit ratios
CREATE OR REPLACE FUNCTION get_cache_hit_ratios(hours_back INTEGER DEFAULT 1)
RETURNS TABLE(data_source TEXT, hit_ratio DECIMAL)
LANGUAGE sql
STABLE
AS $$
  WITH cache_stats AS (
    SELECT 
      cm.data_source,
      COUNT(*) FILTER (WHERE cm.metric_type = 'hit') as hits,
      COUNT(*) FILTER (WHERE cm.metric_type = 'miss') as misses,
      COUNT(*) as total
    FROM cache_metrics cm
    WHERE cm.created_at > NOW() - INTERVAL '1 hour' * hours_back
    GROUP BY cm.data_source
  )
  SELECT 
    cs.data_source,
    CASE 
      WHEN cs.total = 0 THEN 0.0
      ELSE ROUND(cs.hits::DECIMAL / cs.total, 3)
    END as hit_ratio
  FROM cache_stats cs;
$$;

-- Function to get API performance metrics
CREATE OR REPLACE FUNCTION get_api_performance_metrics(hours_back INTEGER DEFAULT 1)
RETURNS TABLE(
  endpoint TEXT,
  avg_response_time_ms DECIMAL,
  p50_response_time_ms INTEGER,
  p95_response_time_ms INTEGER,
  total_requests BIGINT,
  error_rate DECIMAL
)
LANGUAGE sql
STABLE
AS $$
  WITH request_stats AS (
    SELECT 
      ar.endpoint,
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ar.response_time_ms) as p50,
      PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ar.response_time_ms) as p95,
      AVG(ar.response_time_ms) as avg_time,
      COUNT(*) as total,
      COUNT(*) FILTER (WHERE ar.status_code >= 400) as errors
    FROM api_requests ar
    WHERE ar.created_at > NOW() - INTERVAL '1 hour' * hours_back
    GROUP BY ar.endpoint
  )
  SELECT 
    rs.endpoint,
    ROUND(rs.avg_time, 1) as avg_response_time_ms,
    rs.p50::INTEGER as p50_response_time_ms,
    rs.p95::INTEGER as p95_response_time_ms,
    rs.total as total_requests,
    CASE 
      WHEN rs.total = 0 THEN 0.0
      ELSE ROUND(rs.errors::DECIMAL / rs.total, 3)
    END as error_rate
  FROM request_stats rs;
$$;

-- =========================================================
-- Sample data for testing
-- =========================================================

-- Insert a sample ingestion event
INSERT INTO ingestion_events (
  event_type, 
  payload, 
  payload_hash, 
  source, 
  status,
  processed_records,
  applied_at
) VALUES (
  'market.fundamentals.upsert',
  '{"market_slug": "dfw", "vacancy_rate_pct": 6.2, "avg_cap_rate_pct": 7.8}',
  encode(digest('sample_payload', 'sha256'), 'hex'),
  'manual_seed',
  'applied',
  1,
  NOW()
) ON CONFLICT (tenant_id, event_type, payload_hash) DO NOTHING;

-- Insert sample cache metrics
INSERT INTO cache_metrics (metric_type, cache_key, data_source, latency_ms)
VALUES 
  ('hit', 'macro_data', 'macro', 45),
  ('miss', 'fundamentals_dfw', 'fundamentals', 230),
  ('hit', 'comps_dfw_15', 'comps', 12);

-- =========================================================
-- Verification queries
-- =========================================================

-- Check table creation
SELECT 
  'Tables Created' as status,
  COUNT(*) as table_count
FROM information_schema.tables 
WHERE table_name IN ('ingestion_events', 'jobs', 'cache_metrics', 'api_requests');

-- Check constraints
SELECT 
  'Constraints Added' as status,
  COUNT(*) as constraint_count
FROM information_schema.table_constraints 
WHERE constraint_type = 'CHECK' 
  AND table_name IN ('market_fundamentals', 'v_comps_trimmed');

-- Sample metrics query
SELECT * FROM get_cache_hit_ratios(24);

-- Recent ingestion events
SELECT 
  event_type,
  status,
  processed_records,
  created_at,
  applied_at - created_at as processing_time
FROM ingestion_events 
ORDER BY created_at DESC 
LIMIT 5;
