import smbus2
import time

ADDRESS = 0x23

try:
    bus = smbus2.SMBus(1)
except:
    bus = None


def get_lux():

    if bus is None:
        return None

    try:
        bus.write_byte(ADDRESS, 0x10)
        time.sleep(0.18)

        data = bus.read_i2c_block_data(ADDRESS, 0x00, 2)

        return ((data[0] << 8) + data[1]) / 1.2

    except:
        return None