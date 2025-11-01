# quotex_client.py
import os, time, json, threading, logging
from dotenv import load_dotenv
load_dotenv()
USERNAME = os.getenv("info.universefor.loop@gmail.com")
PASSWORD = os.getenv("mamunxD@091")

from playwright.sync_api import sync_playwright
import websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuotexClient")

class QuotexClient:
    def __init__(self, logger_obj=None):
        self.logger = logger_obj or logger
        self.session_cookie = {}
        self.ws = None
        self.ws_thread = None
        self._stop = False
        self._live = {}  # pair -> {price,time,candles,volume,spread}
        self.pairs = []
        self.connected = False

    # ----- Playwright login to fetch cookies/session -----
    def login_via_playwright(self, headless=True):
        if not USERNAME or not PASSWORD:
            self.logger.info("No credentials provided — run in demo mode.")
            return False
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=headless)
                ctx = browser.new_context()
                page = ctx.new_page()
                page.goto("https://quotex.io/", timeout=30000)
                time.sleep(1)
                # Attempt to open sign-in and fill inputs — selectors may vary by build
                try:
                    if page.query_selector("input[type='email']"):
                        page.fill("input[type='email']", USERNAME)
                        page.fill("input[type='password']", PASSWORD)
                        page.press("input[type='password']", "Enter")
                    else:
                        # fallback attempts
                        if page.query_selector("input[name='email']"):
                            page.fill("input[name='email']", USERNAME)
                            page.fill("input[name='password']", PASSWORD)
                            page.press("input[name='password']", "Enter")
                except Exception as e:
                    self.logger.info(f"Playwright auto-fill fallback: {e}")
                time.sleep(3)
                cookies = ctx.cookies()
                self.session_cookie = {c['name']: c['value'] for c in cookies}
                browser.close()
                self.logger.info(f"Playwright login done, cookies {len(self.session_cookie)} captured.")
                return True
        except Exception as e:
            self.logger.error(f"Playwright login failed: {e}")
            return False

    # ----- WebSocket connection -----
    def _on_message(self, ws, message):
        # Generic parser: log raw and attempt to extract price info
        try:
            if isinstance(message, bytes):
                payload = message.decode('utf-8', errors='ignore')
            else:
                payload = message
            if os.getenv("DEBUG_WS","false").lower()=="true":
                self.logger.info(f"WS RAW: {payload[:1000]}")
            # try parse JSON part
            data = None
            try:
                # socket.io may prefix '42'
                if payload.startswith("42"):
                    data = json.loads(payload[2:])
                else:
                    data = json.loads(payload)
            except:
                data = None
            if data:
                # scan for price-like dicts
                # This must be adapted to actual WS format; user should paste sample logs for exact mapping
                if isinstance(data, dict):
                    for k,v in data.items():
                        if isinstance(v, dict) and ('price' in v or 'last' in v):
                            p = k.upper()
                            price = v.get('price', v.get('last'))
                            self._live[p] = {"price": float(price), "time": time.time(), "candles": v.get('candles',[]), "volume": v.get('volume',0), "spread": v.get('spread',None)}
                elif isinstance(data, list) and len(data)>=2 and isinstance(data[1], dict):
                    body = data[1]
                    # heuristics - adapt as needed
                    for k,v in body.items():
                        if isinstance(v, dict) and ('last' in v or 'price' in v):
                            p = k.upper()
                            price = v.get('price', v.get('last'))
                            self._live[p] = {"price": float(price), "time": time.time(), "candles": v.get('candles',[]), "volume": v.get('volume',0), "spread": v.get('spread',None)}
        except Exception as e:
            self.logger.error(f"WS on_message parse error: {e}")

    def _on_open(self, ws):
        self.logger.info("WebSocket opened")
        self.connected = True

    def _on_error(self, ws, err):
        self.logger.error(f"WebSocket error: {err}")

    def _on_close(self, ws, code, msg):
        self.logger.info("WebSocket closed")
        self.connected = False

    def connect_ws(self, ws_url=None, headers=None):
        if not ws_url:
            ws_url = "wss://ws.qxbroker.com/socket.io/?EIO=3&transport=websocket"
        hdrs = headers or {}
        if self.session_cookie:
            hdrs['Cookie'] = "; ".join([f"{k}={v}" for k,v in self.session_cookie.items()])
        def run():
            while not self._stop:
                try:
                    ws = websocket.WebSocketApp(ws_url,
                                                header=[f"{k}: {v}" for k,v in hdrs.items()],
                                                on_message=self._on_message,
                                                on_open=self._on_open,
                                                on_error=self._on_error,
                                                on_close=self._on_close)
                    self.ws = ws
                    ws.run_forever(ping_interval=20, ping_timeout=10)
                except Exception as e:
                    self.logger.error(f"WS loop error: {e}")
                self.logger.info("WS disconnected, retrying in 3s...")
                time.sleep(3)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        self.ws_thread = t
        return True

    def start(self):
        ok = self.login_via_playwright(headless=True)
        self.connect_ws()
        return ok

    def stop(self):
        self._stop = True
        try:
            if self.ws:
                self.ws.close()
        except:
            pass

    # helpers used by signal engine
    def get_live_snapshot(self, pairs, timeframe="1m"):
        # Ensure keys uppercase and normalized e.g., EUR/USD -> EURUSD
        snapshot = {}
        for p in pairs:
            key = p.replace("/","").upper()
            if key in self._live:
                snapshot[p] = self._live[key]
            else:
                # fallback: synthetic placeholder to keep engine running
                snapshot[p] = {"price": None, "time": time.time(), "candles": [], "volume":0, "spread": None}
        return snapshot

    def get_historical(self, pair, timeframe="1m", limit=200):
        # IMPORTANT: Implement real historical fetch if possible. For now return [] so strategies handle
        return []
