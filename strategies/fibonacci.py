# fibonacci.py
class Fibonacci:
    def analyze(self, candles):
        if not candles or len(candles) < 6:
            return []
        slice_ = candles[-10:] if len(candles)>=10 else candles
        highs = [c['high'] for c in slice_]
        lows = [c['low'] for c in slice_]
        high = max(highs); low = min(lows)
        if high==low:
            return []
        last = candles[-1]['close']
        rel = (last - low)/(high - low)
        res = []
        for lvl in [0.382,0.5,0.618]:
            if abs(rel - lvl) < 0.02:
                res.append({"type":"CALL" if last<high else "PUT","reason":f"Fib{lvl}"})
        return res
