select
    job_s1_no as job_id,
    job_no as jon_number,
    job_type as job_type_code,
    job_status as job_status_code,
    job_status_descrp as job_status,
    borough as borough,
    house_no as house_number,
    street_name as street_name,
    block as block,
    lot as lot,
    latitude::float as latitude,
    longitude::float as longitude,
    try_to_date(pre_filing_date, 'MM/DD/YYYY') as filing_date,
    try_to_date(latest_action_date, 'MM/DD/YYYY') as latest_action_date,
    try_to_date(approved, 'MM/DD/YYYY') as approval_date,
    try_to_number(replace(initial_cost, '$', '')) as initial_cost,
    building_type as building_type,
    existing_occupancy as existing_occupancy,
    proposed_occupancy as proposed_occupancy,
    dobrundate as dob_run_date,
    load_timestamp as load_timestamp,
    current_timestamp as update_timestamp
from {{ source('raw', 'job_filings') }}

{% if is_incremental() %}
    where load_timestamp > (select max(load_timestamp) from {{ this }}) and job_id is not null
{% endif %}