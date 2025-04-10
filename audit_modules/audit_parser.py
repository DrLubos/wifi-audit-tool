import json
import re

from config import get_config
from logger import get_logger

CONN = None
CURSOR = None

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG
KISMET_USER = CONFIG_INSTANCE.KISMET_USER
KISMET_PASSWORD = CONFIG_INSTANCE.KISMET_PASSWORD

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

PARSER_RUNNING = False


def parse():
	global PARSER_RUNNING, CONN, CURSOR, send_to_kismet_api
	PARSER_RUNNING = True
	from db_handler import get_database_handler
	CONN = get_database_handler().get_conn()
	CURSOR = get_database_handler().get_cursor()
	send_to_kismet_api = get_database_handler().send_to_kismet_api
	try:
		parse_devices()
	except Exception as e:
		LOGGER.exception(f"Error parsing devices: {e}")

	PARSER_RUNNING = False


def stop_parser():
	global PARSER_RUNNING
	PARSER_RUNNING = False


def get_parser_status():
	"""
	Get the status of the parser.

	Returns:
		bool: True if the parser is running, False otherwise
	"""
	global PARSER_RUNNING
	return PARSER_RUNNING


def parse_devices():
	"""
	Parse the devices from the Kismet API and insert them into the database.
	"""
	if CONN is None or CURSOR is None:
		LOGGER.error("Database CONNection not initialized.")
		return

	data = send_to_kismet_api(
		"/devices/views/phydot11_accesspoints/devices.json")
	if len(data) == 0:
		LOGGER.warning("No data received from Kismet API.")
		return

	with CONN:
		for device in data:
			ssid = str(device["kismet.device.base.name"])
			# Filter out APs that should not be processed.
			if not filter_AP_from_file(ssid):
				continue
			
			if ssid == "WifiAudit":
				continue 

			mac_address = str(device["kismet.device.base.macaddr"])
			manufacturer = str(device["kismet.device.base.manuf"])
			ssid_channel = str(device["kismet.device.base.channel"])
			freq_map = str(device["kismet.device.base.freq_khz_map"])
			# change every ' in freq_map to "
			freq_map = freq_map.replace("'", '"')
			encryption = str(device["kismet.device.base.crypt"])
			device_signal = device["kismet.device.base.signal"]
			if device_signal is not None:
				try:
					average_location = device_signal["kismet.common.signal.peak_loc"]["kismet.common.location.geopoint"]
				except Exception as e:
					LOGGER.error(f"Error parsing average location: {e}")
					average_location = [0.0, 0.0]
			else:
				average_location = [0.0, 0.0]
			# average_location = [19.59914, 49.088724]
			lon_avg = float(average_location[0])
			lat_avg = float(average_location[1])
			if lon_avg == 0.0 and lat_avg == 0.0:
				lon_avg = None
				lat_avg = None

			# Check if the device already exists in table by comparing ssid, mac_address, manufacturer, encryption.
			query = "SELECT ID FROM devices WHERE ssid = ? AND mac_address = ? AND manufacturer = ? AND encryption = ?"
			CURSOR.execute(query, (ssid, mac_address, manufacturer, encryption))
			result = CURSOR.fetchone()
			if result:
				device_id = result[0]  # found device in the table.
				# Update the avg_gps, ssid_channels and frequency_map for the device.
				query_update = "SELECT ssid_channels FROM devices WHERE ID = ?"
				CURSOR.execute(query_update, (device_id,))
				result = CURSOR.fetchone()
				if result:
					ssid_channels = result[0]
					ssid_channel_list = json.loads(ssid_channels) if ssid_channels else []
					if ssid_channel not in ssid_channel_list:
						ssid_channel_list.append(ssid_channel)
						ssid_channel_list = json.dumps(ssid_channel_list)
						update_query = "UPDATE devices SET ssid_channels = ? WHERE ID = ?"
						CURSOR.execute(update_query, (ssid_channel_list, device_id))
				update_query = "UPDATE devices SET frequency_map = ? WHERE ID = ?"
				CURSOR.execute(update_query, (freq_map, device_id))
				update_query = "UPDATE devices SET lat_avg = ?, lon_avg = ? WHERE ID = ?"
				CURSOR.execute(update_query, (lat_avg, lon_avg, device_id))
			else:
				# Insert new device record.
				ssid_channel_list = json.dumps([ssid_channel])
				query_insert = (
					"INSERT INTO devices"
					"(ssid, mac_address, manufacturer, ssid_channels, frequency_map, encryption, lat_avg, lon_avg) "
					"VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
				)
				CURSOR.execute(query_insert, (ssid, mac_address, manufacturer,
							   ssid_channel_list, freq_map, encryption, lat_avg, lon_avg))
				device_id = CURSOR.lastrowid


def filter_AP_from_file(ssid: str) -> bool:
	"""
	Filter APs based on the scan type file.

	Parameters:
		ssid (str): The SSID of the AP to filter.

	Returns:
		bool: True if the AP is allowed, False otherwise.
	"""
	file_name = get_scan_type_file()
	if file_name == "None":
		return True  # No file specified, allow all APs.
	list_path = "config/" + file_name

	with open(list_path, 'r') as fp:
		lines = [line.strip() for line in fp if line.strip()]

	if file_name == 'whiteList.txt':
		# White list: allowed if any pattern matches.
		for pattern in lines:
			if re.match(pattern, ssid):
				return True
		return False

	elif file_name == 'blackList.txt':
		# Black list: blocked if any pattern matches.
		for pattern in lines:
			if re.match(pattern, ssid):
				return False
		return True

	elif file_name == 'whiteBlackList.txt':
		# White-Black list: each line should have two parts separated by "#".
		for line in lines:
			parts = line.split("#", 1)
			if len(parts) != 2:
				continue  # Skip improperly formatted lines.
			white_pattern, black_pattern = parts[0].strip(), parts[1].strip()
			if re.match(white_pattern, ssid):
				# Allow unless it also matches the black pattern.
				if re.match(black_pattern, ssid):
					return False
				else:
					return True
		return False

	return True  # Default allow.


def get_scan_type_file() -> str:
	"""
	Returns the file name of the scan type file.

	Returns:
		str: The file name.
	"""
	scan_type = CONFIG["scan_type"]
	if scan_type == 1:
		return "whiteList.txt"
	elif scan_type == 2:
		return "blackList.txt"
	elif scan_type == 3:
		return "whiteBlackList.txt"
	return "None"
