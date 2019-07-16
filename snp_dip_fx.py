import price_pull_fx as ppfx
import alpaca_trade_api as tradeapi
import psycopg2 as psql
from yahoo_fin import stock_info as si
import psycopg2 as psql
import datetime as dt
import numpy as np
import time
import sys
import os
from price_pull_fx import connect, load_alpaca
import pandas as pd
import string
import random

def generate_order_id():
    # generate a random order ID

    chars = string.ascii_letters + string.digits
    new_id = ''.join(random.choice(chars) for i in range(16))

    return new_id


def load_tickers(filename):
    # load the ticker symbols from the given file
    # filename : name of the given file

    with open(filename, "r") as f:
        syms = f.read().split("\n")

    return syms


def get_prices(api, syms, days=50):
    # load the prices for some days for a set of symbols
    # api : connection to the alpaca web api
    # syms : set of symbols to consider
    # days : number of days back to calculate

    now = dt.datetime.utcnow()
    end_dt = now

    # if the market has already opened, get the most recent price today
    if now.time() >= dt.time(14,30):
        end_dt  = now - dt.timedelta(minutes=1)

    start_dt = end_dt - dt.timedelta(days=days)

    start = start_dt.strftime("%Y-%m-%d")
    end = end_dt.strftime("%Y-%m-%d")

    barset = api.get_barset(syms[0:200], "day", limit=days, start=start, end=end)  # initial pull of first 200 symbols

    idx = 200
    while idx <= len(syms)-1:
        barset.update(api.get_barset(syms[idx:idx+200], "day", limit=days, start=start, end=end))  # update set with next 200 symbols
        idx += 200

    return barset.df  # return a pandas dataframe with elements
        

def calc_scores(api, price_df):
    # calculate the scores for all of the symbols we are considering
    # api : connection to the alpaca web api
    # price_df : dataframe containing prices for the set of symbols

    # build dictionary, mapping tickers to pd df with prices
    scores = {}

    for sym in price_df.columns.levels[0]:
        spec_df = price_df[sym]
        if len(spec_df.close.values) > 10:
            ewma= spec_df.close.ewm(span=10).mean()[-1]  # calculate the exponentially weighted moving average for each stock
            last = spec_df.close.values[-1]  # the latest price for the stock
            diff = (last - ewma)/last  # score, the normalized relation between weighted mean and current price
            scores[sym] = diff
            
    scores = sorted(scores.items(), key = lambda x: x[1])  # sort the scores from best (to buy) and worst

    return scores
        

def get_current_position(api, cur, conn):
    # get active positions in alpaca and db, return df of [strat_sk, symb, qty]
    # api: connection to the alpaca web api
    # cur : cursor for database
    # conn : connection to the database

    # build a dataframe of positions currently held on Alpaca
    positions = api.list_positions()
    api_pos = pd.DataFrame([(pos.symbol, pos.qty) for pos in positions], columns=["stk", "qty"])

    # build dataframe of positions currently held according to this strategy on DB
    with open("sql_stmts/active_snp_dip.sql", "r") as f:
        sqlStr = f.read()

    cur.execute(sqlStr)

    db_pos = pd.DataFrame(cur.fetchall())
    if len(db_pos.columns) == 3:
        db_pos.columns = ["strat_sk", "stk", "qty"]

        df = pd.merge(db_pos, api_pos, on="stk", how="inner", suffixes=("_db", "_api"))

        df["qty"] = df[["qty_db", "qty_api"]].min(axis=1)

        # deactivate all positions that do not exist anymore in alpaca
        sqlStrParam = "update snp_dip set active = false, exit_date = CURRENT_TIMESTAMP where strat_sk not in (%s)" 
        cur.execute(sqlStrParam, ",".join([str(x) for x in df["strat_sk"]]))
        conn.commit()
        df["strat_sk"] = int(df["strat_sk"])

        return df[["strat_sk", "stk", "qty"]]

    else:
        return pd.DataFrame(columns=["strat_sk", "stk", "qty"])


def update_positions(api, cur, conn, price_df, scores, position_size = 100, max_positions= 5):
    # update account holdings to reflect the current strategy
    # api : connection to the alpaca web api
    # cur : database cursor
    # conn : connection to the database
    # scores : the score values for each symbol
    # position_size : the amount we want to invest in each position
    # max_positions : the number of positions we want to hold

    # pull in account information and what stocks we want to hold
    holdings = get_current_position(api, cur, conn)
    
    holdings_syms = set(holdings["stk"])

    # create set of the best stocks to buy (top twentieth)
    to_buy = set([sym for sym, _ in scores[:len(scores)//20]])
    to_sell = holdings_syms - to_buy   # exit out of positions that we currently hold but do not want
    to_buy = to_buy - holdings_syms  # buy positions that we do not currently hold

    # build list of orders based on updates needed
    orders = []

    # for each position to sell, create an order-sell object and update DB to reflect the position closing
    for sym in to_sell:
        shares = holdings[holdings["stk"] == sym]["qty"]
        orders.append({"symbol": sym, "qty": shares, "side": "sell"})
        sqlStrParam = "update snp_dip set active = false where strat_sk = %s"
        upd_sk = int(holdings[holdings["stk"] == sym]["strat_sk"].values[0])
        cur.execute(sqlStrParam, str(upd_sk))
        conn.commit()

    max_to_buy = max_positions - (len(holdings) - len(to_sell))  # determine the number of positions to enter into

    # for each position to buy, create an order-buy object
    for sym in to_buy:
        if max_to_buy <= 0:
            break
        shares = position_size // float(price_df[sym].close.values[-1])
        if shares == 0:
            continue
        orders.append({"symbol": sym, "qty": shares, "side": "buy"})
        max_to_buy -= 1

    return orders


def add_buy(cur, conn, stk, qty):
    # push to database the new buy action

    sqlStr = "select max(strat_sk) from snp_dip"
    cur.execute(sqlStr)
    new_sk = cur.fetchone()[0] + 1

    sqlStrParam = "insert into snp_dip (strat_sk, stk, qty) values (%s, %s, %s)"
    cur.execute(sqlStrParam, (new_sk, stk, qty))

    conn.commit()


def process_orders(api, cur, conn, orders, wait=30):
    # proces the orders built, waiting between sellign and buying
    # api : connection to alpaca web api
    # orders : set of orders to submit
    # wait : maximum time to wait between selling and buying

    # sell positions
    sells = [o for o in orders if o["side"] == "sell"]
    for order in sells:
        try:
            order_id = generate_order_id()
            api.submit_order(symbol = order["symbol"], qty = order["qty"], side = "sell", type = "market", time_in_force = "day", client_order_id = order_id)
        except Exception as e:
            print("Error in process orders: %s" % e)

    count = wait

    while count > 0:
        pending = api.list_orders()
        if len(pending) == 0:
            break
        time.sleep(1)
        count -= 1

    # buy positions
    buys = [o for o in orders if o["side"] == "buy"]
    for order in buys:
        try:
            order_id = generate_order_id()
            api.submit_order(symbol = order["symbol"], qty = order["qty"], side = "buy", type = "market", time_in_force = "day", client_order_id = order_id)
            add_buy(cur, conn, order["symbol"], order["qty"])
        except Exception as e:
            print("Error in process orders: %s" % e)
            print(traceback.format_exc())

    count = wait
    while count > 0:
        pending = api.list_orders()
        if len(pending) == 0:
            break
        time.sleep(1)
        count -= 1
    

def snp_dip_strat(api, cur, conn):
    # execute snp drop strategy


    get_current_position(api, cur, conn)
    # build list of tickers
    syms = load_tickers("tick_sym.txt")


    # build prices
    price_df = get_prices(api, syms, 50)  # build a dataframe with historical prices

    # determine stocks with lowest scores
    scores = calc_scores(api, price_df)

    # build buy and sell conditions based on current position
    orders = update_positions(api, cur, conn, price_df, scores)

    # submit orders
    process_orders(api, cur, conn, orders, 30)
