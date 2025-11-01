# notifier.py
import time, sys, threading
from colorama import Fore, Style, init
init(autoreset=True)

OWNER = "David Mamun William"
MOTIVATIONS = [
    "Trust the process — focus, discipline, execution.",
    "Patience first. Precision next. Profit follows.",
    "Discipline creates consistency. Consistency creates edge."
]

class Notifier:
    def __init__(self, logger, utc_offset=6):
        self.logger = logger
        self.utc_offset = int(utc_offset)
        self.threads = []

    def _format_ts(self, ts):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts + self.utc_offset*3600))

    def show_pre_and_final(self, sig):
        # non-blocking countdown then final display
        t = threading.Thread(target=self._runner, args=(sig,), daemon=True)
        t.start()
        self.threads.append(t)

    def _runner(self, sig):
        pre = int(sig.get("scheduled_for", sig.get("time", time.time())) - time.time())
        pre = max(1, pre)
        for s in range(pre,0,-1):
            sys.stdout.write(Fore.YELLOW + Style.BRIGHT + f"\rPRE-SIGNAL {sig['pair']} -> {sig['type']} in {s}s | CONF {sig['confidence']}% ")
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\n")
        self.display(sig)

    def display(self, sig):
        # color by confidence
        conf = sig.get("confidence",0)
        if conf >= 85:
            color = Fore.GREEN
            suggestion = "STRONG — TAKE"
        elif conf >= 70:
            color = Fore.CYAN
            suggestion = "GOOD — CONSIDER"
        elif conf >= 60:
            color = Fore.YELLOW
            suggestion = "CAUTION — SMALL SIZE"
        else:
            color = Fore.RED
            suggestion = "WAIT"

        badge = sig.get("market_type","REAL")
        print(Fore.MAGENTA + "╔" + "═"*78 + "╗")
        print(Fore.MAGENTA + f"║  ULTRA SNIPER SIGNAL  |  Owner: {OWNER}".ljust(79) + "║")
        print(Fore.MAGENTA + "╠" + "═"*78 + "╣")
        print(color + f"║  Pair: {sig['pair']:<12} Type: {sig['type']:<4} Market: {badge:<10} Confidence: {conf:3}%  {suggestion}".ljust(79) + "║")
        print(color + f"║  Price: {sig.get('price')}  Expiry(UTC+{self.utc_offset}): {self._format_ts(sig.get('expiry'))}  Confirmations: {sig.get('confirmations')}".ljust(79) + "║")
        print(Fore.MAGENTA + f"║  Reasons: {', '.join(sig.get('reasons',[]))}".ljust(79) + "║")
        print(Fore.MAGENTA + "╚" + "═"*78 + "╝")
        self.logger.info(f"Displayed signal {sig['pair']} {sig['type']} conf {conf}%")
