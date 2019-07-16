/*drop table if exists dead_cat;

create table dead_cat (
    cat_sk integer primary key,
    stk varchar(5),
    x_date date,
    entry_price decimal(12,4),
    exit_price_est decimal(12,4),
    exit_price_act decimal(12,4),
    day_drop integer,
    perc_inc decimal(12,4),
    active boolean
);

insert into dead_cat values (1, 'NULL', '9999-12-31', 0, 0, 0, 0, 0, false);
*/

drop table if exists snp_dip;
create table snp_dip (
    strat_sk integer,
    stk varchar(5),
    enter_date date,
    exit_date date,
    enter_price decimal(12,4),
    exit_price decimal(12,4),
    enter_order_id varchar(16),
    exit_order_id varchar(16),
    qty integer,
    active boolean
)
;

insert into snp_dip values (1, null, '9999-12-31', '9999-12-31', 0, 0, 'djvuf83nggalfic8', '8485nfnfld9d84nd', 0, false);
insert into snp_dip values (2, 'AMD', '9999-12-31', '9999-12-31', 0, 0, '8fk3ndlsickmdhsq', NULL, 1, True);
