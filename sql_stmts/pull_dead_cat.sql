-- this query pulls all active dead cat positions

select dc.stk
    ,dc.exit_price_est
from dead_cat as dc
where active = True
