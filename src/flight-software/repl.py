import json
import os
import time

import board
import digitalio
import microcontroller
import storage
import supervisor
from lib.adafruit_mcp230xx.mcp23017 import (
    MCP23017,  # This is Hacky V5a Devel Stuff###
)
from lib.adafruit_tca9548a import TCA9548A  # This is Hacky V5a Devel Stuff###

# from lib.pysquared.Big_Data import AllFaces  ### This is Hacky V5a Devel Stuff##
from lib.pysquared.beacon import Beacon
from lib.pysquared.cdh import CommandDataHandler
from lib.pysquared.config.config import Config
from lib.pysquared.hardware.burnwire.manager.burnwire import BurnwireManager
from lib.pysquared.hardware.busio import _spi_init, initialize_i2c_bus
from lib.pysquared.hardware.digitalio import initialize_pin
from lib.pysquared.hardware.imu.manager.lsm6dsox import LSM6DSOXManager
from lib.pysquared.hardware.magnetometer.manager.lis2mdl import LIS2MDLManager
from lib.pysquared.hardware.power_monitor.manager.ina219 import INA219Manager
from lib.pysquared.hardware.radio.manager.rfm9x import RFM9xManager
from lib.pysquared.hardware.radio.packetizer.packet_manager import PacketManager
from lib.pysquared.logger import Logger
from lib.pysquared.nvm.counter import Counter
from lib.pysquared.protos.power_monitor import PowerMonitorProto
from lib.pysquared.rtc.manager.microcontroller import MicrocontrollerManager
from lib.pysquared.sleep_helper import SleepHelper
from lib.pysquared.watchdog import Watchdog

# Local imports
from version import __version__

SENDING_NEW_NAME = "sending_new_name"
UPDATING_NEW_NAME = "updating_new_name"
SEND_MESSAGE = "send_message"
SEND_MESSAGE_AKNOW = "send_message_aknowlagment"


def erase_system():
    """Erase the filesystem to allow new code to be written to the board."""
    storage.erase_filesystem()


def hard_reboot():
    """Perform a hard reboot of the microcontroller."""
    microcontroller.reset()


def get_temp(sensor):
    """
    Get temperature readings from a sensor for testing purposes.

    Args:
        sensor: Temperature sensor object
    """
    for i in range(1000):
        print(sensor.get_temperature().value)
        time.sleep(0.1)


# Initialize RTC
rtc = MicrocontrollerManager()

# Initialize logger
logger = Logger(
    error_counter=Counter(0),
    colorized=False,
    # log_level=3,
)

logger.info(
    "Booting",
    hardware_version=os.uname().version,  # type: ignore[attr-defined]
    software_version=__version__,
)

# Initialize watchdog
watchdog = Watchdog(logger, board.WDT_WDI)
watchdog.pet()

logger.debug("Initializing Config")
config: Config = Config("config.json")

mux_reset = initialize_pin(logger, board.MUX_RESET, digitalio.Direction.OUTPUT, False)

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

# sband_radio = SX1280Manager(
#     logger,
#     config.radio,
#     spi1,
#     initialize_pin(logger, board.SPI1_CS0, digitalio.Direction.OUTPUT, True),
#     initialize_pin(logger, board.RF2_RST, digitalio.Direction.OUTPUT, True),
#     initialize_pin(logger, board.RF2_IO0, digitalio.Direction.OUTPUT, True),
#     2.4,
#     initialize_pin(logger, board.RF2_TX_EN, digitalio.Direction.OUTPUT, False),
#     initialize_pin(logger, board.RF2_RX_EN, digitalio.Direction.OUTPUT, False),
# )

i2c1 = initialize_i2c_bus(
    logger,
    board.SCL1,
    board.SDA1,
    100000,
)

i2c0 = initialize_i2c_bus(
    logger,
    board.SCL0,
    board.SDA0,
    100000,
)


sleep_helper = SleepHelper(logger, config, watchdog)

uhf_radio = RFM9xManager(
    logger,
    config.radio,
    spi0,
    initialize_pin(logger, board.SPI0_CS0, digitalio.Direction.OUTPUT, True),
    initialize_pin(logger, board.RF1_RST, digitalio.Direction.OUTPUT, True),
)

magnetometer = LIS2MDLManager(logger, i2c1)

imu = LSM6DSOXManager(logger, i2c1, 0x6B)

uhf_packet_manager = PacketManager(
    logger,
    uhf_radio,
    config.radio.license,
    Counter(2),
    0.2,
)

cdh = CommandDataHandler(logger, config, uhf_packet_manager)

beacon = Beacon(
    logger,
    config.cubesat_name,
    uhf_packet_manager,
    time.monotonic(),
    imu,
    magnetometer,
    uhf_radio,
)

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
    This function turns off all of the faces. Note the load switches are disabled low.
    """
    FACE0_ENABLE.value = False
    FACE1_ENABLE.value = False
    FACE2_ENABLE.value = False
    FACE3_ENABLE.value = False
    FACE4_ENABLE.value = False


def all_faces_on():
    """
    This function turns on all of the faces. Note the load switches are enabled high.
    """
    FACE0_ENABLE.value = True
    FACE1_ENABLE.value = True
    FACE2_ENABLE.value = True
    FACE3_ENABLE.value = True
    FACE4_ENABLE.value = True


## Face Sensor Stuff ##

# This is the TCA9548A I2C Multiplexer
all_faces_on()
mux_reset.value = True
tca = TCA9548A(i2c1, address=int(0x77))


# light_sensor0 = VEML7700Manager(logger, tca[0])
# light_sensor1 = VEML7700Manager(logger, tca[1])
# light_sensor2 = VEML7700Manager(logger, tca[2])
# light_sensor3 = VEML7700Manager(logger, tca[3])
# light_sensor4 = VEML7700Manager(logger, tca[4])


# ## Onboard Temp Sensor ##
# temp_sensor5 = MCP9808Manager(logger, i2c0, addr=25)  # Antenna Board
# temp_sensor6 = MCP9808Manager(logger, i2c1, addr=27)  # Flight Controller Board
# temp_sensor0 = MCP9808Manager(logger, tca[0], addr=27)
# temp_sensor1 = MCP9808Manager(logger, tca[1], addr=27)
# temp_sensor2 = MCP9808Manager(logger, tca[2], addr=27)
# temp_sensor3 = MCP9808Manager(logger, tca[3], addr=27)
# temp_sensor4 = MCP9808Manager(logger, tca[4], addr=27)


battery_power_monitor: PowerMonitorProto = INA219Manager(logger, i2c1, 0x40)
solar_power_monitor: PowerMonitorProto = INA219Manager(logger, i2c1, 0x44)


## Init Misc Pins ##
burnwire_heater_enable = initialize_pin(
    logger, board.FIRE_DEPLOY1_A, digitalio.Direction.OUTPUT, False
)
burnwire1_fire = initialize_pin(
    logger, board.FIRE_DEPLOY1_B, digitalio.Direction.OUTPUT, False
)

## Initializing the Burn Wire ##
antenna_deployment = BurnwireManager(
    logger, burnwire_heater_enable, burnwire1_fire, enable_logic=True
)


def listen(my_callsign=None):
    if my_callsign is None:
        my_callsign = config.radio.license
    try:
        if supervisor.runtime.serial_bytes_available:
            typed = input().strip()
            if typed:
                handle_input(typed)
        b = uhf_packet_manager.listen(1)
        if b is not None:
            logger.info(message="Received response", responses=b.decode("utf-8"))
            decoded_message = json.loads(b.decode("utf-8"))
            command = decoded_message.get("command")
            if command == SEND_MESSAGE:
                sender_callsign = decoded_message.get("callsign")
                if sender_callsign != my_callsign:
                    message = decoded_message.get("message")
                    print(message)

    #                 response_message = {
    #                     "current_time" : time.monotonic(),
    #                     "callsign" : my_callsign,
    #                     "command" : SEND_MESSAGE_AKNOW,
    #                 }
    #                 encoded_response = json.dumps(response_message, separators=(",", ":")).encode(
    #                     "utf-8"
    #                 if uhf_packet_manager.send(encoded_response):
    #                     print("aknowlagment send back")
    #                 else:
    #                     print("aknowlagemnt not sent back")
    # )

    except KeyboardInterrupt:
        logger.debug("Keyboard interrupt received, exiting listen mode.")


def handle_input(cmd, my_callsign=None):
    if cmd[0] == ">":
        send_message(cmd, my_callsign)
    # else if cmd == 'PING':
    #     # to make ping work, need to do something when recieving the ping logs as well
    #     # also need to add something so that the sats ping back and you register what callsigns pinged back
    #     # also need to check for race conditions, can we print them all (id assume so butshould be tested)
    #     utils.nominal_power_loop(logger, uhf_packet_manager, sleep_helper, config)
    else:
        # this updates the name in the leaderboard
        send_name_out(cmd, my_callsign)


def send_message(message, my_callsign=None):
    if my_callsign is None:
        my_callsign = config.radio.license
    msg = "message received from " + my_callsign + " " + message
    response_message = {
        "current_time": time.monotonic(),
        "callsign": my_callsign,
        "command": SEND_MESSAGE,
        "message": msg,
    }
    encoded_response = json.dumps(response_message, separators=(",", ":")).encode(
        "utf-8"
    )

    # TODO fix this not retutning False when radio send is False
    if uhf_packet_manager.send(encoded_response):
        print("________________________________ \n\n\n")
        print("Message Sent!")
    else:
        print("________________________________ \n\n\n")
        print("Message Failed to Send! Try again")

    # received_message = uhf_packet_manager.listen(5)

    print(" \n\n\n________________________________")


def send_name_out(name, my_callsign=None):
    if my_callsign is None:
        my_callsign = config.radio.license
    response_message = {
        "current_time": time.monotonic(),
        "callsign": my_callsign,
        "command": SENDING_NEW_NAME,
        "name": name,
    }
    encoded_response = json.dumps(response_message, separators=(",", ":")).encode(
        "utf-8"
    )

    uhf_packet_manager.send(encoded_response)

    print("________________________________ \n\n\n")
    print(f"Name being sent to leaderboard! {name}")

    received_message = uhf_packet_manager.listen(1)
    if received_message is not None:
        decoded_message = json.loads(received_message.decode("utf-8"))
        command = decoded_message.get("command")

    if received_message is not None:
        decoded_message = json.loads(received_message.decode("utf-8"))
        command = decoded_message.get("command")
        if command == UPDATING_NEW_NAME:
            my_alledged_callsign = decoded_message.get("recepient")
            if my_alledged_callsign == my_callsign:
                amt = decoded_message.get("amt")
                selected = decoded_message.get("selected")
                display_message(amt, selected)

    else:
        print("Failed to Update. Try Sending again!")
    print("\n\n\n________________________________")


def print_cubesat():
    cubesat = r"""
     --|               |--
       |               |
       |               |
     --|               |--
        \_____________/
         |\           /|
         | \_________/ |
         | |░░░░░░░░░| |
         | |░░░░░░░░░| |
         | |░░░░░░░░░| |
         | |░░░░░░░░░| |
         | |_________| |
         |/___________\|
    """
    print(cubesat)


def display_message(booths_remaining, selected):
    if booths_remaining == 0:
        print("You have visited all the booths!!! Come claim your prize!")
        print_cubesat()
    else:
        print(f"Congratulations! You have visited {', '.join(selected)}.")
        if booths_remaining == 1:
            print(f"You still have {booths_remaining} booth left to visit!")
        else:
            print(f"You still have {booths_remaining} booths left to visit!")


while True:
    listen()
    time.sleep(1)
