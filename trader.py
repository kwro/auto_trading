from alpaca_trade_api.rest import REST, TimeFrame
from .scraper import scrape_yahoo
import numpy as np
import pandas as pd
import datetime as dt
from time import sleep
import logging
import os
from dotenv import load_dotenv

load_dotenv('/Users/katarzyna/Documents/Alpaca/auto_trading/.env')  # dlaczego działa tylko z pełną ścieżką? :(


class Trader:

    def __init__(self, symbol, sma_fast: int = 12, sma_slow: int = 24):
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
        self.symbol: str = symbol
        self.start: dt.datetime = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
        self.sma_fast: int = sma_fast
        self.sma_slow: int = sma_slow
        self.TimeFrame = TimeFrame
        try:
            self.api = REST(key_id=os.getenv('KEY_ID'),
                            secret_key=os.getenv('SECRET_KEY'),
                            base_url=os.getenv('BASE_URL'))
            logging.info("Connection established")
        except Exception as e:
            logging.info("No connection")
            return

        open_positions = self.get_positions()
        self.signal: str = 'buy' if self.symbol in open_positions.keys() else 'sell'

    def trade_stock(self):
        # check if market is open
        if self.time_to_market_close() <= 60:
            # if not, wait until open
            self.wait_for_market_open()
            logging.info("Waiting for market to open")
        else:
            logging.info("Market open, let's start")

        logging.info(f"Getting last {self.sma_slow} entires")
        historical_data = pd.DataFrame(columns=['price'])
        historical_data = self.collect_entries(historical_data)
        logging.info(f"Entries collected")

        while True:
            historical_data = self.add_entry(historical_data)
            for i, r in historical_data.iloc[-1:].iterrows():
                if (r['ma_fast'] < r['ma_slow']) & (self.signal in ['sell']):
                    purchase_price = r['price']
                    self.signal = 'buy'
                    # self.submit_purchase_order(value=100)
                    logging.info(f"{purchase_price} invested")
                elif (r['ma_fast'] > r['ma_slow']) & (self.signal in ['buy']):
                    if purchase_price < r['price']:
                        self.signal = 'sell'
                        # self.submit_sell_order(open_positions)
                        logging.info(f"{r['price']} returned")
            sleep(2)

    def trade_crypto(self):
        historical_data = pd.DataFrame()
        historical_data = self.get_historical_data_stock()
        assert historical_data.shape[0] >= self.sma_slow

        while True:
            for r in historical_data.iloc[-1]:
                if (r['ma_fast'] < r['ma_slow']) & (self.signal in ['sell']):
                    self.signal = 'buy'
                    buy = r['close']
                    self.submit_order(value=100)
                elif (r['ma_fast'] > r['ma_slow']) & (self.signal in ['buy']):
                    if buy < r['close']:
                        self.signal = 'sell'
                        self.api.cancel_all_orders()

    def time_to_market_close(self):
        clock = self.api.get_clock()
        return (clock.next_close - clock.timestamp).total_seconds()

    def wait_for_market_open(self):
        clock = self.api.get_clock()
        if not clock.is_open:
            time_to_open = (clock.next_open - clock.timestamp).total_seconds()
            sleep(round(time_to_open))

    def get_historical_data_crypto(self):
        bars = self.api.get_crypto_bars(self.symbol, self.TimeFrame.Minute, start=self.start, limit=100,
                                        exchanges=['CBSE']).df
        bars['ma_fast'] = bars['close'].rolling(self.sma_fast).mean()
        bars['ma_slow'] = bars['close'].rolling(self.sma_slow).mean()
        bars['signal'] = np.nan
        return bars

    def get_historical_data_stock(self):
        bars = self.api.get_bars(self.symbol, self.TimeFrame.Minute,
                                 start=self.start - dt.timedelta(minute=self.sma_slow), limit=100).df
        bars['ma_fast'] = bars['close'].rolling(self.sma_fast).mean()
        bars['ma_slow'] = bars['close'].rolling(self.sma_slow).mean()
        bars['signal'] = np.nan
        return bars

    def collect_entries(self, df):
        while df.shape[0] < self.sma_slow - 1:
            df = pd.concat([df, pd.DataFrame(scrape_yahoo(self.symbol))])
            sleep(2)
        return df

    def add_entry(self, df):
        df = pd.concat([df, pd.DataFrame(scrape_yahoo(self.symbol))])
        df['ma_fast'] = df['price'].rolling(self.sma_fast).mean()
        df['ma_slow'] = df['price'].rolling(self.sma_slow).mean()
        df['signal'] = np.nan
        return df

    def submit_purchase_order(self, value=None):
        self.api.submit_order(
            symbol=self.symbol,
            notional=self.api.get_account().cash if value == None else value,
            # notional value of 1.5 shares of SPY at $300
            side=self.signal,
            type='market',
            time_in_force='day',
        )

    def submit_sell_order(self, open_positions):
        self.api.submit_order(
            symbol=self.symbol,
            qty=open_positions[self.symbol],
            # notional value of 1.5 shares of SPY at $300
            side=self.signal,
            type='market',
            time_in_force='day',
        )

    def get_positions(self):
        positions_dict = self.api.list_positions()
        positions = {}
        for p in positions_dict:
            positions[p.symbol] = p.qty
        return positions

    def estimate_profit(self):

