import json
import os
import time

# Constants for communication commands
SEND_LEADERBOARD = "send_leaderboard"
SEND_PING = "ping"
CUBESAT_ID = "Listener1"  # Updated to match main.py configuration
UPDATE_LEADERBOARD = "update_leaderboard"

# Default cube IDs for communication
DEFAULT_CUBE_IDS = ["Listener1", "Listener2", "Listener3"]


def nominal_power_loop(
    logger, uhf_packet_manager, sleep_helper, cube_ids=DEFAULT_CUBE_IDS
):
    """
    Execute the nominal power loop for pinging multiple cubesats.

    Args:
        logger: Logger instance for logging messages
        uhf_packet_manager: Packet manager for UHF communication
        sleep_helper: Helper for safe sleep operations
        cube_ids: List of cube IDs to ping
    """
    message = {}

    for cube_id in cube_ids:
        # Send a ping to a single cubesat
        logger.info(f"Pinging {cube_id}...")
        message["current_time"] = time.monotonic()
        message["cube_id"] = cube_id
        message["command"] = SEND_PING
        encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")

        if not uhf_packet_manager.send(encoded_message):
            logger.warning(f"Failed to send ping to {cube_id}")
            sleep_helper.safe_sleep(1)  # Wait before trying the next one
            continue

        # Listen for an immediate pong response
        logger.info(f"Listening for pong from {cube_id} for 10 seconds.")
        received_message = uhf_packet_manager.listen(10)

        if received_message:
            try:
                decoded_message = json.loads(received_message.decode("utf-8"))
                sender_id = decoded_message.get("cube_id")
                command = decoded_message.get("command")

                if command == "pong" and sender_id == cube_id:
                    logger.info(f"Success! Received pong from {sender_id}.")
                else:
                    logger.warning(f"Received unexpected message: {decoded_message}")
            except (json.JSONDecodeError, UnicodeError) as e:
                logger.error("Could not process received message", e)
        else:
            logger.warning(f"No response from {cube_id} within the time limit.")

        # Wait before contacting the next satellite
        logger.debug("Waiting 5 seconds before contacting next satellite.")
        sleep_helper.safe_sleep(5)


def send_leaderboard_power_loop(
    logger, uhf_packet_manager, sleep_helper, cube_ids=DEFAULT_CUBE_IDS
):
    """
    Execute the leaderboard sending power loop.

    Args:
        logger: Logger instance for logging messages
        uhf_packet_manager: Packet manager for UHF communication
        sleep_helper: Helper for safe sleep operations
        cube_ids: List of cube IDs to contact
    """
    message = {}

    for cube_id in cube_ids:
        # Send a leaderboard request to a single cubesat
        logger.info(f"Requesting leaderboard from {cube_id}...")
        message["current_time"] = time.monotonic()
        message["cube_id"] = cube_id
        message["command"] = SEND_LEADERBOARD
        encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")

        if not uhf_packet_manager.send(encoded_message):
            logger.warning(f"Failed to send leaderboard request to {cube_id}")
            sleep_helper.safe_sleep(1)
            continue

        # Listen for response
        logger.info(f"Listening for response from {cube_id} for 10 seconds.")
        received_message = uhf_packet_manager.listen(10)

        if received_message:
            try:
                decoded_message = json.loads(received_message.decode("utf-8"))
                # sender_id = decoded_message.get("cube_id")
                print(decoded_message)
            except (json.JSONDecodeError, UnicodeError) as e:
                logger.error("Could not process received message", e)
        else:
            logger.warning(f"No response from {cube_id} within the time limit.")

        # Wait before contacting the next satellite
        logger.debug("Waiting 5 seconds before contacting next satellite.")
        sleep_helper.safe_sleep(5)


def listener_nominal_power_loop(
    logger, uhf_packet_manager, sleep_helper, my_cubesat_id=CUBESAT_ID
):
    """
    Execute the listener nominal power loop for responding to pings.

    Args:
        logger: Logger instance for logging messages
        uhf_packet_manager: Packet manager for UHF communication
        sleep_helper: Helper for safe sleep operations
        my_cubesat_id: ID of this cubesat
    """
    received_message = uhf_packet_manager.listen(5)

    if received_message:
        try:
            decoded_message = json.loads(received_message.decode("utf-8"))
            logger.info(f"Received message: {decoded_message}")

            cubesat_id = decoded_message.get("cube_id")
            if cubesat_id == my_cubesat_id:
                command = decoded_message.get("command")

                if command == SEND_PING:
                    logger.info(f"Received ping from {cubesat_id}")
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

                elif command == SEND_LEADERBOARD:
                    send_leaderboard(sleep_helper, uhf_packet_manager, my_cubesat_id)
                elif command == UPDATE_LEADERBOARD:
                    update_leaderboard(decoded_message.get("name"))
        except (ValueError, UnicodeError) as e:
            logger.error("Failed to decode message", e)


# TO DO: turn this into a real test for our flash memory
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
    except FileNotFoundError:
        print("boot_out.txt not found")
    except Exception as e:
        print(f"Error reading boot_out.txt: {e}")


def update_leaderboard(name):
    """
    Update the leaderboard with a new entry or increment existing entry.

    Args:
        name: Name to add or increment in the leaderboard
    """
    leaderboard_file = "sd/leaderboard.json"

    try:
        # Load existing leaderboard
        with open(leaderboard_file, "r") as file:
            current_leaderboard = json.load(file)
    except FileNotFoundError:
        # Create new leaderboard if file doesn't exist or is invalid
        current_leaderboard = {}

    # Update the leaderboard
    if name not in current_leaderboard:
        current_leaderboard[name] = 1
    else:
        current_leaderboard[name] += 1

    # Save updated leaderboard
    try:
        with open(leaderboard_file, "w") as file:
            json.dump(current_leaderboard, file)
    except Exception as e:
        print(f"Error saving leaderboard: {e}")


def display_leaderboard():
    print("LEADERBOARD:")

    try:
        with open("sd/leaderboard.json", "r") as file:
            current_leaderboard = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No leaderboard data available")
        return

    sorted_leaderboard = sorted(
        current_leaderboard.items(), key=lambda kv: (-kv[1], kv[0])
    )

    for i, (name, score) in enumerate(sorted_leaderboard, 1):
        print(f"{i}. {name}: {score}")


def send_leaderboard(sleep_helper, uhf_packet_manager, my_cubesat_id=CUBESAT_ID):
    """
    Send the current leaderboard data via radio.

    Args:
        sleep_helper: Helper for safe sleep operations
        uhf_packet_manager: Packet manager for UHF communication
        my_cubesat_id: ID of this cubesat
    """
    try:
        with open("sd/leaderboard.json", "r") as file:
            current_leaderboard = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        current_leaderboard = {}

    response_message = {
        "current_time": time.monotonic(),
        "cube_id": my_cubesat_id,
        "command": SEND_LEADERBOARD,
        "leaderboard": current_leaderboard,
    }

    encoded_response = json.dumps(response_message, separators=(",", ":")).encode(
        "utf-8"
    )

    print(f"Sending leaderboard: {encoded_response}")
    sleep_helper.safe_sleep(1)
    uhf_packet_manager.send(encoded_response)

    # Clear the leaderboard after sending
    try:
        with open("sd/leaderboard.json", "w") as file:
            file.write("{}")
    except Exception as e:
        print(f"Error clearing leaderboard: {e}")
