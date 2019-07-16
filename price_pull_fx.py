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

MARKET_OPEN = dt.time(14,30)
MARKET_CLOSE = dt.time(21,00)
CYCLE_WAIT_SEC = 60*5
DATABASE_URL = os.environ['HEROKU_POSTGRESQL_BLACK_URL']


def connect():
    # connect to the database and build a cursor and connection

    # build the connection and cursor objects
    conn = psql.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    return cur, conn


def load_alpaca():
    # load the connection to the alpaca web api
    api = tradeapi.REST(key_id =  os.environ['ALPACA_PUB_KEY'], secret_key =  os.environ['ALPACA_PRI_KEY'], base_url = "https://paper-api.alpaca.markets")
    return api


def load_tickers(fname):
    # loads ticker symbols from file
    # fname : filename containing ticker symbols

    with open(fname, 'r') as f:
        tickerList = [line.rstrip() for line in f.readlines()]
        return tickerList


def get_price_sks(cur, conn, cnt=1):
    # pulls a new surrogate key for the price entry
    # cur : cursor
    # conn : connection to database
    # cnt : number of fresh SKs needed

    # pull the last SK
    sqlStr = "select max(price_sk) from prices;"
    cur.execute(sqlStr)
    max_sk = cur.fetchall()[0]

    # format the last SK correctly in case table is empty
    if max_sk[0] is None:
            max_sk = 0
    else:
        max_sk = max_sk[0]

    # build an array with all fresh SKs
    ret_arr = np.arange(max_sk+1, max_sk + cnt + 2, 1)

    return ret_arr


def update_prices(api, cur, conn, symbs):
    # pull the current prices and update in the database
    # api : alapca web api
    # cur : database cursor
    # conn : database connection
    # symbs: set of symbols to pull

    # pull in price information
    barset = None
    barset = api.get_barset(symbs[0:200], 'minute', limit=1)
    for indx in range(1,int(len(symbs)/200)+1):
        sub_symbs = symbs[indx:indx*200]
        barset.update(api.get_barset(sub_symbs, 'minute', limit=1))

    sqlStrParam = "insert into prices (price_sk, symb, ts, open, high, low, close, vol) values (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s)"
    new_sks = get_price_sks(cur, conn, len(symbs))
    
    # for each symbol, push price info to database
    for indx, sym in enumerate(barset):
        cur.execute(sqlStrParam, new_sks[indx], sym, barset[sym][0].o, barset[sym][0].h, barset[sym][0].l, barset[sym][0].c, barset[sym][0].v)  # push row to database

    cur.commit()  # save changes to database


def print_msg(clock, msg):
    print("[Server: %s] [Market: %s] %s" % (dt.datetime.now().strftime("%Y%m%d %H:%M:%S"), clock.timestamp.strftime("%Y%m%d %H:%M:%S"), msg))

