import gc
import json
import os
import time

import board
import digitalio
import microcontroller
from lib.proveskit_rp2350_v5b.register import Register
from lib.pysquared.beacon import Beacon
from lib.pysquared.cdh import CommandDataHandler
from lib.pysquared.config.config import Config
from lib.pysquared.hardware.busio import _spi_init, initialize_i2c_bus
from lib.pysquared.hardware.digitalio import initialize_pin
from lib.pysquared.hardware.imu.manager.lsm6dsox import LSM6DSOXManager
from lib.pysquared.hardware.magnetometer.manager.lis2mdl import LIS2MDLManager
from lib.pysquared.hardware.radio.manager.rfm9x import RFM9xManager
from lib.pysquared.hardware.radio.manager.sx1280 import SX1280Manager
from lib.pysquared.hardware.radio.packetizer.packet_manager import PacketManager
from lib.pysquared.logger import Logger
from lib.pysquared.nvm.counter import Counter
from lib.pysquared.rtc.manager.microcontroller import MicrocontrollerManager
from lib.pysquared.sleep_helper import SleepHelper
from lib.pysquared.watchdog import Watchdog
from version import __version__

boot_time: float = time.time()

cube_ids = ["Listener1", "Listener2", "Listener3"]
my_cubesat_id = "MainSat"

rtc = MicrocontrollerManager()

(boot_count := Counter(index=Register.boot_count)).increment()
error_count: Counter = Counter(index=Register.error_count)

logger: Logger = Logger(
    error_counter=error_count,
    colorized=False,
)

logger.info(
    "Booting",
    hardware_version=os.uname().version,
    software_version=__version__,
)

loiter_time: int = 5
for i in range(loiter_time):
    logger.info(f"Code Starting in {loiter_time-i} seconds")
    time.sleep(1)

try:
    watchdog = Watchdog(logger, board.WDT_WDI)
    watchdog.pet()

    logger.debug("Initializing Config")
    config: Config = Config("config.json")

    mux_reset = initialize_pin(
        logger, board.MUX_RESET, digitalio.Direction.OUTPUT, False
    )

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

    sband_radio = SX1280Manager(
        logger,
        config.radio,
        spi1,
        initialize_pin(logger, board.SPI1_CS0, digitalio.Direction.OUTPUT, True),
        initialize_pin(logger, board.RF2_RST, digitalio.Direction.OUTPUT, True),
        initialize_pin(logger, board.RF2_IO0, digitalio.Direction.OUTPUT, True),
        2.4,
        initialize_pin(logger, board.RF2_TX_EN, digitalio.Direction.OUTPUT, False),
        initialize_pin(logger, board.RF2_RX_EN, digitalio.Direction.OUTPUT, False),
    )

    i2c1 = initialize_i2c_bus(
        logger,
        board.SCL1,
        board.SDA1,
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
        Counter(Register.message_count),
        0.2,
    )

    cdh = CommandDataHandler(logger, config, uhf_packet_manager)

    beacon = Beacon(
        logger,
        config.cubesat_name,
        uhf_packet_manager,
        boot_time,
        imu,
        magnetometer,
        uhf_radio,
        sband_radio,
        error_count,
        boot_count,
    )

    def nominal_power_loop():
        logger.debug(
            "FC Board Stats",
            bytes_remaining=gc.mem_free(),
        )

        message: dict[str, object] = dict()
        for cube_id in cube_ids:
            if cube_id == my_cubesat_id:
                continue

            # --- 1. Send a ping to a single cubesat ---
            logger.info(f"Pinging {cube_id}...")
            message["current_time"] = time.monotonic()
            message["cube_id"] = cube_id
            message["command"] = "ping"
            encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")

            if not uhf_packet_manager.send(encoded_message):
                logger.warning(f"Failed to send ping to {cube_id}")
                sleep_helper.safe_sleep(1)  # Wait a moment before trying the next one
                continue

            # --- 2. Listen for an immediate pong response ---
            logger.info(f"Listening for pong from {cube_id} for 10 seconds.")
            received_message = uhf_packet_manager.listen(10)

            if received_message:
                try:
                    decoded_message = json.loads(received_message.decode("utf-8"))
                    sender_id = decoded_message.get("cube_id")
                    command = decoded_message.get("command")
                    if command == "pong" and sender_id == cube_id:
                        logger.info(
                            f"_______!!!!!!!!!!Success! Received pong for me from {sender_id}.!!!!!!!!!!!!_______"
                        )
                    else:
                        logger.warning(
                            f"Received unexpected message: {decoded_message}"
                        )
                except (json.JSONDecodeError, UnicodeError) as e:
                    logger.error("Could not process received message", e)
            else:
                logger.warning(f"No response from {cube_id} within the time limit.")

            # --- 3. Wait before contacting the next satellite ---
            logger.debug("Waiting 5 seconds before contacting next satellite.")
            sleep_helper.safe_sleep(5)

    def listener_nominal_power_loop():
        # logger.debug(
        #     "FC Board Stats",
        #     bytes_remaining=gc.mem_free(),
        # )

        # logger.info("Listening for messages for 60 seconds")
        received_message: bytes | None = uhf_packet_manager.listen(5)

        if received_message:
            try:
                decoded_message = json.loads(received_message.decode("utf-8"))
                logger.info(f"Received message: {decoded_message}")

                cubesat_id = decoded_message.get("cube_id")
                if cubesat_id == my_cubesat_id:
                    command = decoded_message.get("command")
                    if command == "ping":
                        logger.info(
                            f"_______!!!!!!!!!! Received ping from {cubesat_id} !!!!!!!!!!!!_______"
                        )
                        response_message = {
                            "current_time": time.monotonic(),
                            "cube_id": my_cubesat_id,
                            "command": "pong",
                        }
                        encoded_response = json.dumps(
                            response_message, separators=(",", ":")
                        ).encode("utf-8")
                        sleep_helper.safe_sleep(1)
                        uhf_packet_manager.send(encoded_response)

            except (json.JSONDecodeError, UnicodeError) as e:
                logger.error("Failed to decode message", e)

    try:
        logger.info("Entering main loop")
        while True:
            # TODO(nateinaction): Modify behavior based on power state
            nominal_power_loop()

    except Exception as e:
        logger.critical("Critical in Main Loop", e)
        time.sleep(10)
        microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
        microcontroller.reset()
    finally:
        logger.info("Going Neutral!")

except Exception as e:
    logger.critical("An exception occured within main.py", e)
