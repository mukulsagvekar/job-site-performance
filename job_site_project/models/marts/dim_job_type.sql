{{
    config(
        materialized='incremental',
        unique_key='job_type_key',
        incremental_strategy='merge'
    )
}}

select
    {{ dbt_utils.generate_surrogate_key(['job_type_code', 'building_type', 'existing_occupancy', 'proposed_occupancy']) }} as job_type_key,
    job_type_code,
    case job_type_code
        when 'NB' then 'New Building'
        when 'A1' then 'Major Alteration'
        when 'A2' then 'Minor Alteration'
        when 'A3' then 'Minor Alteration'
        when 'DM' then 'Demolition'
        else 'Other'
    end as job_type_description,
    building_type,
    existing_occupancy,
    proposed_occupancy,
    max(load_timestamp) as load_timestamp,
    current_timestamp as update_timestamp

from {{ ref('enriched_job_filings') }} 

{% if is_incremental() %}
having max(load_timestamp) > (select coalesce(max(load_timestamp), '1900-01-01') from {{ this }}) and job_type_code is not null
{% endif %}

group by 1,2,3,4,5,6