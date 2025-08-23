export interface Market {
  slug: string;
  name: string;
}

export interface ValuationRequest {
  market_slug: string;
  noi_annual: number;
}

export interface ValuationResponse {
  cap_rate_mid: number;
  cap_rate_band_bps: number;
  value_low: number;
  value_mid: number;
  value_high: number;
  n: number;
}

export interface Fundamentals {
  market_slug: string;
  as_of_date: string;
  vacancy_rate_pct: number | null;
  avg_asking_rent_psf_yr_nnn: number | null;
  yoy_rent_growth_pct: number | null;
  under_construction_sf: number | null;
  net_absorption_sf_ytd: number | null;
  cap_rate_stabilized_median_pct: number | null;
  source_name: string;
  source_url: string | null;
  source_date: string | null;
}

export interface Comp {
  market_slug: string;
  sale_date: string;
  submarket: string;
  building_sf: number;
  price_per_sf_usd: number | null;
  cap_rate_pct: number | null;
  data_source_url: string | null;
}

export interface ApiError {
  error: string;
  message?: string;
}
