-- The purpose of this script is to pull the top volatility
-- stocks on a given date

------------------------------- Inputs --------------------------------
-- 1 : date that we want to pull from
-- 2 : the number of volatile stocks we want to pull
-----------------------------------------------------------------------

select sl.symb
    ,sl.cov
from (
    select symb,  -- ticker symbol
        stddev_pop(price)/avg(price) as cov  -- coefficient of variation
    from prices
    --where date(ts) = %s  -- date we want to pull stock for
    where date(ts) = '2019-07-02'
    group by 1
) as sl
order by sl.cov desc
limit %s  -- number of stocks we want to pull
--limit 1

