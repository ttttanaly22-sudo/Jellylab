from datetime import datetime
from config import LOG_DIR
import csv
import os


def save_log(temp, lux):

    os.makedirs(LOG_DIR, exist_ok=True)

    filename = datetime.now().strftime(
        f"{LOG_DIR}/%Y%m%d.csv"
    )

    new_file = not os.path.exists(filename)

    with open(filename, "a", newline="") as f:

        writer = csv.writer(f)

        if new_file:
            writer.writerow([
                "Time",
                "Temperature",
                "Lux"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            round(temp, 2) if temp is not None else "",
            round(lux, 1) if lux is not None else ""
        ])
