select
    calendar_date                                           as date,
    cast(extract(year from calendar_date) as integer)       as annee,
    cast(extract(quarter from calendar_date) as integer)    as trimestre,
    cast(extract(month from calendar_date) as integer)      as mois,
    {{ dbt.date_trunc('month', 'calendar_date') }}          as debut_mois,
    iso_day_of_week                                         as jour_semaine_iso,
    is_holiday                                              as est_ferie,
    is_business_day                                         as est_jour_ouvre
from {{ ref('silver_calendar') }}
