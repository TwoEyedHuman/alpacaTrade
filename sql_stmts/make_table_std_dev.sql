--drop table if exists std_dev_strat;
create table std_dev_strat (
    strat_sk serial primary key,
    stk varchar(5),
    qty integer,
    active boolean
);

insert into std_dev_strat (stk, qty, active) values ('AAPL', 0, false);
