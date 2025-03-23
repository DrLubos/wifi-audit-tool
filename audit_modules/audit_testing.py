import enum
from itertools import combinations
import time
import haversine
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


class TestResult(enum.Enum):
	OK = "Test passed"
	SAME_MAC = "Device has the same MAC address as the tested one"
	SAME_SSID = "Device has the same SSID as the tested one"
	NO_ENCRYPTION = "Device has no encryption"
	WEP_ENCRYPTION = "Device has WEP encryption"
	GPS_DISTANCE = "Device are too far apart"
	NO_GPS = "Device has no GPS coordinates"


# Global flag and variable to track test execution.
TESTING_RUNNING = False
CURRENT_TEST = None

# Global database variables (will be set by test() when database is initialized).
CONN = None
CURSOR = None

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())


def test():
	global TESTING_RUNNING, CURRENT_TEST, CONN, CURSOR
	TESTING_RUNNING = True
	CURRENT_TEST = 0
	# Database needs to be initialized here because kismet is not running yet when the module is imported.
	from db_handler import get_database_handler
	db_handler = get_database_handler()
	CONN = db_handler.get_conn()
	CURSOR = db_handler.get_cursor()
	test_all()
	CURRENT_TEST = 0
	TESTING_RUNNING = False


def log_unique_test(device_id, test_type, test_result, description):
	"""
	Insert a test record only if a record for the same device_id, test_type, and test_result does not already exist.
	"""
	"""
	This logging method may seem controversial, but given our expected scale (not more than 5k devices),
	querying the database for each test ensures consistency without the overhead and complexity of
	maintaining an in-memory cache of all test records using a dictionary or similar structure.
	"""
	if CONN is None or CURSOR is None:
		LOGGER.error("Database not initialized for MAC testing.")
		return
	CURSOR.execute(
		"SELECT 1 FROM tests WHERE device_id = ? AND testType = ? AND testResult = ?",
		(device_id, test_type, test_result)
	)
	if CURSOR.fetchone() is None:
		CURSOR.execute(
			"INSERT INTO tests (device_id, testType, testResult, description) VALUES (?, ?, ?, ?)",
			(device_id, test_type, test_result, description)
		)


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

	try:
		LOGGER.info("Starting SSID test.")
		test_ssid()
		time.sleep(1)
	except Exception as e:
		LOGGER.error(f"Error during SSID test: {e}")

	try:
		LOGGER.info("Starting Encryption test.")
		test_encryption()
		time.sleep(1)
	except Exception as e:
		LOGGER.error(f"Error during Encryption test: {e}")

	try:
		LOGGER.info("Starting GPS test.")
		test_gps()
		time.sleep(1)
	except Exception as e:
		LOGGER.error(f"Error during GPS test: {e}")

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
	CURSOR.execute(
		"SELECT mac_address, COUNT(*) as cnt FROM devices GROUP BY mac_address HAVING cnt >= 2"
	)
	duplicates = CURSOR.fetchall()
	if not duplicates:
		return

	for dup in duplicates:
		mac, count = dup
		# For each duplicate, log each device if not already logged.
		CURSOR.execute("SELECT ID FROM devices WHERE mac_address = ?", (mac,))
		device_ids = CURSOR.fetchall()
		for device_id_tuple in device_ids:
			device_id = device_id_tuple[0]
			log_unique_test(
				device_id,
				TestType.MAC.value,
				TestResult.SAME_MAC.name,
				TestResult.SAME_MAC.value
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

	# Group devices by SSID and count them.
	CURSOR.execute(
		"SELECT ssid, COUNT(*) as cnt FROM devices GROUP BY ssid HAVING cnt >= 2"
	)
	duplicates = CURSOR.fetchall()
	if not duplicates:
		return

	for duplicate in duplicates:
		ssid, count = duplicate
		if not ssid:
			continue
		# Retrieve device ID and MAC address for devices with this SSID.
		CURSOR.execute("SELECT ID, mac_address FROM devices WHERE ssid = ?", (ssid,))
		device_records = CURSOR.fetchall()
		# Build a set of unique MAC addresses.
		mac_set = {record[1] for record in device_records}
		# Only if there are at least two different MAC addresses, log the test.
		if len(mac_set) > 1:
			for record in device_records:
				device_id, _ = record
				log_unique_test(
					device_id,
					TestType.SSID.value,
					TestResult.SAME_SSID.name,
					TestResult.SAME_SSID.value
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

	CURSOR.execute("SELECT ID, encryption FROM devices")
	devices = CURSOR.fetchall()
	for device in devices:
		device_id, encryption = device
		encryption_val = encryption if encryption else ""
		# Determine test result based on encryption string.
		if not encryption_val or encryption_val.lower() == "none":
			result = TestResult.NO_ENCRYPTION
			description = TestResult.NO_ENCRYPTION.value
		elif "WEP" in encryption_val.upper():
			result = TestResult.WEP_ENCRYPTION
			description = TestResult.WEP_ENCRYPTION.value
		else:
			result = TestResult.OK
			description = TestResult.OK.value
		# Log only if an issue is found.
		if result == TestResult.NO_ENCRYPTION or result == TestResult.WEP_ENCRYPTION:
			log_unique_test(
				device_id,
				TestType.ENCRYPTION.value,
				result.name,
				description
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

	CURSOR.execute("SELECT ID, latitude_avg, longitude_avg FROM devices")
	devices = CURSOR.fetchall()
	for device in devices:
		device_id, gps_lat, gps_lon = device
		# Log if GPS coordinates are missing.
		if not gps_lat or not gps_lon:
			log_unique_test(
				device_id,
				TestType.GPS.value,
				TestResult.NO_GPS.name,
				TestResult.NO_GPS.value
			)
		else:
			perform_gps_test(TestType.GPS_MAC, "mac_address")
			perform_gps_test(TestType.GPS_SSID, "ssid")


def perform_gps_test(test_type: TestType, group_by: str):
	global CURRENT_TEST
	CURRENT_TEST = test_type.value
	if CURSOR is None:
		LOGGER.error("Database not initialized for GPS testing.")
		return
	# SELECT * FROM devices WHERE group_by IN (SELECT group_by FROM devices GROUP BY group_by HAVING COUNT(*) > 1);
	query = f"SELECT {group_by}, latitude_avg, longitude_avg FROM devices WHERE {group_by} IN (SELECT {group_by} FROM devices GROUP BY {group_by} HAVING COUNT(*) > 1)"
	CURSOR.execute(query)
	devices = CURSOR.fetchall()
	for device in devices:
		device_id, gps_lat, gps_lon = device
		# Log if GPS coordinates are missing.
		if not gps_lat or not gps_lon:
			continue
		for x in combinations(devices, 2):
			if test_gps_distance(x[0][1:], x[1][1:]):
				description = "[{}] and [{}] are too far apart".format(x[0][0], x[1][0])
				description += TestResult.GPS_DISTANCE.value
				log_unique_test(
					device_id,
					test_type.value,
					TestResult.GPS_DISTANCE.name,
					description
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
