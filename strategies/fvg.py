# fvg.py
class FVG:
    def analyze(self, candles):
        if not candles or len(candles) < 3:
            return []
        a,b,c = candles[-3], candles[-2], candles[-1]
        res = []
        if a['close'] < b['low'] and b['close'] < c['open']:
            res.append({"type":"CALL","reason":"Bullish FVG"})
        if a['close'] > b['high'] and b['close'] > c['open']:
            res.append({"type":"PUT","reason":"Bearish FVG"})
        return res
