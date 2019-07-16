#from price_pull_fx import update_prices, load_tickers
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
import snp_dip_fx as sd


############################ CONSTANTS ############################
MARKET_OPEN = dt.time(14,30)  # UTC time for market open
MARKET_CLOSE = dt.time(21,00)  # UTC time for market close
DATABASE_URL = os.environ['HEROKU_POSTGRESQL_BLACK_URL']
###################################################################

def market_open_strats(api, cur, conn):
    # run strategies that use previous day historical
    # data to submit trades and strategies
    # api : alpaca web api
    # cur : database cursor
    # conn : database connection

    sd.snp_dip_strat(api, cur, conn)


def market_middle_strats(api, cur, conn):
    # run strategies that use real-time market data
    # api : alpaca web api
    # cur : database cursor
    # conn : database connection

    pass


def market_close_strats(api, cur, conn):
    # run strategies or make decisions after market hours
    # api : alpaca web api
    # cur : database cursor
    # conn : database connection

    pass


if __name__ == "__main__":
    market_open_done = None
    market_end_done = None
    tick_syms = ppfx.load_tickers("tick_sym.txt")
    
    api = ppfx.load_alpaca()
    clock = api.get_clock()

    cur, conn = ppfx.connect()

    # run program launch strategy

    while True:
        now = clock.timestamp
        if clock.is_open and market_open_done != clock.timestamp.strftime("%Y-%m-%d"):
            ppfx.print_msg(clock, "Running market open strategies.")
            # run opening market strategy
            market_open_strats(api, cur, conn)

            market_open_done = now.strftime('%Y-%m-%d')

        while clock.is_open and market_open_done == clock.timestamp.strftime("%Y-%m-%d"):
            ppfx.print_msg(clock, "Running middle of market day strategies.")
            # run middle of market strategy
            market_middle_strats(api, cur, conn)

            ppfx.print_msg(clock, "Updating prices in database.")
            # update database
            ppfx.update_prices(api, cur, conn, tick_syms)
            

            time.sleep(600)

        if not clock.is_open and market_end_done != clock.timestamp.strftime("%Y-%m-%d"):
            ppfx.print_msg(clock, "Running after market strategies")
            # run outside of market strategy
            market_close_strats(api, cur, conn)
            market_end_done = now.strftime("%Y-%m-%d")
