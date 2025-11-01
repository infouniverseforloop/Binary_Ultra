# volume_momentum.py
class VolumeMomentum:
    def analyze(self, candles):
        if not candles or len(candles) < 5:
            return []
        vols = [c.get('volume',0) for c in candles[-5:]]
        avg = sum(vols)/len(vols) if vols else 0
        res = []
        if avg>0 and vols[-1] > avg*1.5:
            if candles[-1]['close'] > candles[-2]['close']:
                res.append({"type":"CALL","reason":"Volume spike bullish"})
            else:
                res.append({"type":"PUT","reason":"Volume spike bearish"})
        return res
