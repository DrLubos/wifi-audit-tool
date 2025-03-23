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
	# Database needs to be initialized here because kismet is not running yet when the module is imported.
	from db_handler import get_database_handler
	CONN = get_database_handler().get_conn()
	CURSOR = get_database_handler().get_cursor()
	send_to_kismet_api = get_database_handler().send_to_kismet_api
	parse_devices()
	PARSER_RUNNING = False


def stop_parser():
	global PARSER_RUNNING
	PARSER_RUNNING = False


def get_parser_status():
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
	gps_response = send_to_kismet_api("/gps/location.json")
	gps_response = gps_response["kismet.common.location.geopoint"]
	current_location = tuple(gps_response)

	try:
		with CONN:
			for device in data:
				mac_address = str(device["kismet.device.base.macaddr"])
				manufacturer = str(device["kismet.device.base.manuf"])
				ssid_channel = str(device["kismet.device.base.channel"])
				ssid = str(device["kismet.device.base.name"])
				encryption = str(device["kismet.device.base.crypt"])
				signal_strength = str(
					device["kismet.device.base.signal"]["kismet.common.signal.min_signal"])

				# Filter out APs that should not be processed.
				if not filter_AP_from_file(ssid):
					continue

				# Check if the device already exists.
				query = "SELECT ID FROM devices WHERE mac_address = ? AND ssid_channel = ? AND ssid = ?"
				CURSOR.execute(query, (mac_address, ssid_channel, ssid))
				result = CURSOR.fetchone()
				if result:
					device_id = result[0]
				else:
					# Insert new device record.
					query_insert = (
						"INSERT INTO devices (mac_address, manufacturer, ssid_channel, ssid, encryption, signal_strength) "
						"VALUES (?, ?, ?, ?, ?, ?)"
					)
					CURSOR.execute(query_insert, (mac_address, manufacturer,
                                            ssid_channel, ssid, encryption, signal_strength))
					device_id = CURSOR.lastrowid

				# Insert GPS coordinates record for the device.
				if current_location != (0, 0):
					query_gps_insert = "INSERT INTO gps_coordinates (device_id, latitude, longitude) VALUES (?, ?, ?)"
					CURSOR.execute(query_gps_insert, (device_id,
                                            current_location[0], current_location[1]))

				# Calculate the average latitude and longitude for the device.
				query_avg = "SELECT AVG(latitude), AVG(longitude) FROM gps_coordinates WHERE device_id = ?"
				CURSOR.execute(query_avg, (device_id,))
				avg_coords = CURSOR.fetchone()
				if avg_coords:
					avg_lat, avg_lon = avg_coords
					# Update the devices table with the average coordinates.
					update_query = "UPDATE devices SET latitude_avg = ?, longitude_avg = ? WHERE ID = ?"
					CURSOR.execute(update_query, (avg_lat, avg_lon, device_id))
	except Exception as e:
		LOGGER.exception(f"Error while filling database: {e}")


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
	"""
	scan_type = CONFIG["scan_type"]
	if scan_type == 1:
		return "whiteList.txt"
	elif scan_type == 2:
		return "blackList.txt"
	elif scan_type == 3:
		return "whiteBlackList.txt"
	return "None"
