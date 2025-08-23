-- CapSight Production Schema with UUID PKs, constraints, indexes, and secure views
-- Deploy this in Supabase SQL Editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Markets table
CREATE TABLE IF NOT EXISTS markets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market fundamentals with constraints
CREATE TABLE IF NOT EXISTS market_fundamentals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  market_id UUID REFERENCES markets(id) ON DELETE CASCADE,
  market_slug TEXT NOT NULL,
  as_of_date DATE NOT NULL,
  vacancy_rate_pct FLOAT CHECK (vacancy_rate_pct >= 0 AND vacancy_rate_pct <= 50),
  avg_asking_rent_psf_yr_nnn FLOAT CHECK (avg_asking_rent_psf_yr_nnn >= 1 AND avg_asking_rent_psf_yr_nnn <= 50),
  yoy_rent_growth_pct FLOAT CHECK (yoy_rent_growth_pct >= -50 AND yoy_rent_growth_pct <= 50),
  new_supply_sf_ytd INT CHECK (new_supply_sf_ytd >= 0),
  under_construction_sf INT CHECK (under_construction_sf >= 0),
  net_absorption_sf_ytd INT CHECK (abs(net_absorption_sf_ytd) <= 1000000000),
  cap_rate_stabilized_median_pct FLOAT CHECK (cap_rate_stabilized_median_pct IS NULL OR (cap_rate_stabilized_median_pct >= 2 AND cap_rate_stabilized_median_pct <= 15)),
  source_name TEXT NOT NULL,
  source_url TEXT,
  source_date DATE,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(market_slug, as_of_date)
);

-- Industrial sales with comprehensive constraints
CREATE TABLE IF NOT EXISTS industrial_sales (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sale_id TEXT UNIQUE NOT NULL,
  market_id UUID REFERENCES markets(id) ON DELETE CASCADE,
  market_slug TEXT NOT NULL,
  address TEXT NOT NULL,
  city TEXT NOT NULL,
  state TEXT NOT NULL,
  zip TEXT NOT NULL,
  county TEXT NOT NULL,
  submarket TEXT NOT NULL,
  sale_date DATE NOT NULL,
  price_total_usd BIGINT CHECK (price_total_usd > 0),
  building_sf INT CHECK (building_sf > 0),
  land_acres FLOAT CHECK (land_acres IS NULL OR land_acres > 0),
  cap_rate_pct FLOAT CHECK (cap_rate_pct IS NULL OR (cap_rate_pct >= 2 AND cap_rate_pct <= 15)),
  price_per_sf_usd FLOAT CHECK (price_per_sf_usd IS NULL OR price_per_sf_usd > 0),
  noi_annual BIGINT CHECK (noi_annual IS NULL OR noi_annual > 0),
  year_built INT CHECK (year_built IS NULL OR (year_built >= 1900 AND year_built <= EXTRACT(YEAR FROM CURRENT_DATE))),
  clear_height_ft FLOAT CHECK (clear_height_ft IS NULL OR clear_height_ft > 0),
  tenant_status TEXT CHECK (tenant_status IN ('leased','vacant','partial')),
  buyer TEXT,
  seller TEXT,
  brokerage TEXT,
  data_source_name TEXT NOT NULL,
  data_source_url TEXT,
  verification_status TEXT CHECK (verification_status IN ('unverified','verified','broker-confirmed')) DEFAULT 'unverified',
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluation metrics for accuracy tracking
CREATE TABLE IF NOT EXISTS eval_metrics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  metric_date DATE DEFAULT CURRENT_DATE,
  market_slug TEXT,
  mape FLOAT CHECK (mape >= 0),
  caprate_rmse_bps FLOAT CHECK (caprate_rmse_bps >= 0),
  interval_coverage FLOAT CHECK (interval_coverage >= 0 AND interval_coverage <= 1),
  n_comps INT CHECK (n_comps >= 0),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enhanced accuracy metrics table for per-market tracking with conformal prediction
CREATE TABLE IF NOT EXISTS accuracy_metrics (
  id BIGSERIAL PRIMARY KEY,
  market_slug TEXT NOT NULL,
  calc_date DATE NOT NULL DEFAULT CURRENT_DATE,
  n INT NOT NULL CHECK (n >= 0),
  mape NUMERIC NOT NULL CHECK (mape >= 0),
  rmse_bps NUMERIC NOT NULL CHECK (rmse_bps >= 0),
  coverage80 NUMERIC NOT NULL CHECK (coverage80 >= 0 AND coverage80 <= 1),
  ape_q80 NUMERIC NOT NULL CHECK (ape_q80 >= 0),
  method_version TEXT DEFAULT 'v1.0',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_market_calc_date UNIQUE(market_slug, calc_date)
);

-- Human-in-the-loop review queue for flagged comps
CREATE TABLE IF NOT EXISTS comp_review_queue (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sale_id TEXT NOT NULL REFERENCES comparable_sales(sale_id),
  flag_type TEXT NOT NULL CHECK (flag_type IN ('geofence', 'size_outlier', 'age_outlier', 'cap_outlier', 'manual_review')),
  flag_reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_fundamentals_market_date ON market_fundamentals(market_slug, as_of_date DESC);
CREATE INDEX IF NOT EXISTS idx_sales_market_date ON industrial_sales(market_slug, sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_sales_verification ON industrial_sales(verification_status, sale_date DESC);
CREATE INDEX IF NOT EXISTS idx_eval_metrics_date ON eval_metrics(metric_date DESC);

-- Insert pilot markets
INSERT INTO markets (slug, name) VALUES
  ('dfw', 'Dallas-Fort Worth'),
  ('ie', 'Inland Empire'),
  ('atl', 'Atlanta'),
  ('phx', 'Phoenix'),
  ('sav', 'Savannah')
ON CONFLICT (slug) DO NOTHING;

-- Update foreign key relationships
UPDATE market_fundamentals mf 
SET market_id = m.id
FROM markets m 
WHERE mf.market_slug = m.slug AND mf.market_id IS NULL;

UPDATE industrial_sales s 
SET market_id = m.id
FROM markets m 
WHERE s.market_slug = m.slug AND s.market_id IS NULL;

-- Secure views for frontend (anon key access)
CREATE OR REPLACE VIEW public.v_market_fundamentals_latest AS
SELECT 
  mf.market_slug,
  mf.as_of_date,
  mf.vacancy_rate_pct,
  mf.avg_asking_rent_psf_yr_nnn,
  mf.yoy_rent_growth_pct,
  mf.new_supply_sf_ytd,
  mf.under_construction_sf,
  mf.net_absorption_sf_ytd,
  mf.cap_rate_stabilized_median_pct,
  mf.source_name,
  mf.source_url,
  mf.source_date,
  mf.notes
FROM public.market_fundamentals mf
INNER JOIN (
  SELECT market_slug, MAX(as_of_date) AS max_date
  FROM public.market_fundamentals
  GROUP BY market_slug
) latest ON mf.market_slug = latest.market_slug AND mf.as_of_date = latest.max_date;

CREATE OR REPLACE VIEW public.v_verified_sales_18mo AS
SELECT 
  s.market_slug,
  s.address,
  s.city,
  s.state,
  s.zip,
  s.county,
  s.submarket,
  s.sale_date,
  s.price_total_usd,
  s.building_sf,
  s.land_acres,
  s.cap_rate_pct,
  s.price_per_sf_usd,
  s.noi_annual,
  s.year_built,
  s.clear_height_ft,
  s.tenant_status,
  s.buyer,
  s.seller,
  s.brokerage,
  s.data_source_name,
  s.data_source_url,
  s.notes
FROM public.industrial_sales s
WHERE s.verification_status IN ('verified', 'broker-confirmed')
  AND s.sale_date >= (CURRENT_DATE - INTERVAL '18 months')
  AND s.cap_rate_pct IS NOT NULL
  AND s.noi_annual IS NOT NULL;

-- Trimmed comps view with outlier removal per market
CREATE OR REPLACE VIEW public.v_comps_trimmed AS
SELECT c.*
FROM (
  SELECT s.*,
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY cap_rate_pct) OVER (PARTITION BY market_slug) AS cap_p05,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY cap_rate_pct) OVER (PARTITION BY market_slug) AS cap_p95,
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY price_per_sf_usd) OVER (PARTITION BY market_slug) AS psf_p05,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY price_per_sf_usd) OVER (PARTITION BY market_slug) AS psf_p95
  FROM public.v_verified_sales_18mo s
  WHERE s.cap_rate_pct BETWEEN 2.0 AND 15.0
    AND s.price_per_sf_usd > 0
) c
WHERE c.cap_rate_pct BETWEEN c.cap_p05 AND c.cap_p95
  AND c.price_per_sf_usd BETWEEN c.psf_p05 AND c.psf_p95;

-- Latest accuracy metrics per market
CREATE OR REPLACE VIEW public.latest_accuracy AS
SELECT DISTINCT ON (market_slug)
  market_slug,
  calc_date,
  n,
  mape,
  rmse_bps,
  coverage80,
  ape_q80,
  method_version
FROM public.accuracy_metrics
ORDER BY market_slug, calc_date DESC;

-- Enable Row Level Security
ALTER TABLE markets ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_fundamentals ENABLE ROW LEVEL SECURITY;
ALTER TABLE industrial_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_metrics ENABLE ROW LEVEL SECURITY;

-- RLS Policies for anon (read-only) access
CREATE POLICY "Public read markets" ON markets FOR SELECT USING (true);
CREATE POLICY "Public read fundamentals" ON market_fundamentals FOR SELECT USING (true);
CREATE POLICY "Public read verified sales" ON industrial_sales FOR SELECT USING (
  verification_status IN ('verified', 'broker-confirmed') 
  AND sale_date >= (CURRENT_DATE - INTERVAL '18 months')
);
CREATE POLICY "Public read eval metrics" ON eval_metrics FOR SELECT USING (true);

-- Grant view access to anon role
GRANT SELECT ON public.v_market_fundamentals_latest TO anon;
GRANT SELECT ON public.v_verified_sales_18mo TO anon;
GRANT SELECT ON public.markets TO anon;

-- Grant table access for service role (API writes)
GRANT ALL ON public.markets TO service_role;
GRANT ALL ON public.market_fundamentals TO service_role;
GRANT ALL ON public.industrial_sales TO service_role;
GRANT ALL ON public.eval_metrics TO service_role;

COMMENT ON VIEW v_market_fundamentals_latest IS 'Latest market fundamentals for each pilot market - anon accessible';
COMMENT ON VIEW v_verified_sales_18mo IS 'Verified comparable sales from last 18 months - anon accessible';
