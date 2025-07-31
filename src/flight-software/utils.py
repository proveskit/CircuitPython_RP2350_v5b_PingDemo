
import gc
import json
import os
import time
import json

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


SENDLEADERBOARD = "send_leaderboard"
SENDPING = "ping"
CUBSATID = "Listener"
UPDATE_LEADERBOARD = "update_leaderboard"

def nominal_power_loop(logger, uhf_packet_manager, sleep_helper, cube_ids=["Listener1", "Listener2", "Listener3"]):

        message: dict[str, object] = dict()
        for cube_id in cube_ids:
            if cube_id == my_cubesat_id:
                continue

            # --- 1. Send a ping to a single cubesat ---
            logger.info(f"Pinging {cube_id}...")
            message["current_time"] = time.monotonic()
            message["cube_id"] = cube_id
            message["command"] = PING
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


def send_leaderboard_power_loop(logger, uhf_packet_manager, sleep_helper, cube_ids=["Listener1", "Listener2", "Listener3"]):
        message: dict[str, object] = dict()
        for cube_id in cube_ids:
            # --- 1. Send a ping to a single cubesat ---
            logger.info(f"Pinging {cube_id}...")
            message["current_time"] = time.monotonic()
            message["cube_id"] = cube_id
            message["command"] = SENDLEADERBOARD
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


def listener_nominal_power_loop(logger, uhf_packet_manager, sleep_helper, my_cubesat_id=CUBSATID):

        received_message: bytes | None = uhf_packet_manager.listen(5)

        if received_message:
            try:
                decoded_message = json.loads(received_message.decode("utf-8"))
                logger.info(f"Received message: {decoded_message}")

                cubesat_id = decoded_message.get("cube_id")
                if cubesat_id == my_cubesat_id:
                    command = decoded_message.get("command")
                    if command == PING:
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

                    elif command == SENDLEADERBOARD:
                        send_leaderboard(sleep_helper, uhf_packet_manager)
                    elif command == UPDATE_LEADERBOARD:
                        update_leaderboard(decoded_message.get("name"))
            except (json.JSONDecodeError, UnicodeError) as e:
                logger.error("Failed to decode message", e)



#TO DO: turn this into a real test for our flash memory
def test_sd():
    print(os.listdir())
    print("___________")
    os.mkdir('sd/new_folder')
    print(os.listdir('sd'))
    print("_______________")
    with open('boot_out.txt', 'r') as file:
        print(file.read())

def update_leaderboard(name):
    with open('sd/leaderboard.json', 'r') as file:
        current_leaderboard = json.load(file)
    if name not in current_leaderboard:
        current_leaderboard[name] = 1
    else:
        current_leaderboard[name] = current_leaderboard[name] + 1
    with open('sd/leaderboard.json', 'w') as file:
        json.dump(current_leaderboard, file)    


def display_leaderboard():
    print("LEADERBOARD:")
    with open('sd/leaderboard.json', 'r') as file:
        current_leaderboard = json.load(file)

    sorted_leaderboard = sorted(current_leaderboard.items(), key=lambda kv: (-kv[1], kv[0]))
    i = 0
    for v in sorted_leaderboard:
        i+=1
        print(str(i) + ". " + v[0] + " : " + str(v[1]))

def send_leaderboard(sleep_helper, uhf_packet_manager, my_cubesat_id=CUBSATID):
    with open('sd/leaderboard.json', 'r') as file:
        current_leaderboard = json.load(file)
    message = {}
    encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")
    response_message = {
                            "current_time": time.monotonic(),
                            "cube_id": my_cubesat_id,
                            "command": "pong",
                            "leaderboard": current_leaderboard,
                        }
    encoded_response = json.dumps(response_message, separators=(",", ":")).encode("utf-8")
    print(encoded_response)
    sleep_helper.safe_sleep(1)
    uhf_packet_manager.send(encoded_response)
    #Clear all the old values
    with open('sd/leaderboard.json', 'w') as file:
        file.write("{}")


