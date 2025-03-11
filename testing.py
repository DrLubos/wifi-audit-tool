import enum
import scan
import sqlite3
import logging
import logger
import time
import scan
from threading import Thread
from datetime import datetime
from itertools import combinations
from tests.TestResult import TestResult
from tests import GPS_test, Encryption_test, aircrack
from tests.WiFiConnect import connection

LOGGER = logging.getLogger(__name__)
logger.setup_logger(LOGGER)

DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
TESTED_DEVICES = {}  # (device_id, test_type) -> (result, last_test_timestamp)
LOW_SIGNAL_BOUND = -20
MAX_SIGNAL_DIFFERENCE = 5


# Enumeration of all types of tests.
class TestType(enum.Enum):
    SSID_CHECK = 1
    MAC_CHECK = 2
    ENCRYPTION_CHECK = 3
    GPS_SSID_CHECK = 4
    GPS_MAC_CHECK = 5
    AIRCRACK_FAST = 6
    AIRCRACK_LONG = 7
    WIFI_CONNECT_CHECK = 8


def getActualDateAndTime():
    now = datetime.now()
    # dd/mm/YY H:M:S
    dt_string = now.strftime(DATE_FORMAT)
    return dt_string


def init_testing_module():
    conn = sqlite3.connect(
        scan.KISMET_DIR + scan.get_last_kismet_database().split('.')[0] + ".sqlite3")
    create_testing_table(conn)
    create_tested_devices_dict(conn)
    conn.close()


def create_testing_table(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS tests (ID INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "Device REFERENCES ownTableOfWifiAP, TestType VARCHAR(255), TestResult INTEGER,"
                 " ResultDescription VARCHAR(255), TimeStamp DATETIME)")
    conn.commit()


def create_tested_devices_dict(conn):
    """ Cache all the devices that were tested."""
    result = conn.execute("SELECT Device, TestType, TestResult, max(TimeStamp) FROM tests "
                          "GROUP BY Device, TestType")
    for r in result.fetchall():
        TESTED_DEVICES[(r[0], r[1])] = (r[2], r[3])


def get_devices_without_check(test_type):
    """
        Retrieves and returns a list of devices which should not be check by a specified test_type.
    """
    recheck_time = scan.SETUP[2]
    now = datetime.now()
    return tuple(
        (d1[0] for d1, d2 in TESTED_DEVICES.items()
            if d1[1] == test_type
            and d2[0] == TestResult.OK.value
            and (now - datetime.strptime(d2[1], DATE_FORMAT)).seconds <= recheck_time))


def check_ssid():
    """
        Tests whether two different devices have similar SSID
    """
    test_type = TestType.SSID_CHECK.name
    devices_not_check = get_devices_without_check(test_type)

    conn = sqlite3.connect(
        scan.KISMET_DIR + scan.get_last_kismet_database().split('.')[0] + ".sqlite3")
    cursor = conn.cursor()

    devices_num = cursor.execute("SELECT count(*) from ownTableOfWifiAP").fetchall()
    if len(devices_not_check) == devices_num[0][0]:
        LOGGER.info("Skipping SSID tests")
        conn.close()
        return

    devices_str = str(devices_not_check) if len(devices_not_check) != 1 else '(%d)' % devices_not_check[0]

    # Search for devices with equal SSID but different MAC addresses
    cursor.execute(
        "SELECT a.* from ownTableOfWifiAP a join "
        "(Select SSID from ownTableOfWifiAP where ID NOT IN %s "
        "group by SSID having count(*) > 1 ) b ON a.SSID = b.SSID" % devices_str)

    problem_devices = []
    for x in cursor.fetchall():
        problem_devices.append(x[0])
        record_test(cursor, x[0], test_type, TestResult.SAME_SSID.value,
                    "SSID '%s' has two different MAC addresses" % x[4])

    cursor.execute("SELECT * from ownTableOfWifiAP WHERE ID NOT IN %s" % devices_str)
    for x in cursor.fetchall():
        if x[0] in problem_devices:
            continue

        record_test(cursor, x[0], test_type, TestResult.OK.value, "")

    conn.commit()
    conn.close()


def check_wpa2():
    devices_not_check = get_devices_without_check(TestType.ENCRYPTION_CHECK.name)
    conn = sqlite3.connect(scan.KISMET_DIR + scan.get_last_kismet_database().split('.')[0] + ".sqlite3")
    cursor = conn.cursor()

    devices_num = cursor.execute("SELECT count(*) from ownTableOfWifiAP").fetchall()
    if len(devices_not_check) == devices_num[0][0]:
        LOGGER.info("Skipping All SSID tests")
        conn.close()
        return

    devices_str = str(devices_not_check) if len(devices_not_check) != 1 else '(%d)' % devices_not_check[0]

    cursor.execute("SELECT * FROM ownTableOfWifiAP WHERE ID NOT IN %s" % str(devices_str))

    for dev in cursor.fetchall():
        record_wpa_test(dev, cursor)

    conn.commit()
    conn.close()


def record_wpa_test(dev, cursor):
    test_result = Encryption_test.perform_test(dev)
    # description = '' if test_result is TestResult.OK \
    #     else 'AP "%s" does not have WPA2 encryption. It is recommended using WPA2.' % (dev[4],)
    description = '' if test_result is TestResult.OK \
        else 'AP "%s" dos not have any encryption. It is strongly recommended to have an encryption.'%(dev[4],) if test_result is TestResult.OPEN \
        else 'AP "%s" does not have WPA2 encryption. It is recommended using WPA2.' % (dev[4],)
    record_test(cursor, dev[0], TestType.ENCRYPTION_CHECK.name, test_result.value, description)


def check_mac_address():
    """
        Tests whether two different devices have similar MAC address.
    """
    devices_not_check = get_devices_without_check(TestType.MAC_CHECK.name)
    conn = sqlite3.connect(
        scan.KISMET_DIR + scan.get_last_kismet_database().split('.')[0] + ".sqlite3")
    cursor = conn.cursor()

    devices_num = cursor.execute("SELECT count(*) from ownTableOfWifiAP").fetchall()
    if len(devices_not_check) == devices_num[0][0]:
        LOGGER.info("Skipping MAC tests")
        conn.close()
        return

    cursor.execute(
        "SELECT a.* from ownTableOfWifiAP a join "
        "(Select MACaddress from ownTableOfWifiAP group by MACaddress having count(*) > 1 ) b "
        "ON a.MACaddress  = b.MACaddress ")

    problem_devices = []
    for x in cursor.fetchall():
        problem_devices.append(x[0])
        record_test(cursor, x[0], TestType.MAC_CHECK.name,
                    TestResult.SAME_MAC.value, 'MAC address "%s" has two different SSID' % (x[1]))

    devices_str = str(devices_not_check) if len(devices_not_check) != 1 else '(%d)' % devices_not_check[0]

    cursor.execute("SELECT * from ownTableOfWifiAP WHERE ID NOT IN %s" % str(devices_str))
    for x in cursor.fetchall():
        if x[0] in problem_devices:
            continue
        record_test(cursor, x[0], TestType.MAC_CHECK.name, TestResult.OK.value, '')

    conn.commit()
    conn.close()


def check_gps():
    conn = sqlite3.connect(
        scan.KISMET_DIR + scan.get_last_kismet_database().split('.')[0] + ".sqlite3")
    cursor = conn.cursor()

    start_gps_test(cursor, TestType.GPS_SSID_CHECK, 'SSID')
    start_gps_test(cursor, TestType.GPS_MAC_CHECK, 'MACaddress')

    conn.commit()
    cursor.close()
    conn.close()


def start_gps_test(cursor, test_type: TestType, group_by: str):
    """
        Tests whether devices with similar SSID are located too far from each other.
    """
    devices_not_check = get_devices_without_check(test_type.name)

    devices_num = cursor.execute("SELECT sum(count) from "
                                 "(SELECT count(*) count FROM ownTableOfWifiAP "
                                 "GROUP BY ? HAVING count(*) > 1)", (group_by,)).fetchall()
    if len(devices_not_check) == devices_num[0][0]:
        LOGGER.info("Skipping GPS tests")
        return

    cursor.execute("SELECT ID, Coordinates FROM ownTableOfWifiAP t1 "
                   "JOIN (SELECT %s FROM ownTableOfWifiAP GROUP BY %s HAVING count(*) > 1) t2 "
                   "ON t1.%s == t2.%s" % (group_by, group_by, group_by, group_by))

    for x in combinations(cursor.fetchall(), 2):
        if x[0][0] in devices_not_check or x[1][0] in devices_not_check:
            continue
        result = GPS_test.perform_test(x[0][1], x[1][1])
        description = '' if result == TestResult.OK \
            else 'Devices with equal %ss are located too far from each other.' % group_by
        record_test(cursor, x[0][0], test_type.name, result.value, description)
        record_test(cursor, x[1][0], test_type.name, result.value, description)

def start_fast_aircrack():
	start_aircrack('tests/data/hack/passwords_small.txt', TestType.AIRCRACK_FAST)

aircrack_thread = Thread()
def start_long_aircrack():
    """
        Performs a long aircrack test.
        The test is performed in another test, so it runs parallel with the main loop.
    """
    global aircrack_thread

    if aircrack_thread.is_alive():  # If the test is still running don't create a new thread.
        return

    aircrack_thread = Thread(target=start_aircrack,
                             args=('tests/data/hack/passwords_large.txt', TestType.AIRCRACK_LONG))
    aircrack_thread.start()


def start_aircrack(passwords_path, test_type: TestType):
    """
        Tries to crack an AP with the usage of aircrack-ng.
    """
    devices_not_check = get_devices_without_check(test_type.name)
    conn = sqlite3.connect(scan.KISMET_DIR + scan.get_last_kismet_database().split('.')[0] + ".sqlite3")
    cursor = conn.cursor()

    devices_num = cursor.execute("SELECT count(*) from ownTableOfWifiAP").fetchall()
    if len(devices_not_check) == devices_num[0][0]:
        LOGGER.info("Skipping AirCrack tests")
        conn.close()
        return

    devices_str = str(devices_not_check) if len(devices_not_check) != 1 else '(%d)' % devices_not_check[0]

    result = cursor.execute("SELECT * from ownTableOfWifiAP WHERE ID NOT IN %s" % str(devices_str))
    for d in result.fetchall():
        # Moze nastat ze sila signalu je napisana ako 0 alebo '' (ziadna) program spadne
        if d[6] == '':
            signal_strength = 0
        else:
            signal_strength = int(d[6])
        
        if signal_strength > LOW_SIGNAL_BOUND:
            # Skip the test if signal strength is too low
            continue

        if test_type == TestType.AIRCRACK_LONG:
            # Check if signal strength has not changed for more than a specified threshold.
            time.sleep(15)
            current_signal = cursor.execute("SELECT SignalStrength "
                                            "from ownTableOfWifiAP "
                                            "WHERE ID == ?", (d[0],)).fetchone()[0]
            if current_signal > LOW_SIGNAL_BOUND or abs(current_signal - signal_strength) > MAX_SIGNAL_DIFFERENCE:
                continue

        result = aircrack.perform_test((d[1], d[3], d[4], passwords_path))
        if result[0] is TestResult.OK:
            description = ''
        elif result[0] is TestResult.AIRCRACK_NOT_PERFORMED:
            description = "Test wasn't performed: " + result[1]
        else:
            description = "Aircrack cracked the AP '%s'. The password is '%s'" % (d[4], result[1])
        
        record_test(cursor, d[0], test_type.name, result[0].value, description)

        if result[0] is TestResult.AIRCRACK_SUCCESS:
            # Try to connect to the cracked AP
            #connection_result = connection(d[4], result[1], "wlan0")
            connection_result = connection(d[4], result[1], scan.SETUP[5])
            record_test(cursor, d[0], TestType.WIFI_CONNECT_CHECK.name, connection_result[1].value, connection_result[0])

        conn.commit()
    cursor.close()
    conn.close()

def checkConnection():
    devices_not_check = get_devices_without_check(TestType.WIFI_CONNECT_CHECK.name)
    conn = sqlite3.connect(scan.KISMET_DIR + scan.get_last_kismet_database().split('.')[0] + ".sqlite3")
    cursor = conn.cursor()

    devices_num = cursor.execute('SELECT count(*) from ownTableOfWifiAP where Encryption = "Open"').fetchall()
    if len(devices_not_check) == devices_num[0][0]:
        LOGGER.info("Skipping WiFi Connection tests")
        conn.close()
        return

    devices_str = str(devices_not_check) if len(devices_not_check) != 1 else '(%d)' % devices_not_check[0]
    result = cursor.execute('SELECT * from ownTableOfWifiAP WHERE Encryption = "Open" AND ID NOT IN %s' % str(devices_str))
    for d in result.fetchall():
        #connection_result =connection(d[4],"","wlan0")
        connection_result = connection(d[4], "", scan.SETUP[5])
        record_test(cursor, d[0], TestType.WIFI_CONNECT_CHECK.name, connection_result[1].value, connection_result[0])

    conn.commit()
    cursor.close()
    conn.close()


def record_test(cursor, device_id, test_type, test_result, description):
    """
        Stores a test result into the database.
    """
    cursor.execute("INSERT INTO tests (Device, TestType, TestResult, ResultDescription, TimeStamp)"
                   "VALUES (?, ?, ?, ?, ?)",
                   (device_id, test_type, test_result, description, getActualDateAndTime()))
