# from busio import _spi_init
# import os
# from lib.pysquared.nvm.counter import Counter

# import board
# import sdcardio
import os

import storage

# This tells the computer to disconnect from the board's mass storage device (CIRCUITPY drive).
# This is the correct method for CircuitPython 9+


# wait_time = 0.2
# time.sleep(wait_time)
storage.disable_usb_drive()  # disable CIRCUITPY
# Ensure 'sd' directory exists
if "sd" not in os.listdir():
    os.mkdir("sd")

# Ensure the leaderboard.json file exists with "{}" if not
try:
    with open("sd/leaderboard.json", "r") as file:
        pass  # File exists
except OSError:
    with open("sd/leaderboard.json", "w") as file:
        file.write("{}")


# After the USB drive is disabled, we can remount the /sd filesystem
# as writable for our CircuitPython code.
# storage.remount("/sd", readonly=False)

# os.mkdir("/sd")  # Ensure the lib directory exists'

# from lib.pysquared.logger import Logger

# logger: Logger = Logger(
#     error_counter=Counter(0),
#     colorized=False,
# )

# spi1 = _spi_init(
#     logger,
#     board.SPI1_SCK,
#     board.SPI1_MOSI,
#     board.SPI1_MISO,
# )

# sd = sdcardio.SDCard(spi1, board.SPI1_CS1)
# vfs = storage.VfsFat(sd)

# storage.mount(vfs, "/sd")
# os.listdir("/sd")
