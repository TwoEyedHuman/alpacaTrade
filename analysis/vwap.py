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

    barset = api.get_barset(symb, "minute", limit=200)

    df = barset.df[symb]
    df.volume = (df.volume - df.volume.min())/(df.volume.max() - df.volume.min())
    df.volume = 16 * df.volume
    df["ewma"] = df.ewm(com=0.95).mean().close

    df["wave"] = np.nan
    df["wave"][75:df.shape[0]] = [wave_overlay(df.close[i:i+75], 5)[-1] for i in range(df.shape[0]-75)]

    df["action"] = 0
    df["profit"] = 0.0
    cur_pos = (None, None)
    for indx, row in df.iterrows():
        if cur_pos[0] == None and row.close < row.wave:
            df.loc[df.index == indx, "action"] = 1
            cur_pos = ("long", row.close)
        elif cur_pos[0] == "long" and (row.close > row.wave or row.close < cur_pos[1]*0.999):
            df.loc[df.index == indx, "action"] = -1
            df.loc[df.index == indx, "profit"] = row.close - cur_pos[1]
            cur_pos = (None, None)

    df.to_csv(symb + ".csv")


    pd.plotting.register_matplotlib_converters()

    plt.plot(df.index[75:df.shape[0]], [wave_overlay(df.close[i:i+75], 5)[-1] for i in range(df.shape[0]-75)])
    plt.plot(df.index, wave_overlay(df.close, 5))
    plt.scatter(df.index, df.close, c=df.action)
    plt.xlim(df.index.min(), df.index.max())
    plt.show()
