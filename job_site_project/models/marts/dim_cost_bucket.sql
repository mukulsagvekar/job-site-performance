{{
    config(materialized='table')
}}

select * from (
    values
    ('<100K',     1, 0,        100000),
    ('100K-500K', 2, 100000,   500000),
    ('500K-2M',   3, 500000,   2000000),
    ('2M+',       4, 2000000,  null)
) as t(cost_bucket, sort_order, min_cost, max_cost)