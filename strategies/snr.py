# snr.py
class SNR:
    def analyze(self, candles, price):
        if price is None:
            return []
        frac = price - int(price)
        res = []
        if abs(frac) < 0.0007:
            res.append({"type":"CALL","reason":"RoundNumber/SNR"})
        if abs(frac - 0.5) < 0.0007:
            res.append({"type":"PUT","reason":"RoundNumber/SNR"})
        return res
