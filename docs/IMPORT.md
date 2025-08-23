# CapSight CSV Import & Validation Guide

## 1. Prepare Your Data
- Use the provided templates in `/data/templates/`.
- Use market slugs: dfw, ie, atl, phx, sav.
- For fundamentals, set `as_of_date` as YYYY-MM-01 (DATE).
- For comps, ensure `tenant_status` ∈ {leased,vacant,partial} and `verification_status` ∈ {unverified,verified,broker-confirmed}.

## 2. Validate Your CSVs
- Place all your market CSVs in a folder.
- Run the validator:

```sh
python capsight_csv_validator.py /path/to/your/csv/folder
```
- Fix any issues reported in `validation_report.csv`.

## 3. Import to Supabase
- In Supabase Table Editor, open `market_fundamentals` and `industrial_sales`.
- Click Import data → select your CSV.
- Confirm column mapping. For `as_of_date`, if you get a date error, ensure the format is YYYY-MM-01.
- For market, use the UUID from the `markets` table (join on slug if needed).

## 4. Post-Import Sanity Checks
- Run these SQLs in Supabase:

```sql
-- Missing sources in fundamentals
select market, as_of_date from market_fundamentals
where (vacancy_rate_pct is not null or avg_asking_rent_psf_yr_nnn is not null)
  and (source_url is null or source_url = '');

-- Comps with price/SF mismatch > $0.50
select sale_id, price_total_usd, building_sf, price_per_sf_usd,
       round(price_total_usd/building_sf,2) as calc_ppsf
from industrial_sales
where abs((price_total_usd/building_sf) - price_per_sf_usd) > 0.5;

-- Duplicates by (address, sale_date)
select address, sale_date, count(*) 
from industrial_sales 
group by 1,2 having count(*) > 1;
```

## 5. Data Hygiene
- All numbers: no commas, %, or $.
- Dates: fundamentals YYYY-MM-01, comps YYYY-MM-DD.
- Market names: use slugs everywhere.
- Cap rates: store as 6.25 (not 0.0625).
- Only mark comps as verified with 2 independent sources.

## 6. Troubleshooting
- If you get a market UUID error, join your slug to the `markets` table and use the UUID.
- If you get a date error, check your format and re-export as needed.

---

**Always validate before importing.**
