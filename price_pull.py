# Brandon Locke
# This script loops throughout the trading day pulling the current
# prices for stocks in a separate file. The prices are loaded into
# a postgres database.


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

def getPriceSK(cur, conn, cnt=1):
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
    

def connect():
    # connect to the database and build a cursor and connection

    # build the connection and cursor objects
    conn = psql.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    return cur, conn


def pushPrice(cur, conn, price_sk, symb, price, ask, bid, cum_day_vol):
    # push the price to the database
    # cur : cursor
    # conn : connection to database
    # price_sk : surrogate key to indicate price at time
    # symb : ticker symbol of the stock
    # price : current quote price
    # ask: current ask price
    # bid : current bid price
    # cum_day_vol : cumulative volume of the days trades

    # build the parametrized query
    sqlStrParam = """
        insert into prices values (%s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s);
    """
    
    # repalce the entries in the parametrices query and send to database
    if ask == "N/A":
        ask = None
    if bid == "N/A":
        bid = None
    cur.execute(sqlStrParam, (price_sk, symb, price, ask, bid, cum_day_vol))

    # save changes
    conn.commit()


def is_time_between(begin_time, end_time, check_time=None):
    # checks if the check_time is between two times
    # begin_time : starting period of time check
    # end_time : ending period of time check
    # check_time : time that we are checking

    # if check time is not given, default to current time
    check_time = check_time or dt.datetime.now()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else: # crosses midnight
        return check_time >= begin_time or check_time <= end_time

def loadTickers(fname):
    # loads ticker symbols from file
    # fname : filename containing ticker symbols

    with open(fname, 'r') as f:
        tickerList = [line.rstrip() for line in f.readlines()]
        return tickerList


def queryPrices(symbs, cur, conn):
    # query the prices from api and push to database
    # symbs : list of ticker symbols
    # cur : cursor
    # conn : connection

    symb_cnt = len(symbs)
    new_sks = getPriceSK(cur, conn, symb_cnt)  # pull list of fresh SKs

    for indx, tickerSymb in enumerate(symbs):
        ticker = tickerSymb.rstrip().replace('.', '-')

        try:
            qt = si.get_quote_table(ticker)
            if qt is not None:
                pushPrice(cur,  # cursor
                          conn,  # connection
                          int(new_sks[indx]),  # new price SK
                          ticker,  # ticker symbol
                          str(qt["Quote Price"]).replace(',',''),  # quote price
                          str(qt["Ask"]).replace(',','').split(' ', 1)[0],  # ask price
                          str(qt["Bid"]).replace(',','').split(' ', 1)[0],  # bid price
                          qt["Volume"])  # cumulative day volume

        except:
            print("[error] Cannot pull quote table for %s." % ticker)


def main():
    cur, conn = connect()  # connect to the database

    symbs = loadTickers(sys.argv[1])

    symbCount = len(symbs)

    # load ticker symbols from file
    cur_time = dt.datetime.now().time()
    while True:
        if is_time_between(MARKET_OPEN, MARKET_CLOSE, dt.datetime.now().time()):
            queryPrices(symbs, cur, conn)
            time.sleep(CYCLE_WAIT_SEC)
                

if __name__ == "__main__":
    main()
