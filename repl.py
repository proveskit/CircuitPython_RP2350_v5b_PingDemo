# This is where the magic happens!
# This file is executed on every boot (including wake-boot from deepsleep)
# Created By: Michael Pham

"""
Built for the PySquared V5a FC Board
Version: X.X.X
Published:
"""

import time

import digitalio

try:
    # from board_definitions import proveskit_rp2040_v4 as board
    raise ImportError
except ImportError:
    import board

import os

import lib.pysquared.functions as functions
import lib.pysquared.nvm.register as register
from lib.adafruit_mcp230xx.mcp23017 import (
    MCP23017,  ### This is Hacky V5a Devel Stuff###
)
from lib.adafruit_mcp9808 import MCP9808  ### This is Hacky V5a Devel Stuff###
from lib.adafruit_tca9548a import TCA9548A  ### This is Hacky V5a Devel Stuff###

# from lib.pysquared.Big_Data import AllFaces  ### This is Hacky V5a Devel Stuff###
from lib.pysquared.cdh import CommandDataHandler
from lib.pysquared.config.config import Config
from lib.pysquared.hardware.busio import _spi_init, initialize_i2c_bus
from lib.pysquared.hardware.digitalio import initialize_pin
from lib.pysquared.hardware.imu.manager.lsm6dsox import LSM6DSOXManager
from lib.pysquared.hardware.magnetometer.manager.lis2mdl import LIS2MDLManager
from lib.pysquared.hardware.radio.manager.rfm9x import RFM9xManager
from lib.pysquared.hardware.radio.manager.sx1280 import SX1280Manager
from lib.pysquared.logger import Logger
from lib.pysquared.nvm.counter import Counter
from lib.pysquared.nvm.flag import Flag
from lib.pysquared.rtc.manager.microcontroller import MicrocontrollerManager
from lib.pysquared.satellite import Satellite
from lib.pysquared.sleep_helper import SleepHelper
from lib.pysquared.watchdog import Watchdog
from version import __version__

rtc = MicrocontrollerManager()

logger: Logger = Logger(
    error_counter=Counter(index=register.ERRORCNT),
    colorized=False,
)

logger.info(
    "Booting",
    hardware_version=os.uname().version,
    software_version=__version__,
)

watchdog = Watchdog(logger, board.WDT_WDI)
watchdog.pet()

logger.debug("Initializing Config")
config: Config = Config("config.json")

# TODO(nateinaction): fix spi init
spi0 = _spi_init(
    logger,
    board.SPI0_SCK,
    board.SPI0_MOSI,
    board.SPI0_MISO,
)

spi1 = _spi_init(
    logger,
    board.SPI1_SCK,
    board.SPI1_MOSI,
    board.SPI1_MISO,
)

i2c0 = initialize_i2c_bus(
    logger,
    board.SCL0,
    board.SDA0,
    100000,
)

i2c1 = initialize_i2c_bus(
    logger,
    board.SCL1,
    board.SDA1,
    100000,
)

c = Satellite(logger, config)

sleep_helper = SleepHelper(c, logger, watchdog)

radio = RFM9xManager(
    logger,
    config.radio,
    Flag(index=register.FLAG, bit_index=7),
    spi0,
    initialize_pin(logger, board.SPI0_CS0, digitalio.Direction.OUTPUT, True),
    initialize_pin(logger, board.RF1_RST, digitalio.Direction.OUTPUT, True),
)

magnetometer = LIS2MDLManager(logger, i2c1)

imu = LSM6DSOXManager(logger, i2c1, 0x6B)

cdh = CommandDataHandler(config, logger, radio)

f = functions.functions(
    c,
    logger,
    config,
    sleep_helper,
    radio,
    magnetometer,
    imu,
    watchdog,
    cdh,
)

### This is Hacky V5a Devel Stuff###

## Initialize the Second Radio ##

use_fsk_flag = Flag(index=register.FLAG, bit_index=7)

radio2 = SX1280Manager(
    logger,
    config.radio,
    use_fsk_flag,
    spi1,
    initialize_pin(logger, board.SPI1_CS0, digitalio.Direction.OUTPUT, True),
    initialize_pin(logger, board.RF2_RST, digitalio.Direction.OUTPUT, True),
    initialize_pin(logger, board.RF2_IO0, digitalio.Direction.OUTPUT, True),
    2.4,
    initialize_pin(logger, board.RF2_TX_EN, digitalio.Direction.OUTPUT, True),
    initialize_pin(logger, board.RF2_RX_EN, digitalio.Direction.OUTPUT, True),
)

radio2.send("Hello World")
print("Radio2 sent Hello World")

## Initializing the Burn Wire ##
ENABLE_BURN_A = initialize_pin(
    logger, board.FIRE_DEPLOY1_A, digitalio.Direction.OUTPUT, True
)
ENABLE_BURN_B = initialize_pin(
    logger, board.FIRE_DEPLOY1_B, digitalio.Direction.OUTPUT, True
)


def dumb_burn(duration=5) -> None:
    """
    This function is used to test the burn wire.
    It will turn on the burn wire for 5 seconds and then turn it off.

    Args:
        duration (int): The duration to burn for in seconds. Default is 5 seconds.
    Returns:
        None
    """
    ENABLE_BURN_A.value = False
    ENABLE_BURN_B.value = False
    logger.info("Burn Wire Enabled")
    time.sleep(duration)
    logger.info("Burn Wire Disabled")
    ENABLE_BURN_A.value = True
    ENABLE_BURN_B.value = True


## Initializing the Heater ##
def heater_pulse() -> None:
    """
    This function is used to turn on the heater.
    It will turn on the heater for 5 seconds and then turn it off.

    Args:
        None
    Returns:
        None
    """
    ENABLE_HEATER.value = False
    logger.info("Heater Enabled")
    time.sleep(5)
    logger.info("Heater Disabled")
    ENABLE_HEATER.value = True


## Initialize the MCP23017 GPIO Expander and its pins ##
GPIO_RESET = initialize_pin(
    logger, board.GPIO_EXPANDER_RESET, digitalio.Direction.OUTPUT, True
)
mcp = MCP23017(i2c1)

# This sets up all of the GPIO pins on the MCP23017
FACE4_ENABLE = mcp.get_pin(8)
FACE0_ENABLE = mcp.get_pin(9)
FACE1_ENABLE = mcp.get_pin(10)
FACE2_ENABLE = mcp.get_pin(11)
FACE3_ENABLE = mcp.get_pin(12)
ENAB_RF = mcp.get_pin(13)
VBUS_RESET = mcp.get_pin(14)
SPI0_CS1 = mcp.get_pin(15)
ENABLE_HEATER = mcp.get_pin(0)
PAYLOAD_PWR_ENABLE = mcp.get_pin(1)
Z_GPIO0 = mcp.get_pin(2)
Z_GPIO1 = mcp.get_pin(3)
RF2_IO2 = mcp.get_pin(4)
RF2_IO1 = mcp.get_pin(5)

# This defines the direction of the GPIO pins
FACE4_ENABLE.direction = digitalio.Direction.OUTPUT
FACE0_ENABLE.direction = digitalio.Direction.OUTPUT
FACE1_ENABLE.direction = digitalio.Direction.OUTPUT
FACE2_ENABLE.direction = digitalio.Direction.OUTPUT
FACE3_ENABLE.direction = digitalio.Direction.OUTPUT
ENAB_RF.direction = digitalio.Direction.OUTPUT
VBUS_RESET.direction = digitalio.Direction.OUTPUT
ENABLE_HEATER.direction = digitalio.Direction.OUTPUT
PAYLOAD_PWR_ENABLE.direction = digitalio.Direction.OUTPUT


# Face Control Helper Functions
def all_faces_off():
    """
    This function turns off all of the faces. Note the load switches are disabled high.
    """
    FACE0_ENABLE.value = True
    FACE1_ENABLE.value = True
    FACE2_ENABLE.value = True
    FACE3_ENABLE.value = True
    FACE4_ENABLE.value = True


def all_faces_on():
    """
    This function turns on all of the faces. Note the load switches are enabled low.
    """
    FACE0_ENABLE.value = False
    FACE1_ENABLE.value = False
    FACE2_ENABLE.value = False
    FACE3_ENABLE.value = False
    FACE4_ENABLE.value = False


## Face Sensor Stuff ##

# This is the TCA9548A I2C Multiplexer
mux_reset = initialize_pin(logger, board.MUX_RESET, digitalio.Direction.OUTPUT, True)
all_faces_on()

tca = TCA9548A(i2c1, address=int(0x77))

# all_faces = AllFaces(tca, logger)

## Onboard Temp Sensor ##
mcp = MCP9808(i2c1, address=30)  # Not working for some reason

### This is Hacky V5a Devel Stuff###
