import json
import os
import time

# TO DO: Refactor to use packet manager

# Constants for communication commands
SEND_LEADERBOARD = "send_leaderboard"
SEND_PING = "ping"
UPDATE_LEADERBOARD = "update_leaderboard"
SEND_LEADERBOARD_MAIN = "send_leaderboard_main"
RETURN_LEADERBOARD_MAIN = "return_leaderboard_main"


def nominal_power_loop(
    logger, uhf_packet_manager, sleep_helper, config, callsigns=None
):
    """
    Execute the nominal power loop for pinging multiple cubesats using callsigns.

    Args:
        logger: Logger instance for logging messages
        uhf_packet_manager: Packet manager for UHF communication
        sleep_helper: Helper for safe sleep operations
        config: Configuration object containing radio settings
        callsigns: List of callsigns to ping (defaults to config.radio.default_callsigns)
    """
    if callsigns is None:
        callsigns = config.radio.default_callsigns

    message = {}

    for callsign in callsigns:
        # Send a ping to a single cubesat
        logger.info(f"Pinging {callsign}...")
        message["current_time"] = time.monotonic()
        message["callsign"] = callsign
        message["command"] = SEND_PING
        encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")

        if not uhf_packet_manager.send(encoded_message):
            logger.warning(f"Failed to send ping to {callsign}")
            sleep_helper.safe_sleep(1)  # Wait before trying the next one
            continue

        # Listen for an immediate pong response
        logger.info(f"Listening for pong from {callsign} for 10 seconds.")
        received_message = uhf_packet_manager.listen(10)

        if received_message:
            try:
                decoded_message = json.loads(received_message.decode("utf-8"))
                sender_callsign = decoded_message.get("callsign")
                command = decoded_message.get("command")

                if command == "pong" and sender_callsign == callsign:
                    logger.info(f"Success! Received pong from {sender_callsign}.")
                else:
                    logger.warning(f"Received unexpected message: {decoded_message}")
            except (ValueError, UnicodeError) as e:
                logger.error("Could not process received message", e)
        else:
            logger.warning(f"No response from {callsign} within the time limit.")

        # Wait before contacting the next satellite
        logger.debug("Waiting 5 seconds before contacting next satellite.")
        sleep_helper.safe_sleep(5)


def send_leaderboard_main(
    logger,
    uhf_packet_manager,
    sleep_helper,
    config,
    my_callsign=None,
    target_callsigns=None,
):
    logger.debug("have been asked to send stuff as main")

    if my_callsign is None:
        my_callsign = config.radio.license

    if target_callsigns is None:
        target_callsigns = config.radio.default_callsigns
    # make sure main is as updated as it can be by having it ping all the devices
    send_leaderboard_power_loop(
        logger, uhf_packet_manager, sleep_helper, config, target_callsigns
    )
    try:
        with open("sd/leaderboard.json", "r") as file:
            current_leaderboard = json.load(file)
    except ValueError:
        current_leaderboard = {}
    response_message = {
        "current_time": time.monotonic(),
        "callsign": my_callsign,
        "command": RETURN_LEADERBOARD_MAIN,
        "leaderboard": current_leaderboard,
    }
    encoded_response = json.dumps(response_message, separators=(",", ":")).encode(
        "utf-8"
    )
    print(f"Sending leaderboard: {encoded_response}")
    sleep_helper.safe_sleep(1)
    uhf_packet_manager.send(encoded_response)


def send_leaderboard_power_loop(
    logger, uhf_packet_manager, sleep_helper, config, callsigns=None
):
    """
    Execute the leaderboard sending loop through all the callsigns.

    Args:
        logger: Logger instance for logging messages
        uhf_packet_manager: Packet manager for UHF communication
        sleep_helper: Helper for safe sleep operations
        config: Configuration object containing radio settings
        callsigns: List of callsigns to contact (defaults to config.radio.default_callsigns)
    """
    if callsigns is None:
        callsigns = config.radio.default_callsigns

    message = {}
    for callsign in callsigns:
        logger.info(f"Requesting leaderboard from {callsign}...")
        message["current_time"] = time.monotonic()
        message["callsign"] = callsign
        message["command"] = SEND_LEADERBOARD
        encoded_message = json.dumps(message, separators=(",", ":")).encode("utf-8")
        if not uhf_packet_manager.send(encoded_message):
            logger.warning(f"Failed to send leaderboard request to {callsign}")
            sleep_helper.safe_sleep(1)
            continue
        logger.info(f"Listening for response from {callsign} for 10 seconds.")
        received_message = uhf_packet_manager.listen(10)
        if received_message:
            try:
                decoded_message = json.loads(received_message.decode("utf-8"))
                logger.info(f"Decoded message is: {decoded_message}")
                logger.info(f"Keys are: {decoded_message.keys()}")
                payload = decoded_message.get("leaderboard")
                logger.info(f"PAYLOAD is: {payload}")
                if not payload:
                    logger.warning(f"No leaderboard found in response from {callsign}")
                    continue
                # Extract leaderboard and update
                else:
                    update_leaderboard_dict(payload)
            except (ValueError, UnicodeError):
                logger.error("Could not process received message", exc_info=True)
        else:
            logger.warning(f"No response from {callsign} within the time limit.")

        logger.debug("Waiting 5 seconds before contacting next satellite.")
        sleep_helper.safe_sleep(5)


def listener_nominal_power_loop(
    logger, uhf_packet_manager, sleep_helper, config, my_callsign=None
):
    if my_callsign is None:
        my_callsign = config.radio.license

    received_message = uhf_packet_manager.listen(5)
    if received_message:
        try:
            decoded_message = json.loads(received_message.decode("utf-8"))
            logger.info(f"Received message: {decoded_message}")
            sender_callsign = decoded_message.get("callsign")
            if sender_callsign == my_callsign or sender_callsign == "any":
                logger.info(f"Received message: its for me! {my_callsign}")
                command = decoded_message.get("command")
                if command == SEND_PING:
                    logger.info(f"Received ping from {sender_callsign}")
                    response_message = {
                        "current_time": time.monotonic(),
                        "callsign": my_callsign,
                        "command": "pong",
                    }
                    encoded_response = json.dumps(
                        response_message, separators=(",", ":")
                    ).encode("utf-8")
                    sleep_helper.safe_sleep(1)
                    uhf_packet_manager.send(encoded_response)
                elif command == SEND_LEADERBOARD:
                    send_leaderboard(
                        sleep_helper, uhf_packet_manager, config, my_callsign
                    )
                elif command == UPDATE_LEADERBOARD:
                    name = decoded_message.get("name")
                    logger.info(f"Recieved Command: Update leaderboard with {name}")
                    update_leaderboard(name)
                elif command == SEND_LEADERBOARD_MAIN:
                    send_leaderboard_main(
                        logger,
                        uhf_packet_manager,
                        sleep_helper,
                        config,
                        my_callsign,
                        config.radio.default_callsigns,
                    )
        except (ValueError, UnicodeError):
            logger.error("Failed to decode message")


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
    except ValueError:
        print("boot_out.txt not found")
    except Exception as e:
        print(f"Error reading boot_out.txt: {e}")


def update_leaderboard_dict(leaderboard_dict):
    try:
        with open("sd/leaderboard.json", "r") as file:
            current_leaderboard = json.load(file)
    except ValueError:
        print("No leaderboard data available, creating new one")
        current_leaderboard = {}

    for key, value in leaderboard_dict.items():
        if key in current_leaderboard.keys():
            current_leaderboard[key] = current_leaderboard[key] + value
        else:
            current_leaderboard[key] = value

    print("new dict", current_leaderboard)
    try:
        with open("sd/leaderboard.json", "w") as file:
            json.dump(current_leaderboard, file)
    except ValueError:
        print("Failed to write leaderboard data:")


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
    except OSError:
        # Create new leaderboard if file doesn't exist or is invalid
        print("Error finding leaderboard")
        return
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
    except ValueError:
        print("No leaderboard data available")
        return

    sorted_leaderboard = sorted(
        current_leaderboard.items(), key=lambda kv: (-kv[1], kv[0])
    )

    for i, (name, score) in enumerate(sorted_leaderboard, 1):
        print(f"{i}. {name}: {score}")


def send_leaderboard(sleep_helper, uhf_packet_manager, config, my_callsign=None):
    """
    Send the current leaderboard data via radio.

    Args:
        sleep_helper: Helper for safe sleep operations
        uhf_packet_manager: Packet manager for UHF communication
        config: Configuration object containing radio settings
        my_callsign: Callsign of this cubesat (defaults to config.radio.license)
    """
    if my_callsign is None:
        my_callsign = config.radio.license

    try:
        with open("sd/leaderboard.json", "r") as file:
            current_leaderboard = json.load(file)
    except ValueError:
        print("Error starting leaderboard: Value error")
        current_leaderboard = {}

    response_message = {
        "current_time": time.monotonic(),
        "callsign": my_callsign,
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
