from price_pull_fx import connect, load_alpaca
import pandas as pd
import numpy as np

def current_position(api, cur, conn):
    # determine what stocks we are currently holding for this strategy
    # api : alpaca api
    # cur : database cursor
    # conn : connection to database

    # pull the current strat positions from the db
    sqlStr = "select strat_sk, qty from std_dev_strat where active = false and stk = 'AAPL'"
    cur.execute(sqlStr)
    sk_qty_db = cur.fetchone()
    if sk_qty_db is not None:
        sk_db = sk_qty_db[0]
        qty_db = sk_qty_db[1]
    else:
        sk_db = -1
        qty_db = 0

    # pull the current positions on the server
    try:
        qty_apca = api.get_position("AAPL").qty
    except:
        print("Position does not exist in AAPL")
        qty_apca = 0

    # select the value that is the lowest and return
    qty = min(qty_db, qty_apca)

    return qty
   

def std_dev_strat(api, cur, conn):
    # execute the strategy of buying and selling outside of 1 std of mean

    # if market open for more than 60 minute run, else skip
    if not api.get_clock().is_open and False:
        return

    # get last 60 minutes of prices
    df = api.get_barset("AAPL", "minute", limit=60).df["AAPL"]
    last_close = df.close.values[-1]

    # calc mean, std
    mean = df.close.mean()
    std = df.close.std()

    # determine if we are currently holding a position
    qty = current_position(api, cur, conn)

    qty_to_buy = int(5000/last_close)
    # if last is lower than mean - std, buy until no money left
    if last_close < mean - std and qty_to_buy > 0 and False:
        api.submit_order(symbol="AAPL",
                         qty = qty_to_buy - qty,
                         side = "buy",
                         type="market",
                         time_in_force="day")

        if qty_db > 0:  # if the database has a strategy active for this stock but it is not enough
            sqlStrParam = "update std_dev_strat set qty = %s where strat_sk = %s"
            cur.execute(sqlStrParam, (qty_to_buy, sk_db))
            conn.commit()

        else:  # if qty_db is zero, then we need to create an entry for this stock
            sqlStrParam = "insert into std_dev_strat (stk, qty, active) values ('AAPL', %s, true)"
            cur.execute(sqlStrParam, (qty))
            conn.commit()
        

    # if last is higher than mean + std and position exists, sell
    elif last_close > mean + std and qty > 0 and False:
        api.submit_order(symbol="AAPL", qty = qty, side = "sell", type="market", time_in_force="day")
        sqlStrParam = "update std_dev_strat set active = false where strat_sk = %s"
        cur.execute(sqlStrParam, sk_db)
        conn.commit()
