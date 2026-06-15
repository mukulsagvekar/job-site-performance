-- models/marts/dim_job_status.sql
-- Surfaces the dob_job_status_codes seed as a clean dimension table.
-- Not incremental — static reference data maintained via the seed file.

{{
    config(materialized='table')
}}

select
    status_code,
    status_description,
    stage_group,
    is_active,
    is_approved,
    is_permit_issued,
    is_completed,
    is_disapproved,
    is_suspended
from {{ ref('job_status_codes') }}