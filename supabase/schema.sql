-- Canonical CapSight schema with UUID PKs, constraints, and indexes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE markets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL
);

CREATE TABLE market_fundamentals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  market UUID REFERENCES markets(id) ON DELETE CASCADE,
  as_of_date DATE NOT NULL,
  vacancy_rate_pct FLOAT CHECK (vacancy_rate_pct >= 0 AND vacancy_rate_pct <= 50),
  avg_asking_rent_psf_yr_nnn FLOAT CHECK (avg_asking_rent_psf_yr_nnn >= 1 AND avg_asking_rent_psf_yr_nnn <= 50),
  yoy_rent_growth_pct FLOAT CHECK (yoy_rent_growth_pct >= -50 AND yoy_rent_growth_pct <= 50),
  new_supply_sf_ytd INT CHECK (new_supply_sf_ytd >= 0),
  under_construction_sf INT CHECK (under_construction_sf >= 0),
  net_absorption_sf_ytd INT CHECK (abs(net_absorption_sf_ytd) <= 1000000000),
  cap_rate_stabilized_median_pct FLOAT CHECK (cap_rate_stabilized_median_pct IS NULL OR (cap_rate_stabilized_median_pct >= 2 AND cap_rate_stabilized_median_pct <= 15)),
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_date DATE,
  notes TEXT
);

CREATE TABLE industrial_sales (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sale_id TEXT UNIQUE NOT NULL,
  market UUID REFERENCES markets(id) ON DELETE CASCADE,
  address TEXT NOT NULL,
  city TEXT NOT NULL,
  state TEXT NOT NULL,
  zip TEXT NOT NULL,
  county TEXT NOT NULL,
  submarket TEXT NOT NULL,
  sale_date DATE NOT NULL,
  price_total_usd INT CHECK (price_total_usd > 0),
  building_sf INT CHECK (building_sf > 0),
  land_acres FLOAT,
  cap_rate_pct FLOAT CHECK (cap_rate_pct IS NULL OR (cap_rate_pct >= 2 AND cap_rate_pct <= 15)),
  price_per_sf_usd FLOAT,
  year_built INT,
  clear_height_ft FLOAT,
  tenant_status TEXT CHECK (tenant_status IN ('leased','vacant','partial')),
  buyer TEXT,
  seller TEXT,
  brokerage TEXT,
  data_source_name TEXT NOT NULL,
  data_source_url TEXT NOT NULL,
  verification_status TEXT CHECK (verification_status IN ('unverified','verified','broker-confirmed')),
  notes TEXT
);

CREATE TABLE eval_metrics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  metric_date DATE DEFAULT CURRENT_DATE,
  mape FLOAT,
  caprate_rmse_bps FLOAT,
  interval_coverage FLOAT,
  n INT
);

-- Indexes
CREATE INDEX idx_fundamentals_market_date ON market_fundamentals(market, as_of_date);
CREATE INDEX idx_sales_market_date ON industrial_sales(market, sale_date);
CREATE INDEX idx_eval_metrics_date ON eval_metrics(metric_date);

-- Market seed rows
INSERT INTO markets (slug, name) VALUES
  ('dfw', 'Dallas-Fort Worth'),
  ('ie', 'Inland Empire'),
  ('atl', 'Atlanta'),
  ('phx', 'Phoenix'),
  ('sav', 'Savannah')
ON CONFLICT (slug) DO NOTHING;

-- Add market_slug columns for easier joins/views
ALTER TABLE market_fundamentals ADD COLUMN IF NOT EXISTS market_slug TEXT;
ALTER TABLE industrial_sales ADD COLUMN IF NOT EXISTS market_slug TEXT;

-- Update market_slug from markets table
UPDATE market_fundamentals mf
SET market_slug = m.slug
FROM markets m
WHERE mf.market = m.id AND mf.market_slug IS NULL;

UPDATE industrial_sales s
SET market_slug = m.slug
FROM markets m
WHERE s.market = m.id AND s.market_slug IS NULL;

-- Add NOI column for evaluation metrics
ALTER TABLE industrial_sales ADD COLUMN IF NOT EXISTS noi_annual INT;

-- Create secure views for frontend (browser-safe)
CREATE OR REPLACE VIEW public.v_market_fundamentals_latest AS
SELECT mf.market_slug, mf.as_of_date, mf.vacancy_rate_pct, 
       mf.avg_asking_rent_psf_yr_nnn, mf.yoy_rent_growth_pct,
       mf.new_supply_sf_ytd, mf.under_construction_sf, 
       mf.net_absorption_sf_ytd, mf.cap_rate_stabilized_median_pct,
       mf.source_name, mf.source_date, mf.notes
FROM public.market_fundamentals mf
JOIN (
  SELECT market_slug, MAX(as_of_date) AS max_date
  FROM public.market_fundamentals
  WHERE market_slug IS NOT NULL
  GROUP BY market_slug
) x ON x.market_slug = mf.market_slug AND x.max_date = mf.as_of_date;

CREATE OR REPLACE VIEW public.v_verified_sales_18mo AS
SELECT s.market_slug, s.address, s.city, s.state, s.zip, s.county, 
       s.submarket, s.sale_date, s.price_total_usd, s.building_sf, 
       s.land_acres, s.cap_rate_pct, s.price_per_sf_usd, s.year_built, 
       s.clear_height_ft, s.tenant_status, s.buyer, s.seller, s.brokerage,
       s.data_source_name, s.notes, s.noi_annual
FROM public.industrial_sales s
WHERE s.verification_status IN ('verified','broker-confirmed')
  AND s.sale_date >= (CURRENT_DATE - INTERVAL '18 months')
  AND s.market_slug IS NOT NULL;

-- RLS policies for secure access
ALTER TABLE markets ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_fundamentals ENABLE ROW LEVEL SECURITY;
ALTER TABLE industrial_sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_metrics ENABLE ROW LEVEL SECURITY;

-- Allow public read access to markets table
CREATE POLICY "Public read access to markets" ON markets FOR SELECT USING (true);

-- Allow public read access to fundamentals via views
CREATE POLICY "Public read access to fundamentals" ON market_fundamentals 
FOR SELECT USING (true);

-- Allow public read access to verified sales via views
CREATE POLICY "Public read access to verified sales" ON industrial_sales 
FOR SELECT USING (verification_status IN ('verified','broker-confirmed') 
  AND sale_date >= (CURRENT_DATE - INTERVAL '18 months'));

-- Allow public read access to eval metrics
CREATE POLICY "Public read access to eval metrics" ON eval_metrics FOR SELECT USING (true);

-- Grant select permissions on views to anon role
GRANT SELECT ON public.v_market_fundamentals_latest TO anon;
GRANT SELECT ON public.v_verified_sales_18mo TO anon;
GRANT SELECT ON public.markets TO anon;
