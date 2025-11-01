# logger_util.py
import csv, os, threading, datetime
from collections import defaultdict

class Logger:
    def __init__(self, logfile="bot_log.txt", csvfile="signals_log.csv"):
        self.log_file = logfile
        self.csv_file = csvfile
        self.lock = threading.Lock()
        self._ensure_csv()
        self._strategy_stats_cache = {}

    def _ensure_csv(self):
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp","pair","market_type","signal","price","confidence","confirmations","reasons","expiry","scheduled_for","result","notes"])

    def log(self, level, msg):
        t = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{t}] [{level}] {msg}"
        with self.lock:
            print(line)
            try:
                with open(self.log_file, "a") as f:
                    f.write(line + "\n")
            except:
                pass

    def info(self, msg):
        self.log("INFO", msg)

    def error(self, msg):
        self.log("ERROR", msg)

    def log_signal(self, sig):
        with self.lock:
            try:
                with open(self.csv_file, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        sig.get("pair"),
                        sig.get("market_type"),
                        sig.get("type"),
                        sig.get("price"),
                        sig.get("confidence"),
                        sig.get("confirmations"),
                        "|".join(sig.get("reasons",[])),
                        sig.get("expiry"),
                        sig.get("scheduled_for",""),
                        sig.get("result",""),
                        sig.get("notes","")
                    ])
            except Exception as e:
                self.error(f"CSV write failed: {e}")

    def record_result(self, pair, result, notes=""):
        # Append result row; used when evaluating result externally
        with self.lock:
            try:
                with open(self.csv_file, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), pair, "", "", "", "", "", "", "", "", result, notes])
            except Exception as e:
                self.error(f"record_result failed: {e}")

    def compute_winrate(self, pair=None, lookback=1000):
        with self.lock:
            try:
                if not os.path.exists(self.csv_file):
                    return None
                with open(self.csv_file, "r") as f:
                    rows = f.read().splitlines()
                rows = rows[-lookback:]
                wins = total = 0
                for r in rows[1:]:
                    cols = r.split(",")
                    if len(cols) < 11:
                        continue
                    rpair = cols[1].strip()
                    result = cols[10].strip().upper()
                    if pair and rpair != pair:
                        continue
                    if result in ("WIN","W"):
                        wins += 1; total += 1
                    elif result in ("LOSS","L"):
                        total += 1
                if total == 0:
                    return None
                return int(round((wins/total)*100))
            except Exception as e:
                self.error(f"compute_winrate error: {e}")
                return None
