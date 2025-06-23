# This is where the magic happens!
# This file is executed on every boot (including wake-boot from deepsleep)
# Created By: Michael Pham

"""
Built for the PySquared V5a FC Board
Version: X.X.X
Published:
"""

import gc
import os
import time

import board
import digitalio
import microcontroller

import lib.pysquared.functions as functions
import lib.pysquared.nvm.register as register
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

loiter_time: int = 15

try:
    for i in range(loiter_time):
        logger.info(f"Code Starting in {loiter_time-i} seconds")
        time.sleep(1)

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

    use_fsk_flag = Flag(index=register.FLAG, bit_index=7)

    radio = SX1280Manager(
        logger,
        config.radio,
        spi1,
        initialize_pin(logger, board.SPI1_CS0, digitalio.Direction.OUTPUT, True),
        initialize_pin(logger, board.RF2_RST, digitalio.Direction.OUTPUT, True),
        initialize_pin(logger, board.RF2_IO0, digitalio.Direction.OUTPUT, True),
        2.4,
        initialize_pin(logger, board.RF2_TX_EN, digitalio.Direction.OUTPUT, True),
        initialize_pin(logger, board.RF2_RX_EN, digitalio.Direction.OUTPUT, True),
    )

    i2c1 = initialize_i2c_bus(
        logger,
        board.SCL1,
        board.SDA1,
        100000,
    )

    c = Satellite(logger, config)

    sleep_helper = SleepHelper(c, logger, watchdog, config)

    try:
        radio = RFM9xManager(
            logger,
            config.radio,
            spi0,
            initialize_pin(logger, board.SPI0_CS0, digitalio.Direction.OUTPUT, True),
            initialize_pin(logger, board.RF1_RST, digitalio.Direction.OUTPUT, True),
        )
    except Exception as e:
        logger.error("Failed to initialize RFM9x radio", e)

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

    def initial_boot():
        watchdog.pet()
        f.beacon()
        watchdog.pet()
        f.listen()
        watchdog.pet()

    try:
        c.boot_count.increment()

        logger.info(
            "FC Board Stats",
            bytes_remaining=gc.mem_free(),
            boot_number=c.boot_count.get(),
        )

        initial_boot()

    except Exception as e:
        logger.error("Error in Boot Sequence", e)

    finally:
        pass

    def send_imu_data():
        logger.info("Looking to get imu data...")
        IMUData = []
        watchdog.pet()
        logger.info("IMU has baton")
        IMUData = imu.get_gyro_data()
        watchdog.pet()
        radio.send(IMUData)

    def main():
        f.beacon()

        f.listen_loiter()

        f.state_of_health()

        f.listen_loiter()

        watchdog.pet()

        f.listen_loiter()

        send_imu_data()

        f.listen_loiter()

        f.joke()

        f.listen_loiter()

    def critical_power_operations():
        initial_boot()
        watchdog.pet()

        sleep_helper.long_hibernate()

    def minimum_power_operations():
        initial_boot()
        watchdog.pet()

        sleep_helper.short_hibernate()

    ######################### MAIN LOOP ##############################
    try:
        while True:
            # L0 automatic tasks no matter the battery level
            c.check_reboot()

            if c.power_mode == "critical":
                critical_power_operations()

            elif c.power_mode == "minimum":
                minimum_power_operations()

            elif c.power_mode == "normal":
                main()

            elif c.power_mode == "maximum":
                main()

            else:
                f.listen()

    except Exception as e:
        logger.critical("Critical in Main Loop", e)
        time.sleep(10)
        microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
        microcontroller.reset()
    finally:
        logger.info("Going Neutral!")

except Exception as e:
    logger.critical("An exception occured within main.py", e)
