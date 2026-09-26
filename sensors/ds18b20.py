import glob

devices = glob.glob("/sys/bus/w1/devices/28-*")

DEVICE = devices[0] if devices else None


def get_temperature():

    if DEVICE is None:
        return None

    try:
        with open(DEVICE + "/temperature") as f:
            return int(f.read()) / 1000
    except:
        return None