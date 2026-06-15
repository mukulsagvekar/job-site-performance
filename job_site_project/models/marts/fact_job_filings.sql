{{
    config(
        materialized='incremental',
        unique_key='job_id',
        incremental_strategy='merge',
        on_schema_change='sync_all_columns'
    )
}}

select
    e.job_id,

    -- Foreign keys to dimensions (same hash formula as the dim tables,
    -- so they always match without needing a join here)
    {{ dbt_utils.generate_surrogate_key(['e.borough', 'e.block', 'e.lot', 'e.house_number', 'e.street_name', 'e.latitude', 'e.longitude']) }} as location_key,
    {{ dbt_utils.generate_surrogate_key(['e.job_type_code', 'e.building_type', 'e.existing_occupancy', 'e.proposed_occupancy']) }} as job_type_key,
    e.cost_bucket,
    e.job_status_code,

    -- Dates
    e.filing_date,
    e.latest_action_date,
    e.approval_date,

    -- Measures
    e.initial_cost,
    e.days_in_review,
    e.days_to_approval,

    -- Status flags
    e.is_active,
    e.is_approved,
    e.is_permit_issued,
    e.is_completed,
    e.is_disapproved,
    e.is_suspended,
    e.is_at_risk,
    e.stage_group,

    -- Tracking column for incremental filter
    e.load_timestamp

from {{ ref('enriched_job_filings') }} e

{% if is_incremental() %}
where e.load_timestamp > (select coalesce(max(load_timestamp), '1900-01-01') from {{ this }})
{% endif %}