import alpaca_trade_api as tradeapi
import numpy as np
import pandas as pd
import psycopg2 as psql
import os


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


def dead_cat(api, symb):
    barset = api.get_barset(symb, "day", limit=100)
    df = barset.df

    return df
