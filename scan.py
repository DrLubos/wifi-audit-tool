import os
import sqlite3
import json
import re
import subprocess
import time
import logging
import logger

USE_WHITELIST = 0
USE_BLACKLIST = 0
USE_WHITE_BLACKLIST = 0
USE_EMPTYLIST = 0
RECHECK = 10 * 60
MAIN_SLEEP = 5
SETUP = []
# KISMET_DIR = '/home/kali/PycharmProjects/pythonProject/'
KISMET_DIR = "kismet/"

LOGGER = logging.getLogger(__name__)
logger.setup_logger(LOGGER)


def init():
    """
       Read the configuration file and return all the parameters from it.
    """
    with open("config/config.cfg") as cfg:
        while 1:
            line = cfg.readline()
            if line == "":
                break
            var = line.split('=')[0]
            value = line.split('=')[1]
            if var == "IFACE":
                monitoringInterface = value
            elif var == "SCAN_TYPE":
                scanType = int(value)
            elif var == "RECHECK":
                mult = int(value.split('*')[0])
                secs = int(value.split('*')[1])
                recheckTime = mult * secs
            elif var == "MAIN_SLEEP":
                sleep = int(value)
            elif var == "MAX_AP_DISTANCE":
                max_dist = float(value)
            elif var == "IFACE2":
                connect_interface = value

    setupParameters = (monitoringInterface, scanType, recheckTime, sleep, max_dist,connect_interface)
    return setupParameters


# nastavenie wlan0 do monitorovacieho rezimu
def monitoring_mode():
    global SETUP
    SETUP = init()
    monitoringInterface = SETUP[0]
    # os.system("echo kali | sudo -S airmon-ng stop %s" % (monitoringInterface + "mon"));
    # os.system("echo kali | sudo -S airmon-ng start %s" % (monitoringInterface))
    return monitoringInterface + "mon"


# spustenie kismet programu
def kismet_run():
    monitoringInterface = monitoring_mode()
    os.chdir(KISMET_DIR)
    #os.system("kismet -c %s &" % (monitoringInterface))
    #subprocess.Popen("kismet -c %s" % (monitoringInterface), shell=True)
    os.chdir("..")
    add_dummy_wep_device()


def add_dummy_wep_device():
    """
        Add a testing device. It should not be used in production.
    """
    kismet_file = get_last_kismet_database()
    connection = sqlite3.connect(KISMET_DIR + kismet_file.split('.')[0] + ".sqlite3")
    c = connection.cursor()
    r = c.execute("SELECT * FROM ownTableOfWifiAP WHERE MACaddress = '3C:78:43:62:41:80' AND Encryption = 'WEP'")
    if len(r.fetchall()) != 0:
        connection.close()
        return

    c.execute(
        "INSERT INTO ownTableOfWifiAP (MACaddress, Manufacturer, SSIDChannel, SSID, Encryption, SignalStrength, Coordinates)"
        " VALUES ('3C:78:43:62:41:80','Huawei Technologies Ltd','5','Argo-2G','WEP','-82', '48.759424 19.170199')")
    connection.commit()
    connection.close()


def get_last_kismet_database():
    arr_kismet = sorted([x for x in os.listdir(KISMET_DIR) if x.endswith(".kismet")], reverse=True)

    if len(arr_kismet) == 0:
        raise Exception("Kismet file hasn't been found.")

    newestKismetFile = arr_kismet[0]
    return newestKismetFile


def txt_File_To_List():
    """
        Check which filter list should be used and return its name.
    """
    global SETUP
    if SETUP[1] == 1:
        selected_file = 'whiteList.txt'
        LOGGER.info(selected_file)
    elif SETUP[1] == 2:
        selected_file = 'blackList.txt'
        LOGGER.info(selected_file)
    elif SETUP[1] == 3:
        selected_file = 'whiteBlackList.txt'
        LOGGER.info(selected_file)
    else:
        LOGGER.info("Vybral si typ scanovania EmptyList, to znamena, ze budu testovane vsetky najdene wifi AP")
        selected_file = None
    return selected_file


def list_Filtering_AP(device):
    """
        Check if the device is in the filter list.
        :return True if device should not be filtered, False in the other case.
    """
    file_path = 'config/'
    common_name = 'kismet.device.base.commonname'
    file = txt_File_To_List()
    if file is not None:
        with open(file_path + file) as fp:
            if file == 'whiteList.txt':
                for line in fp:
                    if re.match(line.strip(), device[common_name]) is not None:
                        return True
                return False
            if file == 'blackList.txt':
                for line in fp:
                    if re.match(line.strip(), device[common_name]) is not None:
                        return False
                return True
            if file == 'whiteBlackList.txt':
                for line in fp:
                    kk = line.split("#")
                    if re.match(kk[0], device[common_name]) is not None:
                        if re.match(kk[1], device[common_name]) is not None:
                            return False
                        else:
                            return True
                return False
    else:
        return True


def parse():
    """
        Parsing of the last Kismet database.
        Needed data are transferred to our SQLite database.
    """
    # Create connection to the Kismet database and own SQLite database.
    kismet_file = get_last_kismet_database()
    conn1 = connect_to_database(KISMET_DIR + kismet_file)
    conn2 = connect_to_database(KISMET_DIR + kismet_file.split('.')[0] + ".sqlite3")

    kismet_cursor = conn1.cursor()
    sqllite_cursor = conn2.cursor()

    kismet_cursor.execute("SELECT device, avg_lat, avg_lon FROM devices")

    # Vytvorime novu databazu s potrebnymi atributmi
    sqllite_cursor.execute(
        "CREATE TABLE IF NOT EXISTS ownTableOfWifiAP (ID INTEGER PRIMARY KEY AUTOINCREMENT, "
        "MACaddress VARCHAR(64), Manufacturer VARCHAR(255), "
        "SSIDChannel VARCHAR(255), SSID VARCHAR(255), Encryption VARCHAR(64), "
        "SignalStrength INTEGER, Coordinates VARCHAR(255))")

    countDevice = 0
    countWifiAp = 0

    # Prejdeme vsetkymi zariadeniami, najdeme AP
    # a pridame ich do sqllite databazy ak este nie su tam
    for ap in kismet_cursor.fetchall():
        device = json.loads(ap[0].decode("utf-8"))
        countDevice += 1

        if device['kismet.device.base.type'] != 'Wi-Fi AP':
            LOGGER.info("err: the device %s %s", device["kismet.device.base.commonname"], "is not an AP")
            continue

        def get_attribute(attr_name, device_name, d=device):
            if not isinstance(d, dict):
                return ''

            attr = d.get(attr_name, '')
            if attr == '':
                LOGGER.warning('Attribute %s was not found for the device %s', attr_name, device_name)
            return attr

        ssid = get_attribute('kismet.device.base.commonname', '')
        mac = get_attribute('kismet.device.base.macaddr', ssid)
        manuf = get_attribute('kismet.device.base.manuf', ssid)
        channel = get_attribute('kismet.device.base.channel', ssid)
        crypt = get_attribute('kismet.device.base.crypt', ssid)
        signal_obj = get_attribute('kismet.device.base.signal', ssid)
        min_signal = get_attribute('kismet.common.signal.min_signal', ssid, d=signal_obj)

        LOGGER.info("** AP found %s **", mac)
        LOGGER.info("  Manufacturer: %s", manuf)
        LOGGER.info("  SSID Channel: %s", channel)
        LOGGER.info("  SSID: %s", ssid)
        LOGGER.info("  Encryption: %s", crypt)
        LOGGER.info("  Signal strength: %s dbm", min_signal)

        parameters = (mac, manuf, channel,
                      ssid, crypt)

        res = sqllite_cursor.execute("SELECT * FROM ownTableOfWifiAP own "
                                     "where own.MACaddress == ?"
                                     "AND own.Manufacturer == ?"
                                     "AND own.SSIDChannel == ?"
                                     "AND own.SSID == ?"
                                     "AND own.Encryption == ?", parameters)
        result_device = res.fetchall()
        coordinates = '%f %f' % (ap[1], ap[2])

        if len(result_device) == 0 and list_Filtering_AP(device) is True:
            sqllite_cursor.execute("INSERT INTO ownTableOfWifiAP "
                                   "(MACaddress, Manufacturer, SSIDChannel, SSID, Encryption, SignalStrength, Coordinates) "
                                   "VALUES (?,?,?,?,?,?,?)",
                                   (mac, manuf, channel, ssid, crypt, min_signal, coordinates))
            countWifiAp += 1

        if len(result_device) > 0 and list_Filtering_AP(device):
            sqllite_cursor.execute("UPDATE ownTableOfWifiAP "
                                   "SET SignalStrength = ?, Coordinates = ? "
                                   "WHERE MACaddress = ? AND Manufacturer = ? AND SSIDChannel = ?"
                                   "AND SSID = ? AND Encryption = ?",
                                   (min_signal, coordinates, mac, manuf, channel, ssid, crypt))
        conn2.commit()

    conn1.close()
    conn2.close()
    LOGGER.info("Pocas scanovania bolo najdenych: %s %s %s %s",
                countDevice, "roznych Wifi zariadeny, z ktorych ",
                countWifiAp, "vyhovovalo nasmu scanu")


def connect_to_database(path):
    """
        Tries to connect to a database defined by the 'path' parameter.
        In case of failure it tries to connect 8 times.
        :return connection object of the database. None in case of failure.
    """
    reconnection_num = 8
    for i in range(reconnection_num):
        try:
            connection = sqlite3.connect(path)
            return connection
        except Exception as e:
            if i == reconnection_num - 1:
                break
            LOGGER.warning(e)
            LOGGER.warning("Could not connect to the database. Repeat connection after 1.5s")

        time.sleep(1.5)

    LOGGER.error("Could not connection to the database. Terminating the system.")
    return None


def sleep():
    time.sleep(SETUP[3])    # Sleep time is defined by the configuration file.
