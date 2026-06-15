-- models/semantic/sem_job_site_performance.sql
-- One row per job application, with all dimension attributes flattened in.
-- This view is what Cortex Analyst queries via the semantic model YAML,
-- and what the Streamlit dashboard charts/KPIs are built on.

{{
    config(materialized='table')
}}

select
    f.job_id,

    -- Dates
    f.filing_date,
    f.latest_action_date,
    f.approval_date,
    date_trunc('month', f.filing_date)  as filing_month,
    date_trunc('year',  f.filing_date)  as filing_year,

    -- Cost
    f.initial_cost,
    f.cost_bucket,

    -- Schedule KPIs
    f.days_in_review,
    f.days_to_approval,

    -- Status flags
    f.job_status_code,
    js.status_description,
    f.stage_group,
    f.is_active,
    f.is_approved,
    f.is_permit_issued,
    f.is_completed,
    f.is_disapproved,
    f.is_suspended,
    f.is_at_risk,

    -- Location
    l.borough,
    --l.community_board,
    l.latitude,
    l.longitude,

    -- Job type / building
    jt.job_type_code,
    jt.job_type_description,
    jt.building_type,
    jt.existing_occupancy,
    jt.proposed_occupancy

from {{ ref('fact_job_filings') }} f
left join {{ ref('dim_location') }}   l  on f.location_key  = l.location_key
left join {{ ref('dim_job_type') }}   jt on f.job_type_key   = jt.job_type_key
left join {{ ref('dim_job_status') }} js on f.job_status_code = js.status_code