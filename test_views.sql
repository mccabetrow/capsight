-- Test both views with anon permissions
-- Run these in Supabase SQL Editor to confirm anon access

-- Test 1: Latest fundamentals view
SELECT count(*) as fundamentals_count FROM public.v_market_fundamentals_latest;
SELECT market_slug, as_of_date, vacancy_rate_pct FROM public.v_market_fundamentals_latest LIMIT 5;

-- Test 2: Verified sales view  
SELECT count(*) as verified_sales_count FROM public.v_verified_sales_18mo;
SELECT market_slug, sale_date, cap_rate_pct FROM public.v_verified_sales_18mo LIMIT 5;

-- Test 3: Check markets table
SELECT slug, name FROM public.markets;
