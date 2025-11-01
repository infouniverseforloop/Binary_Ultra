# signal_generator.py
import time, math
from collections import defaultdict, deque
from strategies.smc_ict import SMC_ICT
from strategies.snr import SNR
from strategies.fvg import FVG
from strategies.fibonacci import Fibonacci
from strategies.volume_momentum import VolumeMomentum
from strategies.price_action import PriceAction

class SignalGenerator:
    def __init__(self, client, logger, config):
        self.client = client
        self.logger = logger
        self.cfg = config
        self.smc = SMC_ICT(); self.snr = SNR(); self.fvg = FVG(); self.fib = Fibonacci()
        self.vol = VolumeMomentum(); self.pa = PriceAction()
        self.pairs = []
        # flatten pairs list
        for k,v in self.cfg.get("pairs",{}).items():
            self.pairs += v
        self.primary_tf = self.cfg.get("primary_timeframe","1m")
        self.higher_tfs = self.cfg.get("higher_timeframes",["5m","15m"])
        self.hist_candles = int(self.cfg.get("historical_candles",100))
        self.confirmation_threshold = int(self.cfg.get("confirmation_threshold",3))
        self.conf_publish = int(self.cfg.get("confidence_publish_threshold",60))
        self.pre_seconds = int(self.cfg.get("pre_signal_seconds",3))
        self.pair_cooldown = int(self.cfg.get("pair_cooldown_seconds",90))
        self.expiry = int(self.cfg.get("expiry_seconds",60))
        self.max_trades_hour = int(self.cfg.get("max_trades_per_hour",12))
        self.hourly_queue = deque()
        self.last_signal_time = defaultdict(lambda:0)
        self.consec_losses = 0

    def generate_signals(self):
        # convenience wrapper if no argument: fetch live snapshot internally
        snapshot = self.client.get_live_snapshot(self.pairs, timeframe=self.primary_tf)
        return self._generate_from_snapshot(snapshot)

    def _generate_from_snapshot(self, snapshot):
        now = time.time()
        # prune hourly queue
        while self.hourly_queue and now - self.hourly_queue[0] > 3600:
            self.hourly_queue.popleft()
        if len(self.hourly_queue) >= self.max_trades_hour:
            self.logger.info("Hourly trade cap reached")
            return []

        signals = []
        for pair in self.pairs:
            data = snapshot.get(pair)
            if not data:
                continue
            # cooldown per pair
            if now - self.last_signal_time[pair] < self.pair_cooldown:
                continue
            # gather candles
            candles = data.get("candles", []) or self.client.get_historical(pair, timeframe=self.primary_tf, limit=self.hist_candles)
            # market health check: simple ATR threshold
            if len(candles) >= 10:
                atr = self._atr(candles[-30:])
                if self._atr_too_high(pair, atr):
                    self.logger.info(f"{pair} ATR high {atr} — skip")
                    continue
            # run strategies
            votes = []
            reasons = []
            for out in self.smc.analyze(candles):
                votes.append(out['type']); reasons.append(out['reason'])
            for out in self.snr.analyze(candles, data.get("price")):
                votes.append(out['type']); reasons.append(out['reason'])
            for out in self.fvg.analyze(candles):
                votes.append(out['type']); reasons.append(out['reason'])
            for out in self.fib.analyze(candles):
                votes.append(out['type']); reasons.append(out['reason'])
            for out in self.vol.analyze(candles):
                votes.append(out['type']); reasons.append(out['reason'])
            for out in self.pa.analyze(candles):
                votes.append(out['type']); reasons.append(out['reason'])
            if not votes:
                continue
            # count calls/puts
            call_votes = votes.count("CALL")
            put_votes = votes.count("PUT")
            votes_total = call_votes + put_votes
            # pick side
            side = "CALL" if call_votes > put_votes else "PUT"
            # basic vote confidence
            vote_conf = int(round( (max(call_votes, put_votes) / max(1, votes_total)) * 100 ))
            # historical weight using logger winrate
            hist_win = self.logger.compute_winrate(pair=pair, lookback=500) or 50
            confidence = int(round(vote_conf*0.6 + hist_win*0.4))
            # adjust for market type
            mtype = self._market_type(pair)
            if mtype in ("OTC","CRYPTO","COMMODITY"):
                confidence = max(0, confidence - 5)
            if confidence < self.conf_publish:
                self.logger.info(f"{pair} confidence {confidence}% below publish threshold")
                continue
            # multi-TF confirmation
            if not self._multi_tf_confirm(pair, side):
                self.logger.info(f"{pair} higher TF not confirm {side}")
                continue
            # build signal
            sig = {
                "pair": pair,
                "market_type": mtype,
                "type": side,
                "price": data.get("price"),
                "confirmations": votes_total,
                "reasons": reasons,
                "confidence": confidence,
                "time": now,
                "scheduled_for": now + self.pre_seconds,
                "expiry": now + self.expiry
            }
            # reserve slot
            self.hourly_queue.append(now)
            self.last_signal_time[pair] = now
            signals.append(sig)
        return signals

    def _atr(self, candles):
        trs = []
        for i in range(1, len(candles)):
            h = candles[i]['high']; l = candles[i]['low']; pc = candles[i-1]['close']
            trs.append(max(h-l, abs(h-pc), abs(l-pc)))
        return sum(trs)/len(trs) if trs else 0

    def _atr_too_high(self, pair, atr):
        # heuristics, adjust per asset
        if pair in ["Bitcoin","Gold","UScrude","Silver"]:
            return atr > 50
        if "JPY" in pair or "USD/JPY" == pair:
            return atr > 0.2
        return atr > 0.003

    def _multi_tf_confirm(self, pair, desired_side):
        agrees = checked = 0
        for tf in self.higher_tfs:
            candles = self.client.get_historical(pair, timeframe=tf, limit=10)
            if not candles or len(candles) < 2:
                continue
            checked += 1
            if candles[-1]['close'] > candles[-2]['close'] and desired_side=="CALL":
                agrees += 1
            if candles[-1]['close'] < candles[-2]['close'] and desired_side=="PUT":
                agrees += 1
        if checked == 0:
            return True
        return agrees >= (checked//2)+1

    def _market_type(self, pair):
        for k in self.cfg.get("pairs",{}):
            if pair in self.cfg["pairs"][k]:
                return k
        return "REAL"
