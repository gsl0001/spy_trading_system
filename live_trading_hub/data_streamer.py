import pandas as pd
import numpy as np
from ib_insync import *
import asyncio

class DataStreamer:
    def __init__(self, ib_client: IB):
        self.ib = ib_client
        self.symbol = "SPY"
        self.contract = Stock(self.symbol, "SMART", "USD")
        self.df = pd.DataFrame(columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        self.bars = None
        self.on_new_bar_callbacks = []
        
    async def request_data(self):
        # Qualify the contract
        await self.ib.qualifyContractsAsync(self.contract)
        print(f"[{self.symbol}] Contract qualified. Requesting historical data + live updates.")
        
        # Request recent 1-minute historical bars to prime indicators (e.g. 100 bars)
        self.bars = self.ib.reqHistoricalData(
            self.contract,
            endDateTime='',
            durationStr='1 D',
            barSizeSetting='1 min',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1,
            keepUpToDate=True # This returns a Live BarDataList
        )
        
        # Attach the callback for live updates
        self.bars.updateEvent += self._on_bar_update
        
        # Initial dataframe populate
        self._update_dataframe()

    def _update_dataframe(self):
        # Convert ib_insync bars to Pandas DataFrame
        data = [{'Date': bar.date, 'Open': bar.open, 'High': bar.high, 
                 'Low': bar.low, 'Close': bar.close, 'Volume': bar.volume} 
                for bar in self.bars]
        self.df = pd.DataFrame(data)
        if not self.df.empty:
            self.df.set_index('Date', inplace=True)
            self._compute_indicators()

    def _on_bar_update(self, bars, hasNewBar):
        if hasNewBar:
            # We only trigger the trading engine on the completion of a full 1-minute bar
            self._update_dataframe()
            for cb in self.on_new_bar_callbacks:
                cb(self.df)

    def _compute_indicators(self):
        """Calculate VWAP Proxy, Keltner Channels, BB, Sub-indicators lazily using numpy vectorization."""
        df = self.df
        
        # Typical Price for VWAP and CCI
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        
        # VWAP Proxy
        vol = df['Volume'].replace(0, 1)
        df['VWAP_Proxy'] = (tp * vol).rolling(window=20).sum() / vol.rolling(window=20).sum()
        df['VWAP_Proxy_Dist'] = (df['Close'] / df['VWAP_Proxy']) - 1.0
        
        # Bollinger Bands (20, 2)
        df['BB_Mid'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
        
        # True Range
        tr = pd.concat([
            df['High'] - df['Low'], 
            (df['High'] - df['Close'].shift(1)).abs(), 
            (df['Low'] - df['Close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(window=14).mean()
        
        # Keltner Channels (20, 1.5)
        df['KC_Upper'] = df['BB_Mid'] + (1.5 * df['ATR_14'])
        df['KC_Lower'] = df['BB_Mid'] - (1.5 * df['ATR_14'])
        
        # MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist_Dist'] = df['MACD'] - df['MACD_Signal']
        
        # Chaikin Money Flow (CMF) 20-period
        mfm = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']).replace(0, 1)
        df['CMF'] = (mfm * vol).rolling(20).sum() / vol.rolling(20).sum()
