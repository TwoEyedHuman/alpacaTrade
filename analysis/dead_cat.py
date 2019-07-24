import alpaca_trade_api as tradeapi
import numpy as np
import pandas as pd
import psycopg2 as psql
import os
import matplotlib.pyplot as plt

pd.options.mode.chained_assignment = None

DATABASE_URL = os.environ['HEROKU_POSTGRESQL_BLACK_URL']

def load_alpaca():
    # load the connection to the alpaca web api
    api = tradeapi.REST(key_id =  os.environ['ALPACA_PUB_KEY'], secret_key =  os.environ['ALPACA_PRI_KEY'], base_url = "https://paper-api.alpaca.markets")
    return api


def connect():
    # connect to the database and build a cursor and connection

    # build the connection and cursor objects
    conn = psql.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    
    return cur, conn


def dead_cat(api, df, day_drop=3, perc_inc = 0.1):
    df.loc[:,"day_n_drop"] = df.close.rolling(day_drop, day_drop).apply(lambda x: pd.Series(x).is_monotonic_decreasing, raw=False)
    df.loc[:,"ystrday_close_ind"] = df.day_n_drop.shift(periods=1)

    buy_price = None
    df.loc[:,"buy_price"] = np.nan
    df.loc[:,"buy_vol"] = np.nan
    for indx, row in df.iterrows():
        if buy_price == None and row.ystrday_close_ind == 1:
            df.loc[indx, "buy_price"] = row.high
            df.loc[indx, "buy_vol"] = 1
            buy_price = row.high
        elif (buy_price != None) and (row.low > buy_price*(1.0 + perc_inc)):
            df.loc[indx, "buy_price"] = -1*row.low
            df.loc[indx, "buy_vol"] = -1
            buy_price = None


    return -1*(df.buy_vol.sum())*df.close[-1] + df.buy_price.sum()

def main(day_drop=3, perc_inc = 0.1):
    api = load_alpaca()
    barset = api.get_barset("AMZN", "day", limit=500)
    df = barset.df["AMZN"]

    syms = ["FB","AMZN","AAPL","NFLX","GOOG"]
#    for sym in syms:
#        prof = dead_cat(api, sym)
#        print("[%s] $%0.2f" % (sym, prof))

    for sym in syms:
        arr = np.zeros(30)
        for i in range(1,30):
            arr[i] = dead_cat(api, df, 3, i/100.0)
        plt.plot(arr)
        plt.show()


if __name__ == "__main__":
    main()
