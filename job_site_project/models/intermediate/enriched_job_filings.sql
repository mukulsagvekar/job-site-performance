with jobs as (
    select * from {{ ref('stg_job_filings') }}
),

status_lookup as (
    select * from {{ ref('job_status_codes') }}
)

select
    j.job_id,
    j.job_type_code,
    j.job_status_code,
    j.borough,
    j.house_number,
    j.street_name,
    j.block,
    j.lot,
    j.latitude,
    j.longitude,
    j.filing_date,
    j.latest_action_date,
    j.approval_date,
    j.initial_cost,
    j.building_type,
    j.existing_occupancy,
    j.proposed_occupancy,

    -- Pull in status meaning from the lookup table
    s.status_description,
    s.stage_group,
    s.is_active,
    s.is_approved,
    s.is_permit_issued,
    s.is_completed,
    s.is_disapproved,
    s.is_suspended,

    -- Schedule KPIs
    datediff('day', j.filing_date, j.latest_action_date) as days_in_review,
    datediff('day', j.filing_date, j.approval_date) as days_to_approval,

    -- At-risk only applies to jobs still active in the pipeline
    case
        when s.is_active = true and datediff('day', j.filing_date, j.latest_action_date) > 180
        then true
        else false
    end as is_at_risk,

    -- Cost segmentation
    case
        when j.initial_cost < 100000 then '<100K'
        when j.initial_cost < 500000 then '100K-500K'
        when j.initial_cost < 2000000 then '500K-2M'
        else '2M+'
    end as cost_bucket,
    
    j.load_timestamp as load_timestamp,
    current_timestamp as update__timestamp

from jobs j
left join status_lookup s
    on j.job_status_code = s.status_code


{% if is_incremental() %}
    where load_timestamp > (select max(load_timestamp) from {{ this }}) and days_in_review >= 0 and days_to_approval >= 0
{% endif %}