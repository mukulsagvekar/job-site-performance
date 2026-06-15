{{
    config(
        materialized='incremental',
        unique_key='location_key',
        incremental_strategy='merge'
    )
}}

select
    {{ dbt_utils.generate_surrogate_key(['borough', 'block', 'lot', 'house_number', 'street_name', 'latitude', 'longitude']) }} as location_key,
    borough,
    block,
    lot,
    house_number,
    street_name,
    latitude,
    longitude,
    max(load_timestamp) as load_timestamp,
    current_timestamp as update_timestamp

from {{ ref('enriched_job_filings') }} 

{% if is_incremental() %}
    having max(load_timestamp) > (select coalesce(max(load_timestamp), '1900-01-01') from {{ this }}) and borough is not null
{% endif %}

group by 1,2,3,4,5,6,7,8