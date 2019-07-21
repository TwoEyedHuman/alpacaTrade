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
    # create indicators to indicate if a strategy was already run "today"
    market_open_done = None
    market_mid_msg_done = None
    market_end_done = None

    # load the universe of tickers
    tick_syms = ppfx.load_tickers("tick_sym.txt")
    
    api = ppfx.load_alpaca()  # connect to the alpaca API
    clock = api.get_clock()  # build a market clock

    cur, conn = ppfx.connect()  # connect to the database

    # run program launch strategy

    while True:  # continuously run until end or server error
        now = clock.timestamp

        # run strategies that start or are triggered when the market opens
        if clock.is_open and market_open_done != clock.timestamp.strftime("%Y-%m-%d"):
            ppfx.print_msg(clock, "Running market open strategies.")
            # run opening market strategy
            market_open_strats(api, cur, conn)

            market_open_done = now.strftime('%Y-%m-%d')

        # continuously run strategies that will run while the market is open
        while clock.is_open and market_open_done == clock.timestamp.strftime("%Y-%m-%d"):
            if market_mid_msg_done != clock.timestamp.strftime("%Y-%m%-d"):
                ppfx.print_msg(clock, "Run mid market strategies and updating prices.")
                market_mid_msg_done = now.strftime("%Y-%m-%d")

            # run middle of market strategy
            market_middle_strats(api, cur, conn)

            # update database
            ppfx.update_prices(api, cur, conn, tick_syms)
            

            time.sleep(600)  # wait to avoid access revoked from API

        # run stategies that trigger after the market closes
        if not clock.is_open and market_end_done != clock.timestamp.strftime("%Y-%m-%d"):
            ppfx.print_msg(clock, "Running after market strategies")
            # run outside of market strategy
            market_close_strats(api, cur, conn)
            market_end_done = now.strftime("%Y-%m-%d")
