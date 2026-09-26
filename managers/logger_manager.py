import threading
import time
from config import LOG_INTERVAL

from managers.sensor_manager import get_status
from utils.logger import save_log


def logger_loop():

    while True:

        status = get_status()

        save_log(
            status["temperature"],
            status["lux"]
        )

        time.sleep(LOG_INTERVAL)


def start_logger():

    thread = threading.Thread(
        target=logger_loop,
        daemon=True
    )

    thread.start()