# bot_main.py
import os, time, json
from dotenv import load_dotenv
load_dotenv()
from logger_util import Logger
from quotex_client import QuotexClient
from signal_generator import SignalGenerator
from notifier import Notifier

# load config
with open("config.json") as f:
    CONFIG = json.load(f)

logger = Logger()
client = QuotexClient(logger_obj=logger)
client.start()

signal_gen = SignalGenerator(client, logger, CONFIG)
notifier = Notifier(logger, utc_offset=CONFIG.get("utc_offset_hours",6))

logger.info("==== TheSniperBinaryBot STARTED ====")
logger.info("Owner: David Mamun William")

try:
    while True:
        try:
            # generate signals from live feed
            signals = signal_gen.generate_signals()
            for s in signals:
                # log immediately, then show pre-countdown + final
                logger.log_signal(s)
                notifier.show_pre_and_final(s)
            # scheduled predictions (optional) - using generator if exists
            if hasattr(signal_gen, "generate_scheduled_signals"):
                scheduled = signal_gen.generate_scheduled_signals()
                for s in scheduled:
                    logger.log_signal(s)
                    notifier.display(s)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(2)
except KeyboardInterrupt:
    logger.info("Stopping bot by user")
    client.stop()
    time.sleep(1)
