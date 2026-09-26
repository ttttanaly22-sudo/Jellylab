from sensors.ds18b20 import get_temperature
from sensors.bh1750 import get_lux


def get_status():

    return {
        "temperature": get_temperature(),
        "lux": get_lux()
    }