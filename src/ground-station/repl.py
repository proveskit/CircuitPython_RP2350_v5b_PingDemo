import json
import os
import time

import board
import digitalio
import supervisor
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
SENDING_NEW_NAME = "sending_new_name"
UPDATING_NEW_NAME = "updating_new_name"

byte_dict = {
    "Main": b"10000",
    "Portla": b"01000",
    "hawaii": b"00100",
    "texas": b"00010",
    "cygnet": b"00001",
}

key_order = ["Main", "Portla", "hawaii", "texas", "cygnet"]


logger: Logger = Logger(
    error_counter=Counter(1),
    colorized=False,
    log_level=3,
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


def ask_for_leaderboard(main_callsign=None):
    if main_callsign is None:
        main_callsign = config.radio.license
    logger.info(f"Requesting leaderboard from {main_callsign}...")
    message = {
        "current_time": time.monotonic(),
        "callsign": main_callsign,
        "command": SEND_LEADERBOARD_MAIN,
    }
    encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if not packet_manager.send(encoded_message):
        logger.warning(f"Failed to send leaderboard request to {main_callsign}")
        return
    logger.info(f"Listening for response from {main_callsign} for 30 seconds.")
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
        "callsign": "any",
        "name": name,
    }
    encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")
    if not packet_manager.send(encoded_message):
        logger.warning("Failed to send leaderboard request")
    else:  # TODO have cubes say who sent them :)
        logger.info("name sent! out in the world")


def listen_display(my_callsign=None):
    last_display_time = time.monotonic()
    display_top_10()
    try:
        while True:
            if supervisor.runtime.serial_bytes_available:
                typed = input().strip()
                if typed:
                    handle_input(typed)

            # display the leaderboard every 5 seconds
            current_time = time.monotonic()
            if current_time - last_display_time >= 5:
                display_top_10()
                last_display_time = current_time

            received_message = packet_manager.listen(1)
            if received_message is not None:
                # logger.debug("recieved not None")
                try:
                    decoded_message = json.loads(received_message.decode("utf-8"))
                    # logger.debug(f"Received message: {decoded_message}")
                    command = decoded_message.get("command")
                    if command == SENDING_NEW_NAME:
                        sender_callsign = decoded_message.get("callsign")
                        name = decoded_message.get("name")
                        if sender_callsign in byte_dict.keys():
                            leader_status = update_distinct_leaderboard(
                                name, byte_dict[sender_callsign]
                            )

                            booths_remaining, selected = display_leader_status(
                                leader_status
                            )

                            if my_callsign is None:
                                my_callsign = config.radio.license

                            response_message = {
                                "current_time": time.monotonic(),
                                "callsign": my_callsign,
                                "recepient": sender_callsign,
                                "command": UPDATING_NEW_NAME,
                                "amt": booths_remaining,
                                "selected": selected,
                            }
                            encoded_response = json.dumps(
                                response_message, separators=(",", ":")
                            ).encode("utf-8")
                            # print(f"Sending leaderboard: {encoded_response}")
                            packet_manager.send(encoded_response)

                        else:
                            print(
                                f"Error: {sender_callsign} is not a configured Cubesat"
                            )
                except ValueError:
                    logger.error("Failed to decode message")
    except KeyboardInterrupt:
        print("Stopping listener.")


def handle_input(name):
    display_leaderboard_status_from_name(name)


def display_top_10():
    filepath = "sd/leaderboard.json"
    try:
        with open(filepath, "r") as file:
            leaderboard_dict = json.load(file)
    except Exception as e:
        print("Could not read leaderboard:", e)
        return
    scores = []
    for name, bits in leaderboard_dict.items():
        try:
            score = bin(int(bits, 2)).count("1")
            scores.append((name, score))
        except ValueError:
            print(f"Skipping invalid bitstring for {name}: {bits}")
    scores.sort(key=lambda x: (-x[1], x[0]))
    print("\n\n\n Top 10 PROVES Explorers:")
    print("-----------------------------")
    for rank, (name, score) in enumerate(scores[:10], start=1):
        print(f"{rank:2d}. {name:12} | {score} booths visited")
    print("-----------------------------\n\n\n")


def update_distinct_leaderboard(name, sender_bytes):
    # print("Sender Callsign: ", name)
    # print("Sender Bytes", sender_bytes)
    sender_bits = sender_bytes.decode()
    filepath = "sd/leaderboard.json"
    with open(filepath, "r") as file:
        try:
            leaderboard_dict = json.load(file)
        except ValueError:
            leaderboard_dict = {}
    current_bits = leaderboard_dict.get(name, "0" * len(sender_bits))
    current_int = int(current_bits, 2)
    sender_int = int(sender_bits, 2)
    updated_int = current_int | sender_int
    updated_bits = bin(updated_int)[2:]  # remove '0b' prefix
    # pad with leading zeros if needed
    updated_bits = "0" * (len(sender_bits) - len(updated_bits)) + updated_bits
    leaderboard_dict[name] = updated_bits
    # print("new dict", leaderboard_dict)
    try:
        with open(filepath, "w") as file:
            json.dump(leaderboard_dict, file)
    except ValueError:
        print("Failed to write leaderboard data:")
    return leaderboard_dict[name]


def display_leaderboard_status_from_name(name):
    try:
        with open("sd/leaderboard.json", "r") as file:
            leaderboard_dict = json.load(file)
    except ValueError:
        print("Failed to read leaderboard data:")
        return
    leader_bits = leaderboard_dict.get(name)
    if leader_bits is None:
        print(f"No progress found for {name}.")
        return
    booths_selected, selected = display_leader_status(leader_bits)
    display_message(booths_selected, selected)


def display_leader_status(leader_bits):
    selected = [item for item, bit in zip(key_order, leader_bits) if bit == "1"]
    booths_visited = bin(int(leader_bits, 2)).count("1")
    booths_remaining = len(key_order) - booths_visited
    return booths_remaining, selected


def display_message(booths_remaining, selected):
    if booths_remaining == 0:
        print("You have visited all the booths!!! Come claim your prize!")
        print_cubesat()
    else:
        print(f"Congratulations! You have visited {', '.join(selected)}.")
        print(f"You still have {booths_remaining} booths left to visit!")


def print_cubesat():
    cubesat = r"""
                      \
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
/
    """
    print(cubesat)


def test_sd():
    """Test SD card functionality and file operations."""
    print(f"Current directory contents: {os.listdir()}")
    print("___________")

    try:
        os.mkdir("sd/new_folder")
        print(f"SD directory contents: {os.listdir('sd')}")
    except OSError as e:
        print(f"Error creating directory: {e}")

    print("_______________")

    try:
        with open("boot_out.txt", "r") as file:
            print(file.read())
    except ValueError:
        print("boot_out.txt not found")
    except Exception as e:
        print(f"Error reading boot_out.txt: {e}")


listen_display()
