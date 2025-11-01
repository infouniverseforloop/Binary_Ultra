# smc_ict.py
import pandas as pd

class SMC_ICT:
    def analyze(self, candles):
        # candles: list of dicts with open,high,low,close,volume
        if not candles or len(candles) < 5:
            return []
        df = pd.DataFrame(candles)
        results = []
        last = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]
        # CHoCH heuristic
        if last['close'] > prev['high'] and prev2['close'] < prev2['open']:
            results.append({"type":"CALL","reason":"CHoCH Bullish"})
        if last['close'] < prev['low'] and prev2['close'] > prev2['open']:
            results.append({"type":"PUT","reason":"CHoCH Bearish"})
        # Order block placeholder: last opposite bearish candle before CHoCH
        return results
