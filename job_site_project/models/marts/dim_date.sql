{{
    config(materialized='table')
}}

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2000-01-01' as date)",
        end_date="cast(dateadd(year, 1, current_date) as date)"
    ) }}
)

select
    date_day as date_key,
    date_day,
    year(date_day) as year,
    quarter(date_day) as quarter,
    month(date_day) as month,
    monthname(date_day) as month_name,
    day(date_day) as day_of_month,
    dayname(date_day) as day_name,
    dayofweek(date_day) in (0, 6) as is_weekend,
    date_trunc('month', date_day) as month_start_date,
    date_trunc('year', date_day)as year_start_date
from date_spine