select
    reps.rep_id                                     as commercial_id,
    reps.first_name || ' ' || reps.last_name        as commercial,
    reps.branch_id                                  as agence_id,
    branches.branch_name                            as agence,
    reps.hired_on                                   as date_embauche
from {{ ref('silver_sales_reps') }} as reps
inner join {{ ref('silver_branches') }} as branches
    on reps.branch_id = branches.branch_id
