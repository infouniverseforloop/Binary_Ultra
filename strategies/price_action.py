# price_action.py
class PriceAction:
    def analyze(self, candles):
        if not candles or len(candles) < 3:
            return []
        last = candles[-1]; prev = candles[-2]
        body = abs(last['close'] - last['open'])
        wick = last['high'] - last['low']
        res = []
        if body>0 and wick > 3*body:
            res.append({"type":"CALL" if last['close']>last['open'] else "PUT","reason":"PinBar"})
        # engulfing
        if last['close'] > last['open'] and prev['close'] < prev['open'] and last['close']>prev['open']:
            res.append({"type":"CALL","reason":"BullishEngulf"})
        if last['close'] < last['open'] and prev['close'] > prev['open'] and last['close']<prev['open']:
            res.append({"type":"PUT","reason":"BearishEngulf"})
        return res
