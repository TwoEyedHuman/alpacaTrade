# Alpaca Trade
This project has two main purposes:
- Implement an automated trading strategy that can run with zero human intervention and
- Track and store intermittent price and market information.

# Motivation
This project was inspired by Ernest Chang's book *Quantiative Trading*. In the book, the Interactive Broker API was used but due to their API requiring a local installation of their Trader Workstation, I opted for using Alpaca's REST API.

# Getting Started
To get started, first copy this repository and ensure you have the proper requirements setup (see `requirements.txt`). Then, to launch simply run the command `python3 trade.py`. I recommend utilizing a virtual environment to avoid dependency issues.

# Strategies
Below are several strategies that are either currently completed or in progress.

## S&P 500 Dip (Mean Reversion)
The universe of stocks considered in this strategy are those in the S&P 500 (at time of project creation). Every market open the average of the close of the previous 50 trading days is compared to the current price. The 5 stocks with the largest drop are assigned as the current position and the protfolio (for this strategy) is updated to reflect this.
