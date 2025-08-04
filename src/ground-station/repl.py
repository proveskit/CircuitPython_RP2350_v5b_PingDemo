import json
import time

import board
import digitalio
from busio import SPI
from lib.proveskit_ground_station.proveskit_ground_station import GroundStation
from lib.pysquared.cdh import CommandDataHandler
from lib.pysquared.config.config import Config
from lib.pysquared.hardware.busio import _spi_init
from lib.pysquared.hardware.digitalio import initialize_pin
from lib.pysquared.hardware.radio.manager.rfm9x import RFM9xManager
from lib.pysquared.hardware.radio.packetizer.packet_manager import PacketManager
from lib.pysquared.logger import Logger
from lib.pysquared.nvm.counter import Counter

# TODO: Import util and call up these funcstions later
# TODO: Turn these into numbers instead of strings <3
SEND_LEADERBOARD_MAIN = "send_leaderboard_main"
RETURN_LEADERBOARD_MAIN = "return_leaderboard_main"
UPDATE_LEADERBOARD = "update_leaderboard"


logger: Logger = Logger(
    error_counter=Counter(1),
    colorized=False,
)
config: Config = Config("config.json")

spi0: SPI = _spi_init(
    logger,
    board.SPI0_SCK,
    board.SPI0_MOSI,
    board.SPI0_MISO,
)

radio = RFM9xManager(
    logger,
    config.radio,
    spi0,
    initialize_pin(logger, board.SPI0_CS0, digitalio.Direction.OUTPUT, True),
    initialize_pin(logger, board.RF1_RST, digitalio.Direction.OUTPUT, True),
)

packet_manager = PacketManager(
    logger,
    radio,
    config.radio.license,
    Counter(2),
    0.2,
)

cdh = CommandDataHandler(
    logger,
    config,
    packet_manager,
)

ground_station = GroundStation(
    logger,
    config,
    packet_manager,
    cdh,
)


def ask_for_leaderboard(main_cube_id="Main"):
    logger.info(f"Requesting leaderboard from {main_cube_id}...")
    message = {
        "current_time": time.monotonic(),
        "cube_id": main_cube_id,
        "command": SEND_LEADERBOARD_MAIN,
    }
    encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if not packet_manager.send(encoded_message):
        logger.warning(f"Failed to send leaderboard request to {main_cube_id}")
        return
    logger.info(f"Listening for response from {main_cube_id} for 30 seconds.")
    command = ""
    start_time = time.monotonic()
    while command != RETURN_LEADERBOARD_MAIN and time.monotonic() < start_time + 30:
        logger.info(f"Listening... {time.monotonic()}")
        received_message = packet_manager.listen(1)
        if not received_message:
            continue
        try:
            decoded_message = json.loads(received_message.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Failed to decode message: {e}")
            continue
        command = decoded_message.get("command")
        logger.info(f"Received: {received_message}")
        logger.info(f"Command: {command}")
    if command == RETURN_LEADERBOARD_MAIN:
        payload = decoded_message.get("leaderboard", {})
        print("LEADERBOARD:")
        if payload:
            sorted_leaderboard = sorted(payload.items(), key=lambda kv: (-kv[1], kv[0]))
            for i, (name, score) in enumerate(sorted_leaderboard, 1):
                print(f"{i}. {name}: {score}")
        else:
            print("Leaderboard is empty.")
    else:
        logger.warning("Did not receive leaderboard response in time.")


def ask_to_update(name):
    message = {
        "current_time": time.monotonic(),
        "command": UPDATE_LEADERBOARD,
        "cube_id": "any",
        "name": name,
    }
    encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if not packet_manager.send(encoded_message):
        logger.warning("Failed to send leaderboard request")
    else:  # TODO have cubes say who sent them :)
        logger.info("name sent! out in the world")


ground_station.run()
