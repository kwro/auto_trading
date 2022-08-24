import requests
from bs4 import BeautifulSoup
import datetime as dt
import json

def scrape_yahoo(symbol: str):
    """
    Get actual stock price for given symbol
    :param symbol: stock symbol, for example "AAPL" for Apple
    :return: dictionary with current timestamp and price {"AAPL": {"2022-08-01 10:00": 170.03}}
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",

    }

    html = requests.get(f"https://finance.yahoo.com/quote/{symbol}", timeout=30, headers=headers)
    soup = BeautifulSoup(html.text, 'html.parser')
    value = soup.find('fin-streamer', {'class': "Fw(b) Fz(36px) Mb(-4px) D(ib)"})
    value_text = value.get_text()
    value_data = json.loads(value_text)
    # ticker_data = {"price": value_data, "timestamp": dt.datetime.now(dt.timezone.utc)}
    ticker_data = {"price": {dt.datetime.now(dt.timezone.utc): value_data}}
    return ticker_data



