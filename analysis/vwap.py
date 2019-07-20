import alpaca_trade_api as tradeapi
import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd
import sys


def load_alpaca():
    # load the connection to the alpaca web api
    api = tradeapi.REST(key_id =  os.environ['ALPACA_PUB_KEY'], secret_key =  os.environ['ALPACA_PRI_KEY'], base_url = "https://paper-api.alpaca.markets")
    return api


def wave_overlay(x, harmonics=10):

    lin_trend = np.polyfit(np.arange(0, x.size), x, 1)
    x = x - lin_trend[0]*np.arange(0,x.size)

    waves = np.fft.fft(x)
    freqs = np.fft.fftfreq(len(x))
    res = np.zeros(len(x))

    indices = range(len(x))
#    indices.sort(key = lambda i: np.absolute(freqs[i]))
#    indices = indices[0:harmonics]

    for k in range(0, len(x)):
        val = 0.0
        for n in range(0, harmonics):
            val += waves[n] * np.exp(1.j * 2 * np.pi * n * k / len(waves)) / len(waves)
        res[k] = val.real

    return res + lin_trend[0]*np.arange(0, x.size)


if __name__ == "__main__":
    symb = sys.argv[1]
    api = load_alpaca()

    barset = api.get_barset(symb, "day", limit=150)

    df = barset.df[symb]
    df.volume = (df.volume - df.volume.min())/(df.volume.max() - df.volume.min())
    df.volume = 16 * df.volume
    df["ewma"] = df.ewm(com=0.95).mean().close


    pd.plotting.register_matplotlib_converters()

    plt.plot(df.index, wave_overlay(df.close, 30))
    plt.scatter(df.index, df.close, s = df.volume)
    plt.xlim(df.index.min(), df.index.max())
    plt.show()
