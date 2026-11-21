-- The generator writes the exact number of defects it injected
-- (seeds/anomaly_manifest.csv). Silver must catch every one of them, and
-- nothing else: any difference, in either direction, fails the build.
with detected as (
    select anomaly_type, count(*) as detected_count
    from {{ ref('silver_quarantine') }}
    group by anomaly_type
),

expected as (
    select anomaly_type, expected_count
    from {{ ref('anomaly_manifest') }}
)

select
    coalesce(expected.anomaly_type, detected.anomaly_type) as anomaly_type,
    expected.expected_count,
    detected.detected_count
from expected
full outer join detected
    on expected.anomaly_type = detected.anomaly_type
where coalesce(expected.expected_count, -1) <> coalesce(detected.detected_count, -1)
